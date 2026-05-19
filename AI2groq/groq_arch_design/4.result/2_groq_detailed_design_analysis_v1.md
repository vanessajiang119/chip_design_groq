# Groq TSP 详细设计分析报告
# Groq TSP Detailed Design Analysis Report

> 版本: v1.0 | 创建时间: 2026-05-19
> 分析层级: Layer 2 (微架构深度展开) — 6 模块覆盖
> 数据来源: Round 1/2 Research + Layer 2 Working Documents

---

## 1. ICU — 指令控制单元 RTL 微架构

### 1.1 VLIW 包推断格式 (VLIW Packet Format)

基于 Groq 专利 US20240037064A1 和功能分片架构，推测 VLIW 包格式包含 8 个字段：

```
VLIW Packet (~100-200 bits):
┌────────┬──────┬──────┬──────┬──────┬──────┬──────┬──────┐
│ HEADER │MEM_L │MEM_R │ VXM  │MXM_L │MXM_R │SXM_L │SXM_R │
│ (ctrl) │(op)  │(op)  │(op)  │(op)  │(op)  │(op)  │(op)  │
└────────┴──────┴──────┴──────┴──────┴──────┴──────┴──────┘
```

**HEADER 字段**:
- Packet ID (4-bit): 调试和追踪
- Instruction Count (4-bit): 包内指令数
- Sync Flags (2-bit): SYNC/NOTIFY/DESKEW 标志
- Queue Select (8-bit): 目标指令队列选择

**每个操作字段 (Operation Slot)**:
- Opcode (8-bit): 256 种操作
- Stream ID (6-bit): 目标流 ID (0-63)
- Direction (1-bit): East/West
- Destination Slice (4-bit): 目标切片
- Immediate/Offset (16-bit): 立即数或偏移量
- Flags (4-bit): 控制标志

### 1.2 144 队列分配表

| 队列范围 | 用途 | 数量 |
|---------|------|------|
| Q0-Q15 | MEM 左切片 (西半球) | 16 |
| Q16-Q31 | MEM 右切片 (东半球) | 16 |
| Q32-Q47 | VXM 向量操作 | 16 |
| Q48-Q63 | MXM 左切片 (西半球) | 16 |
| Q64-Q79 | MXM 右切片 (东半球) | 16 |
| Q80-Q95 | SXM 左切片 (西半球) | 16 |
| Q96-Q111 | SXM 右切片 (东半球) | 16 |
| Q112-Q127 | ICU 控制/同步 | 16 |
| Q128-Q143 | 保留/特殊功能 | 16 |

每个队列微架构：
- 深度: ~16-32 条指令 (FIFO)
- 宽度: ~64-128 bits
- 发射逻辑: 一个比较器 + 一个计数器 (无 reservation station)
- 每队列每 cycle 0-1 条指令

### 1.3 流水线 5 阶段 (Pipeline Stages)

```
Stage 0: 指令取指 (Instruction Fetch)
  - 从指令 SRAM 读取 VLIW 包
  - 每 cycle 读取 1-2 个 VLIW 包

Stage 1: 指令解码 (Instruction Decode)
  - 解码 VLIW 包头
  - 提取各操作字段
  - 验证指令合法性

Stage 2: 队列分发 (Queue Dispatch)
  - 将解码后的操作分发到 144 队列中对应的队列
  - 每个操作指定目标 queue ID
  - 支持广播到多个 queue

Stage 3: 指令发射 (Instruction Issue)
  - 每个 queue 按编译器预设 schedule 发射
  - 发射带宽: 80+ 条指令/cycle

Stage 4: 追踪与同步 (Trace & Sync)
  - 管理 SYNC/NOTIFY/DESKEW 事件
  - 硬件对齐计数器 (HAC) 管理
```

### 1.4 SYNC/NOTIFY/DESKEW 协议

**SYNC 指令**: 暂停所有 144 个队列，等待到达同步点
- 用于阶段转换或模型层之间

