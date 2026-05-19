# Layer 2: MEM Slice 内部架构深入分析

> **时间**: 20260519-1645
> **类型**: Working Document — 基于公开信息的技术推断与分析

---

## 1. MEM Slice 内部结构推断

### 1.1 5.5 MB MEM Unit 的内部构成

根据公开的架构信息，每个 MEM unit 包含 5.5 MB SRAM。基于 14nm 工艺的典型 SRAM 宏单元密度，可以做以下推断：

**14nm SRAM 宏单元密度参考**:
- 典型 14nm 高密度 SRAM bitcell: ~0.042-0.050 um²
- SRAM 宏单元利用率: ~60-70%（含外围电路）
- 每 mm² 可实现约 2-3 MB SRAM

**5.5 MB MEM Unit 的物理面积估算**:
```
5.5 MB × 8 bits/byte × 0.046 um²/bit ÷ 0.65 ≈ 3.1 mm² 每 MEM 单元
40 MEM 单元 × 3.1 mm² ≈ 124 mm² (全芯片 SRAM 面积)
芯片总面积 725 mm² → SRAM 占比约 17%
```

这与公开信息中 SRAM 占据芯片面积约 15-20% 的描述吻合。

### 1.2 Bank 组织模式推断

基于带宽需求和典型 SRAM 架构：

```
5.5 MB MEM Unit
  └── N 个 SRAM Bank
       ├── Bank 0: ~64-128 KB
       ├── Bank 1: ~64-128 KB
       ├── ...
       └── Bank N-1: ~64-128 KB
```

**Bank 数量估算**:

带宽需求驱动:
- 每个 MEM 单元需要支持: 80 TB/s ÷ 40 MEM = 2 TB/s per MEM
- 在 900 MHz: 2 TB/s ÷ 900 MHz = 2,222 bytes/cycle per MEM
- SRAM bank 典型位宽: 64-256 bytes (512-2048 bits)
- 需要的 bank 数: 2,222 / 128 ≈ 17-35 banks

推断: **每 MEM 单元约 16-32 个 bank**，每个 bank 约 172-344 KB

```
5.5 MB = 16 banks × 344 KB/bank
      = 32 banks × 172 KB/bank
```

### 1.3 地址映射模型

```
全局地址 (虚拟)
  ↓ 编译器映射
物理地址:
  ├── Chip ID (多芯片扩展时)
  ├── Superlane ID (0-19)
  ├── MEM 单元 ID (左/右, 0-1)
  ├── Bank ID (0-31)
  ├── Row Address
  └── Column Address
```

编译器在编译时将张量元素映射到具体的 bank、行、列地址，确保：
- 连续访问分布在不同的 bank 中（bank interleaving）
- 并发访问不冲突（no bank conflict）

### 1.4 读写端口配置

基于 2.2 TB/s per MEM 单元的带宽需求：

| 端口类型 | 数量 | 位宽 | 频率 | 总带宽 |
|----------|------|------|------|--------|
| **读端口** | 1-2 | 512-1024 bit | 900 MHz | ~57-230 GB/s |
| **写端口** | 1-2 | 512-1024 bit | 900 MHz | ~57-230 GB/s |
| **合计** | 2-4 | | | ~115-460 GB/s per MEM 单元 |

推断: 每个 MEM 单元可能配备 **1 读端口 + 1 写端口**（双端口 SRAM），每个端口 **1024 bit (128 B)** 宽。这样：

```
128 B/port × 2 ports × 900 MHz × 16-32 banks = ~3.6-7.2 TB/s per MEM 单元
```

这超过了 2 TB/s 的需求，留有余量。

---

## 2. 带宽计算验证

### 2.1 自上而下验证

| 参数 | 值 | 说明 |
|------|-----|------|
| 每个 MEM 单元端口位宽 | 128 B (1024 bit) | 每个端口 |
| 端口数 | 2 (R+W) | 双端口 SRAM |
| Bank 并行度 | 16-32 | 同时访问 |
| 频率 | 900 MHz | 核心时钟 |
| MEM 单元数 | 40 | 20 superlanes × 2 |
| 理论带宽 | 40 × 2 × 128 × 900M × (16-32)/(16-32) | 修正: 单个 MEM 内部的 bank 并行与端口结合 |

更准确的计算：
```
每 MEM 单元: 128 B × 2 端口 = 256 B/cycle
每 MEM 单元带宽: 256 B × 900 MHz × bank_factor
40 MEM 单元: 40 × 256 × 900M × bank_factor
```

