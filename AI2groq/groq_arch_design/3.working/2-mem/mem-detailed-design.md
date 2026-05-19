# MEM — 存储切片详细设计分析
# MEM — Memory Slice Detailed Design Analysis

> 创建时间: 2026-05-19T1600
> 分析层级: Layer 2 (微架构深度展开)

---

## 1. 概述 (Overview)

MEM (Memory Slice) 是 Groq TSP 的存储引擎，采用纯 SRAM 单级存储层次。TSP 完全摒弃 DRAM/HBM 和传统缓存层次，所有数据存储在 220-230 MB 的片上 SRAM 中，由编译器静态管理。MEM 切片约占芯片面积的 40-50%。

### 设计哲学 (Design Philosophy)

```
┌─────────────────────────────────────────────┐
│          传统层次 (CPU/GPU)                   │
│  DRAM → L3$ → L2$ → L1$ → RF → ALU         │
│  高容量    低确定性    高延迟                  │
└─────────────────────────────────────────────┘

┌─────────────────────────────────────────────┐
│          TSP 层次 (Groq)                      │
│  SRAM (全局) → 流寄存器 → 功能单元            │
│  低容量     确定性      直接数据流             │
│  高带宽     低延迟      隐式 RF               │
└─────────────────────────────────────────────┘
```

---

## 2. SRAM Tile 组织 (SRAM Tile Organization)

### 物理布局 (Physical Layout)

TSP 的 SRAM 分布在 40 个 MEM 切片上 (20 Super Lanes × 2 MEM/SL):

```
Super Lane n:
┌──────┬──────┬─────────┬────────┬────────┬──────┬──────┐
│ MXM  │ SXM  │  MEM_L  │  VXM   │ MEM_R  │ SXM  │ MXM  │
│      │      │ ┌─────┐ │        │ ┌─────┐ │      │      │
│      │      │ │2.75M│ │        │ │2.75M│ │      │      │
│      │      │ │×2=5.5MB│       │ │×2=5.5MB│     │      │
│      │      │ └─────┘ │        │ └─────┘ │      │      │
└──────┴──────┴─────────┴────────┴────────┴──────┴──────┘
```

### MEM Tile 内部结构 (MEM Tile Internal Structure)

每个 MEM 切片 (5.5 MB) 由多个 Tile 组成:

```
MEM Slice (5.5 MB):
┌───────────────────────────────────────────┐
│  Tile 19 (顶层)                            │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐  │
│  │ Bank 0   │ │ Bank 1   │ │ Bank 2   │  │
│  │ 32KB×N   │ │ 32KB×N   │ │ 32KB×N   │  │
│  └──────────┘ └──────────┘ └──────────┘  │
├───────────────────────────────────────────┤
│  Tile 18                                   │
│  ...                                       │
├───────────────────────────────────────────┤
│  Tile 0 (底层)                             │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐  │
│  │ Bank 0   │ │ Bank 1   │ │ Bank 2   │  │
│  └──────────┘ └──────────┘ └──────────┘  │
└───────────────────────────────────────────┘

每个 Tile: ~256 KB SRAM (20 tiles × 256 KB = 5 MB ~= 5.5 MB)
每个 Bank: ~32 KB
```

### SRAM Bank 参数

| 参数 | 数值 |
|------|------|
| 总 SRAM | 220-230 MB |
| MEM 切片数 | 40 (20 SL × 2) |
| 每切片容量 | ~5.5 MB |
| 每切片 Tile 数 | 20 (垂直堆叠) |
| 每 Tile Bank 数 | 8-16 (推测) |
| 每 Bank 容量 | 32-64 KB (推测) |
| 总 Bank 数 | 40 × 20 × 8 = 6,400+ |

---

## 3. 带宽分析 (Bandwidth Analysis)

### 理论带宽计算 (Theoretical Bandwidth)

```
每 cycle 带宽:
  20 Super Lanes × 16 lanes × 32 bytes/lane = 10,240 bytes/cycle
  = 10 KB/cycle

900 MHz 下:
  10 KB × 900 MHz = 9.0 GB/s (单一方向)
  双向 (RD + WR) = 18 GB/s

单层 SRAM 访问:
  每 cycle 可访问多个 bank
  假设 16-way bank 并行:
    18 GB/s × 16 = 288 GB/s

但 80 TB/s 需要更细粒度的并行:
  88 MEM tiles × 2 ports × 32 bytes × 900 MHz × 2 (RD+WR) = 10.1 TB/s
  再乘以多 bank 并行因子 ~8 = 80 TB/s
```

### 带宽分解 (Bandwidth Breakdown)

| 带宽类型 | 数值 | 计算方式 |
|---------|------|---------|
| 单 lane 带宽 | 28.8 GB/s | 32 bytes × 900 MHz |
| Super Lane 带宽 | 460.8 GB/s | 16 lanes × 28.8 GB/s |
| 芯片总带宽 (理论) | 9.2 TB/s | 20 SL × 460.8 GB/s |
| 芯片总带宽 (报告) | 80 TB/s | 含 multi-bank + multi-port + 双向 |

### 80 TB/s 的物理实现

80 TB/s 带宽通过以下机制实现:

1. **细粒度 Bank 级并行**: 每个 tile 内多个 bank 可同时访问
2. **Tile 级并行**: 20 tiles × 40 slices = 800 MEM tiles 并发
3. **双端口 SRAM**: 每个 MEM 切片支持同时读写
4. **数据路径宽度**: 32 bytes/lane × 16 lanes/SL = 512 bytes/SL/cycle
5. **方向并行**: 东西方向数据流同时传输

---

## 4. 地址空间与映射 (Address Space & Mapping)

### 地址空间布局 (Address Space Layout)

编译器管理的全局 SRAM 地址空间:

```
Address Map (220 MB):
┌──────────────────────────────────┐
│  0x00000000                      │
│  ┌────────────────────────────┐  │
│  │ 权重 (Weights)              │  │ ~120 MB
│  │ 所有模型权重静态分配         │  │
│  └────────────────────────────┘  │
│  ┌────────────────────────────┐  │
│  │ 激活值缓冲区 (Activations)   │  │ ~60 MB
│  │ 中间激活值流式缓冲区         │  │
│  └────────────────────────────┘  │
│  ┌────────────────────────────┐  │
│  │ 指令存储 (Instruction)      │  │ ~20 MB
│  │ 编译后的 VLIW 包            │  │
│  └────────────────────────────┘  │
│  ┌────────────────────────────┐  │
│  │ 保留/Runtime 数据           │  │ ~20-30 MB
│  │ 流寄存器文件备份等           │  │
│  └────────────────────────────┘  │
│  0x0DBFFFFF (220 MB - 1)       │
└──────────────────────────────────┘
```

### 地址映射策略

1. **静态分配**: 所有 tensor 地址在编译时确定
2. **无动态映射**: 无 TLB/页表/MMU
3. **切面对齐**: 地址按 MEM 切片边界对齐以最大化带宽
4. **Bank 级交错**: 连续地址映射到不同 bank，提高并行度
5. **编译器优化**: 数据布局优化最小化 bank 冲突

### 流地址机制 (Stream Addressing)

数据不通过传统地址访问，而是通过流 ID:

```
READ 流: MEM(DDR addr) → Stream_ID (0-31, Dir: E/W)
WRITE 流: Stream_ID (0-31) → MEM(DDR addr)

流的组成:
  Stream = {ID (0-31), Direction (E/W), Data}
```

---

## 5. 数据路径与端口 (Data Path & Ports)

### MEM 切片端口配置

每个 MEM 切片具有:

| 端口类型 | 数量 | 宽度 | 方向 |
|---------|------|------|------|
| 读端口 (向西) | 1 | 32 bytes | Westbound |
| 读端口 (向东) | 1 | 32 bytes | Eastbound |
| 写端口 (向西) | 1 | 32 bytes | Westbound |
| 写端口 (向东) | 1 | 32 bytes | Eastbound |
| 总端口带宽 | 4 | 128 bytes/cycle | 双向 |

### 数据流路径

```
                ← 数据流 (West)    数据流 (East) →
                     │                    │
MEM Slice ───────────┼────────────────────┼──────────
  Port W_RD ────────►│                    │
  Port E_RD ─────────┼───────────────────►│
  Port W_WR ◄────────│                    │
  Port E_WR ─────────┼────────────────────│
                     │                    │
              Lane n (32 bytes)    Lane n+1 (32 bytes)
```

---

## 6. 确定性存储详解 (Deterministic Memory)

### 延迟组成 (Latency Composition)

编译器已知的 MEM 访问延迟:

| 操作 | 延迟 (cycles) | 说明 |
|------|-------------|------|
| SRAM 读访问 | 2-3 | Bank select + read |
| SRAM 写访问 | 2-3 | Write + write-through |
| 流 setup | 1 | Stream ID 分配 |
| 切片间传输 | 1/SL | 每 Super Lane 1 cycle |
| 总访问延迟 | 5-20 | 取决于目标位置 |

### 无 DRAM 的原因

| 因素 | DRAM 问题 | TSP 方案 |
|------|----------|---------|
| Refresh | 不可预测的暂停 | SRAM 无 refresh |
| Row activate | 可变延迟 | SRAM 固定延迟 |
| Bank conflict | 等待时间变化 | 编译器避免冲突 |
| Command bus | 仲裁延迟 | 每切片独立控制 |
| PHY 延迟 | SerDes 延迟 | 片上直连 |

---

## 7. 与传统存储层次对比 (Comparison)

| 特性 | TSP MEM (SRAM) | GPU HBM | CPU DDR5 |
|------|---------------|---------|----------|
| 容量 | 230 MB | 80 GB | 64-512 GB |
| 带宽 | 80 TB/s | 3 TB/s | ~50 GB/s |
| 延迟 | ~5-10 ns | ~100-200 ns | ~80-100 ns |
| 确定性 | 完全 (cycle 级) | 部分 | 无 |
| 能耗/bit | ~1-2 pJ | ~10-20 pJ (含 PHY) | ~20-30 pJ |
| 成本/bit | 高 | 中 | 低 |

### 关键洞察

TSP 用 **SRAM 的容量折衷换取了带宽和确定性**:
- 适合: 单批次低延迟推理, 模型可放入 230MB
- 不适合: 大模型训练, 大批次推理
- 扩展方案: 多 TSP 级联 (Dragonfly 拓扑)