**NOTIFY 指令**: 广播同步信号恢复所有队列执行
- 点对点通知比全局屏障更轻量

**DESKEW 指令**: 等待硬件对齐计数器 (HAC) 溢出
- 用于多 TSP 系统中的 cycle 边界对齐
- 补偿芯片间的时钟漂移

```
Queue 0 (Notifier)          Queue 1-143 (Listeners)
       │                          │
       ├── SYNC() ───────────────►│  ← 所有 queue 暂停
       │                          │
    [计算/加载数据]              [等待]
       │                          │
       ├── NOTIFY() ────────────►│  ← 广播唤醒
       │                          │
       │◄──── 恢复执行 ────────── │
```

### 1.5 面积分解表

| 子模块 | 面积占比 (ICU 内) | 估算面积 (14nm) |
|--------|-----------------|----------------|
| 指令队列 (144 × 64 条目) | ~40% | ~1.5-2 mm² |
| 解码逻辑 | ~20% | ~0.8 mm² |
| 发射逻辑 | ~15% | ~0.6 mm² |
| 同步逻辑 | ~10% | ~0.4 mm² |
| 控制/状态寄存器 | ~10% | ~0.4 mm² |
| 布线/测试 | ~5% | ~0.2 mm² |
| **ICU 总计** | **100%** | **~4-8 mm²** |

---

## 2. MEM — 存储切片 RTL 微架构

### 2.1 SRAM Bank 组织

| 层级 | 容量 | 数量 | 合计 |
|------|------|------|------|
| SRAM Bank | ~172-344 KB | 16-32 / MEM | 5.5 MB / MEM |
| MEM 单元 | 5.5 MB | 40 (20×2) | **220 MB** |
| Super Lane | 11 MB | 20 | **220 MB** |

总 Bank 数: 40 MEM × (16-32) banks = **6,400+ banks**

### 2.2 5.5 MB/切片分层结构

```
MEM Slice (5.5 MB):
┌───────────────────────────────────────────┐
│  20 tiles (垂直堆叠)                        │
│  Tile 19 (顶层)                            │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐   │
│  │ Bank 0   │ │ Bank 1   │ │ Bank 2   │   │
│  │ 32KB×N   │ │ 32KB×N   │ │ 32KB×N   │   │
│  └──────────┘ └──────────┘ └──────────┘   │
├───────────────────────────────────────────┤
│  Tile 18/17/...                           │
├───────────────────────────────────────────┤
│  Tile 0 (底层)                             │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐  │
│  │ Bank 0   │ │ Bank 1   │ │ Bank 2   │  │
│  └──────────┘ └──────────┘ └──────────┘  │
└───────────────────────────────────────────┘

每个 Tile: ~256 KB SRAM (20 tiles × 256 KB = 5 MB)
每个 Bank: ~32 KB, 每 tile 约 8 个 bank
```

### 2.3 80 TB/s 详细推导

```
公式: 20 SL × 2 MEM/SL × 512 B × 900 MHz × 2 (RD+WR) × ~2.2 (bank_factor)

逐步分解:
1. Super Lane 数据宽度: 512 B/cycle (16 lanes × 32 B/lane)
2. 全芯片数据宽度: 20 SL × 512 B = 10,240 B/cycle
3. 基础带宽 (单方向): 10,240 B × 900 MHz = 9.2 TB/s
4. 双向 (RD+WR): 9.2 TB/s × 2 = 18.4 TB/s
5. Bank 级并行倍增: SRAM bank 并行因子 ≈ 4.4×
6. 总带宽: 18.4 TB/s × 4.4 = 80 TB/s ✓

或等价:
40 MEM × 2 ports × 128 B × 900 MHz × ~4.4 bank_factor = 80 TB/s
```

### 2.4 地址映射布局