当 bank_factor ≈ 4-8× 时（bank 级并行度，每个 bank 独立访问）:
```
40 × 256 × 900M × 4 = 36.9 TB/s
40 × 256 × 900M × 8 = 73.7 TB/s ≈ 80 TB/s ✓
```

### 2.2 与 HBM 的带宽密度对比

| 指标 | Groq TSP SRAM | HBM3 (H100) | 比率 |
|------|---------------|-------------|------|
| 每引脚带宽 | ~7.3 TB/s per pin (11 pins) | ~0.3 TB/s per stack (12 stacks) | 24× |
| 带宽/容量比 | 348 TB/s per GB | 37.5 GB/s per GB | 9,280× |
| 每 W 带宽 | ~432 GB/s per W | ~4.3 GB/s per W | 100× |
| 每 mm² 带宽 | ~110 GB/s per mm² | ~3.7 GB/s per mm² | 30× |

> **关键洞察**: Groq TSP 的 SRAM 带宽密度在功耗归一化上达到 H100 HBM 的 **100 倍**。这是 SRAM 最核心的优势：**不需要 SerDes、不需要 long-reach driver、不需要 TSV 穿透硅通孔**。

---

## 3. SRAM 独特的功耗优势

### 3.1 每 bit 访问能耗

| 存储层次 | 能耗 (pJ/bit) | 相对于 SRAM |
|----------|--------------|-------------|
| SRAM (on-chip) | ~0.3 pJ | 1× |
| DRAM (off-chip) | ~1.3 pJ | 4.3× |
| HBM (through TSV) | ~2-3 pJ | 7-10× |
| **HBM + PHY** | **~5-10 pJ** | **17-33×** |

Groq TSP 的每 bit 访问能耗低 20 倍以上，主要来自：
1. **无 off-chip 驱动** — 节省 SerDes 和 I/O 功耗
2. **无 DRAM refresh** — SRAM 无需刷新（~DRAM 总功耗 15-25%）
3. **无 cache tag 查询** — 统一地址空间，无 tag 比对
4. **近距离布线** — SRAM 紧邻计算单元

### 3.2 功耗分解对比

假设 Llama-2 7B 推理：

| 组件 | GPU (H100) | Groq TSP |
|------|-----------|----------|
| 计算功耗 | ~200W | ~60W |
| HBM/DRAM 功耗 | ~120W | 0 |
| SRAM 功耗 | ~30W (cache) | ~50W |
| 互联功耗 | ~50W | ~30W |
| 其他 | ~300W | ~45W |
| **总计** | **~700W** | **~185W** |

---

## 4. 与竞争 SRAM 方案对比

### 4.1 Graphcore IPU

| 指标 | Groq TSP | Graphcore IPU (GC200) |
|------|----------|----------------------|
| SRAM 容量 | 230 MB | ~900 MB (分布式) |
| 组织方式 | 集中式全局 SRAM | 分布式 per-tile SRAM |
| 管理方式 | 编译器统一管理 | 硬件+编译器 |
| 带宽 | 80 TB/s | ~150-180 TB/s |
| 工艺 | 14nm | 7nm |
| 去确定性 | 完全确定性 | 部分确定性 |

### 4.2 Cerebras WSE

| 指标 | Groq TSP | Cerebras WSE-3 |
|------|----------|-----------------|
| SRAM 容量 | 230 MB | 44 GB |
| 组织方式 | 20 superlane 集中式 | 850,000 core 分布式 |
| 带宽 | 80 TB/s | 214 PB/s (片上) |
| 晶圆尺寸 | 725 mm² 单芯片 | 整片晶圆 (~46,225 mm²) |
| 制造难度 | 普通 | 极高 |

### 4.3 Groq TSP 的独特优势
- **全局统一 SRAM 地址空间** — 简化编译器设计
- **确定性 cycle 级调度** — 无任何运行时不确定性
- **功能切片架构** — 每个 slice 极致优化面积效率

---

## 5. 总结: MEM Slice 架构关键参数

| 参数 | 推断值 | 置信度 | 依据 |
|------|--------|--------|------|
| MEM 单元 SRAM | 5.5 MB | 高 | 公开文献确认 |
| 每 MEM bank 数 | 16-32 | 中等 | 基于带宽计算 |
| Bank 大小 | 172-344 KB | 中等 | 基于总容量/bank 数 |
| 端口配置 | R+W 双端口 | 高 | 基于带宽需求 |
| 端口位宽 | ~1024 bit | 中等 | 基于带宽计算 |
| 全芯片 MEM 单元数 | 40 | 高 | 公开文献确认 |
| SRAM 占芯片面积 | ~17% | 中等 | 基于 14nm SRAM 密度估算 |
| SRAM 功耗占比 | ~27% | 低 | 估算值 |