```
全局地址 (编译器管理, 220 MB):
  0x00000000
  ┌──────────────────────────────────┐
  │ 权重 (Weights)                    │ ~120 MB
  │ 所有模型权重静态分配               │
  ├──────────────────────────────────┤
  │ 激活值缓冲区 (Activations)         │ ~60 MB
  │ 中间激活值流式缓冲区               │
  ├──────────────────────────────────┤
  │ 指令存储 (Instruction)            │ ~20 MB
  │ 编译后的 VLIW 包                  │
  ├──────────────────────────────────┤
  │ 保留/Runtime 数据                 │ ~20-30 MB
  │ 流寄存器文件备份等                 │
  └──────────────────────────────────┘
  0x0DBFFFFF

地址映射路径:
  Chip ID (多芯片) → Superlane ID (0-19) → MEM 单元 ID (左/右)
  → Bank ID (0-31) → Row Address → Column Address
```

### 2.5 双端口配置

| 端口类型 | 数量 | 宽度 | 总带宽/MEM |
|---------|------|------|-----------|
| 读端口 (向东西) | 2 | 32 B × 2 | ~115 GB/s |
| 写端口 (向东西) | 2 | 32 B × 2 | ~115 GB/s |
| **总计** | **4** | **128 B/cycle** | **>2 TB/s** |

### 2.6 MEM 访问延迟

| 操作 | 延迟 (cycles) |
|------|-------------|
| SRAM 读访问 (bank select + read) | 2-3 |
| SRAM 写访问 | 2-3 |
| 流 setup (Stream ID 分配) | 1 |
| 切片间传输 (每 SL) | 1 |
| 总访问延迟 | 5-20 |

---

## 3. VXM — 向量执行模块 RTL 微架构

### 3.1 320-lane SIMD 详细结构

```
VXM (每个 Super Lane, 16 lanes × 32 bytes):
┌─────────────────────────────────────────────────────────────┐
│  Lane 0    Lane 1    Lane 2    ...    Lane 14   Lane 15    │
│ ┌──────┐  ┌──────┐  ┌──────┐         ┌──────┐  ┌──────┐   │
│ │ ALU0 │  │ ALU1 │  │ ALU2 │         │ALU14 │  │ALU15 │   │
│ │┌────┐│  │┌────┐│  │┌────┐│         │┌────┐│  │┌────┐│   │
│ ││ FP ││  ││ FP ││  ││ FP ││         ││ FP ││  ││ FP ││   │
│ ││INT ││  ││INT ││  ││INT ││  ...    ││INT ││  ││INT ││   │
│ ││SIMD││  ││SIMD││  ││SIMD││         ││SIMD││  ││SIMD││   │
│ │└────┘│  │└────┘│  │└────┘│         │└────┘│  │└────┘│   │
│ └──────┘  └──────┘  └──────┘         └──────┘  └──────┘   │
└─────────────────────────────────────────────────────────────┘

20 SL × 16 lanes/SL = 320 lanes 全芯片
16 lanes/SL × 16 ALU/lane = 5,120 运算单元 全芯片
```

### 3.2 ALU 内部 7 子单元

| 子单元 | 功能 | 位宽 |
|--------|------|------|
| FP32 Adder | 浮点加法/减法 | 32-bit |
| FP32 Multiplier | 浮点乘法 | 32-bit |
| INT32 ALU | 整数算术/逻辑 | 32-bit |
| FP16/BF16 Unit | 半精度运算 | 16-bit |
| INT8 SIMD | 8-bit SIMD 运算 | 32-bit (4×INT8) |
| Type Converter | 精度转换 | 可变 |
| Comparator | 比较/选择 | 32-bit |

### 3.3 20 级流水线阶段

```
Stage 0-1:  指令接收 (Inst Receive)
             从垂直指令流接收来自 ICU 的 VXM 操作码
             Stream ID 解析

Stage 2-3:  操作数加载 (Operand Load)
             从东西方向数据流接收源操作数

Stage 4-5:  流合并 (Stream Combine)
             多流输入合并, 数据类型统一

Stage 6-12: 算术执行 (Arithmetic Execute)
             不同运算延迟:
               INT ADD: 1 cycle
               INT MUL: 2-3 cycles
               FP ADD: 3-4 cycles
               FP MUL: 4-5 cycles
               FP DIV: 7-12 cycles

Stage 13-15: 类型转换/格式化 (Type Convert)
             结果精度转换, TruePoint 累加输出格式化

Stage 16-17: 归约操作 (Reduce)
             跨 lane 的 SUM/MAX/MIN

Stage 18-19: 结果输出 (Result Output)
             写回数据流, 指定输出 Stream ID 和方向
```

### 3.4 TruePoint 100-bit 累加器实现

Groq 专有精度技术，保证无精度损失的累加：

```
传统方式:
  FP16 输入 → FP16 乘法 → FP16 累加 → FP16 输出
            ↘ 精度损失 ↗

TruePoint 方式:
  INT8/FP16 输入 → 全精度乘法 → 100-bit 累加器 → 按需量化输出
                                       ↓
                               精度无损累加
```

**关键特性**:
1. 矩阵运算使用 100-bit 中间累加器
2. 权重/激活值可用低精度 (INT8/FP16) 存储
3. 输出根据下游误差敏感度选择性量化
4. 相比 BF16 精度无损且速度提升 2-4×

### 3.5 向量指令集分类表

| 类别 | 指令 | 延迟 (cycles) |
|------|------|-------------|
| **算术** | VADD, VSUB, VMUL, VFMUL | 1-5 |
| | VFDIV, VSQRT, VMLA | 3-15 |
| **激活** | RELU, GELU, TANH, SIGMOID | 2-8 (近似) |
| | EXP, LOG | 5-12 (迭代/LUT) |
| | SOFTMAX (跨 lane) | 10-15 |
| **归约** | REDUCE_SUM, REDUCE_MAX, REDUCE_MIN | 5-8 |
| | REDUCE_MEAN | 6-10 |
| **类型转换** | CVT_I8_F16, CVT_F16_F32, CVT_F32_I8 | 2-4 |
| | CVT_BF16_F32, PACK_I8, UNPACK_I8 | 1-3 |
| **比较** | VCMP, VMAX, VMIN, VSEL | 1-2 |
| **逻辑** | VAND, VOR, VXOR, VNOT | 1 |

### 3.6 全芯片向量性能

| 精度 | ops/cycle (全芯片) | 性能 @900MHz |
|------|-------------------|-------------|
| INT8 | 20,480 | 18.4 TOPS |
| FP16 | 10,240 | 9.2 TFLOPS |
| FP32 | 5,120 | 4.6 TFLOPS |

---

## 4. MXM — 矩阵执行模块 RTL 微架构

### 4.1 4 Plane × 320×320 Systolic Array

```
MXM 切片 (1 个):
┌──────────────────────────────────────────────────────────┐
│  Plane 0 (320×320)                                       │
│  ┌────────┐ ┌────────┐         ┌────────┐               │
│  │16×16 SC│ │16×16 SC│  ... 19 │16×16 SC│  20 cols     │
│  └────────┘ └────────┘         └────────┘               │
│  ┌────────┐ ┌────────┐         ┌────────┐               │
│  │16×16 SC│ │16×16 SC│  ... 19 │16×16 SC│  20 rows     │
│  └────────┘ └────────┘         └────────┘               │
│     ...        ...                ...   20×20 SCells    │
│  ┌────────┐ ┌────────┐         ┌────────┐               │
│  │16×16 SC│ │16×16 SC│  ... 19 │16×16 SC│               │
│  └────────┘ └────────┘         └────────┘               │
├──────────────────────────────────────────────────────────┤
│  Plane 1/2/3 (各 320×320)                                 │
└──────────────────────────────────────────────────────────┘
```

### 4.2 16×16 Supercell 内部结构

```
16×16 Supercell:
┌──────────────────────────────────┐
│  Weight Register File (16×16)    │ ← 权重本地存储
│  ┌─ w00 ─ w01 ─ ... ─ w0,15 ─┐  │
│  │  │       │           │     │  │
│  │  MAC    MAC   ...    MAC   │  │
│  │  │       │           │     │  │
│  │  w10 ─ w11 ─ ... ─ w1,15  │  │
│  │  ...     ...   ...   ...   │  │
│  │ w15,0 ─ w15,1 ─ ... ─ w15,15│ │
│  └────────────────────────────┘  │
│  输入: Activation Bus (16-wide)  │
│  输出: Partial Sum Bus (16-wide) │
└──────────────────────────────────┘

每个 MAC:
┌─────────────────────┐
│  Weight Reg (W)      │ ← 权重固定 (weight-stationary)
│  Activation Reg (A)  │ ← 激活值流过
│  Partial Sum Reg (P) │ ← 部分和累加
│  P += A × W          │
└─────────────────────┘
```

### 4.3 关键参数

| 参数 | 数值 |
|------|------|
| 每 MXM Plane 数 | 4 |
| 每 Plane 尺寸 | 320×320 MACs |
| 每 Plane Supercell 数 | 400 (20×20) |
| 每 Supercell 尺寸 | 16×16 MACs |
| 每 MXM MAC 总数 | 409,600 (4×320×320) |
| 每 Super Lane MXM 数 | 2 (左右) |
| 全芯片 MXM 总数 | 40 (20 SL × 2) |
| 全芯片 MAC 总数 | 16,384,000 (40 × 409,600) |
| 每 Plane 权重容量 | 102,400 weights (320×320) |
| 权重加载时间 | <40 cycles (4 planes) |

### 4.4 Weight-Stationary 三步执行

**Step 1: 权重加载 (Weight Load)**
- 权重通过数据流进入 4 个 plane 的 MAC 阵列
- 所有 4 个 plane 并行加载
- <40 cycles 完成 4 × 102,400 权重的加载

**Step 2: 激活值流 (Activation Stream)**
- 方向: East → West 或 West → East
- 每个 cycle 一个 320-element 向量流过 systolic array
- 激活值水平传播，每个 MAC 执行 P += A × W

**Step 3: 部分和排空 (Drain)**
- 部分和在垂直方向传播 (South → North)
- 经过 320 cycles 完成所有部分和累加
- 结果输出到数据流 (→ SXM/VXM chain)

### 4.5 4 Plane 使用模式

| 模式 | 描述 | 应用 |
|------|------|------|
| **大矩阵分解** | 4 个 320×320 块独立运算 | 多头注意力的 4 个 head 并行 |
| **FP16 精度** | 4 planes 处理高低字节后组合 | 高精度矩阵乘 |
| **批量处理** | 同一权重, 4 组不同激活值 | 小批量推理 (batch=4) |

### 4.6 性能参数

| 精度 | MAC/cycle | 峰值性能 @900MHz |
|------|-----------|-----------------|
| INT8 (单 MXM) | 409,600 | 368 GOPS |
| INT8 (全芯片) | 16,384,000 | 14.7 POPS |
| FP16 (单 MXM) | 409,600 | 184 TFLOPS |
| FP16 (全芯片) | 16,384,000 | 7.4 PFLOPS |

---

## 5. SXM — 移位/交换执行模块 RTL 微架构

### 5.1 Tiled Crossbar 1D 实现

SXM 根据 Groq 专利 US20240037064A1 实现为 lane switching slice：

```
SXM Tiled Crossbar (320 × 32B):
                    输出 Lanes
         ┌──────────────────────────────────┐
         │ Lane 0  Lane 1  ...  Lane 19    │
         │  ┌─┐    ┌─┐         ┌─┐         │
输入     │  │ │    │ │         │ │         │
Lane 0 ──┼─┤ ├───►│ │   ...   │ │         │
         │  │ │    │ │         │ │         │
Lane 1 ──┼─┤ ├────┤ ├───►... │ │         │
         │  │ │    │ │         │ │         │
   ...   │  ...    ...         ...         │
Lane 19 ─┼─┤ ├────┤ ├───►... │ │         │
         │  └─┘    └─┘         └─┘         │
         └──────────────────────────────────┘
```

**Tiled vs 全 Crossbar 面积优化**:

| 特性 | 全 Crossbar | Tiled Crossbar (SXM) |
|------|------------|---------------------|
| 复杂度 | O(N²) | O(N × tile_size) |
| 面积 (N=320) | ~1M 连接点 | ~20K 连接点 (tile=16) |
| 延迟 | ~1 cycle | ~1-2 cycles |
| 灵活性 | 任意排列 | 块内任意, 块间有限 |

### 5.2 Permute/Shift/Rotate/Broadcast/Transpose 10 种功能

| # | 功能 | 操作 | 延迟 (cycles) |
|---|------|------|-------------|
| 1 | Shift | 向量元素左移/右移, 空缺填 0 | 1 |
| 2 | Rotate | 循环移位, 移出位补到另一侧 | 1 |
| 3 | Permute | Lane 间任意元素重排 | 1-2 |
| 4 | Broadcast | 将单 lane 数据复制到所有 lanes | 1 |
| 5 | Gather | 从多个 lane 收集数据到目标 lane | 1-2 |
| 6 | Scatter | 将一个 lane 数据分发到多个 lanes | 1-2 |
| 7 | Transpose | 矩阵转置的 lane 级实现 | 2 |
| 8 | Interleave | 多数据流的交错合并 | 1 |
| 9 | Select | 按 mask 选择特定 lanes | 1 |
| 10 | Pack/Unpack | 数据格式重组 | 1-2 |

### 5.3 C2C 片间接口

SXM 承担片间通信功能：

```
TSP 0                     TSP 1
┌─────────────────┐      ┌─────────────────┐
│ ...              │      │              ...│
│ SXM ──C2C Link──┼──────┼── SXM          │
│ ...              │      │              ...│
└─────────────────┘      └─────────────────┘

C2C 参数:
  - 8 lanes × 32 GB/s per direction
  - 编译器静态调度通信
  - 无自适应路由 — 通信模式在编译时已知
  - DESKEW 指令同步多 TSP
```

### 5.4 面积优化分析

| 子模块 | 单个 SXM | 全芯片 (40 SXM) |
|--------|---------|----------------|
| Crossbar 网络 (320×32B) | ~4 mm² | ~160 mm² |
| Permuter 逻辑 | ~1 mm² | ~40 mm² |
| 缓冲/流水线寄存器 | ~1 mm² | ~40 mm² |
| C2C/PCIe 接口 | ~2 mm² | ~80 mm² |
| 控制/配置逻辑 | ~0.5 mm² | ~20 mm² |
| **SXM 总计** | **~8.5 mm²** | **~340 mm²** |

---

## 6. 时钟与功耗设计 (Clock & Power Design)

### 6.1 面积分布预估表 (725 mm² total)

| 模块 | 估算面积 | 占比 |
|------|---------|------|
| SRAM (MEM) | ~290-360 mm² | ~40-50% |
| MXM (矩阵乘, 409,600 MACs) | ~145-180 mm² | ~20-25% |
| VXM (向量, 5,120 ALUs) | ~72-108 mm² | ~10-15% |
| SXM (Crossbar + C2C + PCIe) | ~72 mm² | ~10% |
| ICU (控制, 144 队列) | ~4-8 mm² | <3% |
| 其他 (时钟树/布线/I/O) | ~72-108 mm² | ~10-15% |

### 6.2 功耗分布表 (300W TDP)

| 模块 | 估算功耗 | 占比 |
|------|---------|------|
| SRAM 阵列 | ~120-150W | ~40-50% |
| MXM MAC 阵列 | ~60-75W | ~20-25% |
| VXM ALU | ~30-45W | ~10-15% |
| SXM Crossbar + C2C SerDes | ~30W | ~10% |
| ICU + 时钟分布 | ~3-5W | ~1-2% |
| 时钟树/布线/漏电 | ~30-45W | ~10-15% |

### 6.3 各模块延迟表格

| 模块 | 操作 | 延迟 (cycles) | 延迟 (ns @900MHz) |
|------|------|-------------|-----------------|
| **ICU** | 指令取指 → 发射 | 3-4 | 3.3-4.4 |
| | 指令传播 (SL 0→19) | 20 | 22.2 |
| | SYNC/NOTIFY 同步 | 1-2 | 1.1-2.2 |
| **MEM** | SRAM 读访问 | 2-3 | 2.2-3.3 |
| | SRAM 写访问 | 2-3 | 2.2-3.3 |
| | 总访问 (load → stream) | 5-12 | 5.5-13.3 |
| **VXM** | INT ADD | 1-2 | 1.1-2.2 |
| | FP16 MUL | 2-3 | 2.2-3.3 |
| | FP32 FMA | 4-5 | 4.4-5.6 |
| | FP DIV | 7-12 | 7.8-13.3 |
| | GELU (分段近似) | ~8 | ~8.9 |
| | SOFTMAX (跨 lane) | 10-15 | 11.1-16.7 |
| | 完整向量流水线 | 20 | 22.2 |
| **MXM** | 权重加载 (4 planes) | <40 | <44.4 |
| | 320×320 矩阵乘 | 320+ | 355+ |
| | 部分和累加 + 输出 | ~20 | ~22.2 |
| **SXM** | 简单移位/旋转 | 1 | 1.1 |
| | Lane 间排列 | 1-2 | 1.1-2.2 |
| | 全 crossbar 操作 | 2 | 2.2 |
| | C2C 片间传播 | 50-100 | 55-111 |

### 6.4 物理实现参数总结

| 参数 | 数值 |
|------|------|
| 制程节点 | 14nm FinFET |
| 时钟频率 | 900 MHz (最高 1.25 GHz) |
| Die 尺寸 | 25mm × 29mm |
| Die 面积 | ~725 mm² |
| 片上 SRAM | ~220-230 MB (40 MEM × 5.5 MB) |
| 晶体管数 | ~数亿 |
| TDP | ~300W (芯片), ~375W (GroqCard) |
| 典型推理功耗 | ~40W (芯片), ~240W (GroqCard) |
| 供电电压 | ~0.8V (core), ~0.9V (SerDes) |
| INT8 峰值性能 | 750-1000 TOPS |
| FP16 峰值性能 | 188-205 TFLOPS |
| 存储带宽 | 80 TB/s (片上 SRAM) |
| 片间互联 | Dragonfly (每 TSP 7 local + 4 global) |
| C2C 链路 | 8 lanes, ~32 GB/s per direction |
| 封装 | GroqCard (PCIe Gen 4 ×16) |
| 散热 | 标准风冷 (~40W/TSP 典型) |

---

> **参考文献**:
> 1. Abts et al., "Think Fast: A TSP for Accelerating Deep Learning", ISCA 2020
> 2. Singh et al., "The Virtuous Cycles of Determinism", ISCA 2022
> 3. US20240037064A1 — Instruction Format and ISA for TSP
> 4. US20230024670A1 — Deterministic Memory for TSP
> 5. US12277444B2 — Software-defined Tensor Streaming Multiprocessor
> 6. Zellic Research — "How Is Groq So Fast?"
> 7. IEEE ITherm 2024 — Direct-On-Chip Hotspot Targeted Microjet Cooling
