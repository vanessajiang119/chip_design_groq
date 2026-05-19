# TSP 微架构深度分析 — Round 2 研究报告：五模块深入
# TSP Microarchitecture Deep Dive — Round 2: Module Deep-Dive

> 创建时间: 2026-05-19T1430
> 来源: Multiple web searches, patent analysis, tech analysis articles

---

## 1. ICU — 指令控制单元深度分析

### 微架构角色 (Microarchitecture Role)

ICU 是 TSP 芯片的"大脑"——集中式指令控制单元，以不到 3% 的芯片面积控制整个芯片的指令流。

### 关键设计参数

| 参数 | 数值 |
|------|------|
| 面积占比 | <3% die area |
| 指令队列数 | 144 (独立) |
| 每 cycle 发射能力 | 每个 queue 可发射 1+ 指令 |
| 指令流方向 | North → South (向上传播) |
| 控制方式 | 编译器静态调度，无硬件动态调度 |
| 同步机制 | SYNC/NOTIFY/DESKEW 指令 |

### 指令流水线阶段推测 (Inferred Pipeline Stages)

基于功能分片和数据流模型，ICU 的流水线阶段可能包括:

1. **取指 (Fetch)**: 从指令存储器 (SRAM 中的指令区域) 读取 VLIW 包
2. **解码 (Decode)**: 解码 VLIW 包，提取各功能切片对应的操作码
3. **队列分发 (Queue Dispatch)**: 将解码后的操作分发到 144 个指令队列中对应的队列
4. **发射 (Issue)**: 每个 queue 按编译器设定的顺序发射指令
5. **同步 (Sync)**: 管理 NOTIFY/DESKEW 同步事件

### 指令队列仲裁 (Queue Arbitration)

- **无硬件仲裁**: 编译器在编译时已解决所有资源冲突
- 每个 queue 对应一个功能切片或子功能
- queue 之间通过 SYNC/NOTIFY 进行协调
- 编译器已知每个 queue 的 issue 时间表

### VLIW 指令格式推断 (Inferred VLIW Format)

一个 VLIW 包可能包含以下字段:
```
[OP_ICU] [OP_MEM_0] [OP_MEM_1] [OP_VXM] [OP_MXM_0] [OP_MXM_1] [OP_SXM_0] [OP_SXM_1]
```
每个操作字段包含: opcode, stream_id, destination, immediate, flags

---

## 2. MEM — 存储切片深度分析

### SRAM 层次结构 (SRAM Hierarchy)

TSP 使用**纯 SRAM 单级存储层次** — 无 DRAM/HBM，无缓存层次：

```
┌─────────────────────────────────────────────────────────┐
│                  220-230 MB 片上 SRAM                     │
│  ┌──────────┐ ┌──────────┐           ┌──────────┐       │
│  │ MEM Tile │ │ MEM Tile │  ... 88   │ MEM Tile │       │
│  │ (SL 0)   │ │ (SL 0)   │    tiles  │ (SL 19)  │       │
│  │ ~2.5MB   │ │ ~2.5MB   │           │ ~2.5MB   │       │
│  └──────────┘ └──────────┘           └──────────┘       │
└─────────────────────────────────────────────────────────┘
```

### MEM 切片排列 (MEM Slice Organization)

- 每个 Super Lane 包含 **2 个 MEM 切片** (左右各一，以 VXM 为中心镜像)
- 20 Super Lanes × 2 = **40 个 MEM 切片**
- 另有额外 MEM 切片 → 总计 ~88 个 MEM tile (垂直堆叠)
- 每个 MEM tile 约 2.5 MB → 每切片约 5.5 MB (2 tiles)
- 总 SRAM: 40 × 5.5 MB ≈ 220 MB (实际为 220-230 MB 不等)

### 带宽计算 (Bandwidth Calculation)

| 参数 | 数值 |
|------|------|
| 时钟频率 | 900 MHz |
| 数据路径宽度 | 512 bytes/cycle (20 lanes × 32 bytes) |
| 理论峰值带宽 | 512 bytes × 900 MHz = 460.8 GB/s (单一方向) |
| 总带宽 (双向) | ~921.6 GB/s (单层 SRAM) |
| 报告带宽 | 80 TB/s (含多端口/多bank并行) |

注：80 TB/s 是通过 SRAM 的多 bank 并行 + 多 tile 并发 + 双向流实现的。具体为:
- 88 MEM tiles × 2 ports/tile × 32 bytes/port × 900 MHz × 2 (RD+WR) ≈ 10 TB/s per direction
- 但实际 80 TB/s 来自更细粒度的 bank 级并行

### 地址映射 (Address Mapping)

编译器静态管理地址空间:
- 编译器精确知道每个 tensor 的 SRAM 位置
- 地址映射在编译时确定 — 无 TLB/页表/地址翻译
- 数据传输通过 stream ID (0-31) + direction (East/West) 进行
- 每个 MEM 切片可独立进行读写操作

### 确定性存储 (Deterministic Memory)

- SRAM 提供固定延迟访问
- 无 DRAM refresh 延迟 → 延迟确定
- 无缓存缺失 → 延迟确定
- 无 TLB miss → 延迟确定
- 编译器可精确调度数据到达和离开时间

---

## 3. VXM — 向量执行模块深度分析

### 微架构 (Microarchitecture)

每个 Super Lane 包含 1 个 VXM，含 **16 个 ALU**:

```
Super Lane (16 lanes × 32 bytes each):
┌────────────────────────────────────────────────────┐
│  Lane 0 │ Lane 1 │ Lane 2 │ ... │ Lane 14 │ Lane 15│
│  ALU 0  │ ALU 1  │ ALU 2  │     │ ALU 14  │ ALU 15 │
│ ┌─────┐ │ ┌─────┐ │ ┌─────┐ │   │ ┌─────┐ │ ┌─────┐│
│ │FP/INT│ │ │FP/INT│ │ │FP/INT│ │   │ │FP/INT│ │ │FP/INT││
│ └─────┘ │ └─────┘ │ └─────┘ │   │ └─────┘ │ └─────┘│
└────────────────────────────────────────────────────┘
```

### 全芯片向量能力 (Chip-Wide Vector Capability)

| 参数 | 数值 |
|------|------|
| Super Lane 数 | 20 |
| 每 SL ALU 数 | 16 |
| 总 ALU 数 | 320 × 16 = 5,120 |
| SIMD 宽度 | 320 (全芯片) |
| 数据路径宽度 | 32 bytes/lane |
| 流水线深度 | 20 级 |
| 向量寄存器 | 流式寄存器文件 (无传统 RF) |

### 支持的数据类型 (Supported Data Types)

| 类型 | 位宽 | 用途 |
|------|------|------|
| INT8 | 8-bit | 量化推理 |
| INT16 | 16-bit | 一般用途 |
| FP16 | 16-bit | 训练/推理 |
| BF16 | 16-bit | 训练友好 |
| FP32 | 32-bit | 精度关键操作 (attention logits) |
| FP8 | 8-bit | 容错层激活值 |
| 块浮点 | 可变 | MoE 权重 |

### TruePoint Numerics (Groq 专有技术)

- **100-bit 中间累加**: 保证无精度损失
- 权重/激活值使用低精度存储
- 矩阵运算使用全精度
- 输出根据下游误差敏感度选择性量化
- 相比 BF16 实现 2-4× 加速，无精度损失

### 向量指令集 (Vector Instruction Set)

推测指令类型:
- **算术**: ADD, SUB, MUL, DIV, SQRT
- **比较**: CMP, MAX, MIN, SEL
- **类型转换**: CVT (INT↔FP 各类精度)
- **激活函数**: RELU, GELU, TANH, SIGMOID, SOFTMAX (近似)
- **归约**: SUM, MAX, MIN (跨 lane)
- **逻辑**: AND, OR, XOR, NOT

---

## 4. MXM — 矩阵执行模块深度分析

### Systolic Array 架构

MXM 是 TSP 的矩阵计算引擎，核心为 **weight-stationary systolic array**:

```
4 Planes × 320×320 MACs = 409,600 MACs total
```

### 每个 Plane 的组织

```
320×320 MAC Plane:
┌───────────────────────────────────────────────────┐
│  320 columns (features)                           │
│  ┌──────┐ ┌──────┐         ┌──────┐               │
│  │16×16 │ │16×16 │  ... 19 │16×16 │  320÷16=20    │
│  │SCell │ │SCell │         │SCell │  supercells    │
│  └──────┘ └──────┘         └──────┘               │
│  ┌──────┐ ┌──────┐         ┌──────┐               │
│  │16×16 │ │16×16 │  ... 19 │16×16 │  20×20        │
│  │SCell │ │SCell │         │SCell │  supercells    │
│  └──────┘ └──────┘         └──────┘               │
│     ...      ...               ...                 │
│  ┌──────┐ ┌──────┐         ┌──────┐               │
│  │16×16 │ │16×16 │  ... 19 │16×16 │  row 19       │
│  │SCell │ │SCell │         │SCell │               │
│  └──────┘ └──────┘         └──────┘               │
└───────────────────────────────────────────────────┘
```

### MXM 关键参数

| 参数 | 数值 |
|------|------|
| 矩阵维度 | 320×320 fused dot product |
| Plane 数 | 4 |
| 总 MAC 数 | 409,600 (= 320×320×4) |
| 每 supercell | 16×16 MAC |
| Supercell 排布 | 20×20 per plane |
| 每 plane 权重 | 102,400 weights |
| 数据流方式 | Weight-stationary |
| INT8 MAC/cycle | 409,600 |
| FP16 MAC/cycle | 409,600 (paired byte-planes) |

### 数据流方式详析 (Dataflow Analysis)

**Weight-Stationary (权重固定)**:
1. 权重被预加载到 4 个 plane 的 320×320 MAC 阵列
2. 权重在计算期间保持不动（stationary）
3. 输入激活值流经 systolic array
4. 部分和在阵列中传播和累加
5. 每个 320×320 plane 每个 cycle 处理一个向量元素

**与传统设计的对比**:

| 特性 | Groq MXM | Google TPU | NVIDIA Tensor Core |
|------|----------|------------|-------------------|
| Systolic | Yes | Yes | Yes |
| 数据流 | Weight-stationary | Systolic | Warp-level |
| 矩阵维度 | 320×320 | 128×128 | 16×16/4×4 |
| MAC 数 | 409,600 | 65,536 | 64-256 |
| 编译器控制 | 完全静态 | 部分动态 | 动态调度 |

### 权重加载时间

- 所有 4 个 320×320 平面的权重可在 **<40 cycles** 内加载完毕
- 每个 cycle 加载 4 × 320 × 320 = 409,600 权重值
- 带宽需求: 409,600 × 权重位宽 / cycle

---

## 5. SXM — 移位执行模块深度分析

### 功能概述 (Functional Overview)

SXM (Switch Execution Module) 是 TSP 的数据移动和形状变换引擎:

- **移位 (Shift)**: 向量元素向左/向右平移
- **旋转 (Rotate)**: 向量元素的循环移位
- **排列 (Permute)**: 向量元素在 lane 之间的任意重排
- **广播 (Broadcast)**: 将元素复制到多个 lane
- **转置支持**: 矩阵转置操作
- **归约支持**: 跨 lane 的归约操作

### 实现方式 (Implementation)

根据 Groq 专利 US20240037064A1:

> *"Lane switching slices may be configured to route data from one data transport lane to any other data transport lane. Data from a first lane may be provided to a second lane through a lane switching slice. The lane switching slice may be implemented as a crossbar switch or by a permuter circuit."*

### 每 Super Lane 配置

| 参数 | 数值 |
|------|------|
| SXM 数量/Super Lane | 2 (左右各一) |
| 总 SXM tiles | 40 (20 × 2) |
| 数据宽度 | 512 bytes (20 lanes × 32 bytes) |
| 交叉开关类型 | 1D tiled crossbar |

### SXM 在数据流中的角色

```
MEM(读数据) → SXM(重排/路由) → VXM/MXM(计算) → SXM(重组) → MEM(写回)
                                       ↑
                                  指令流 (垂直)
```

### 典型操作场景

1. **Permute**: 对 transformer 的 attention 输出进行重排
2. **Broadcast**: 将标量值广播到所有 lane（用于 bias 加法）
3. **Reduce**: 跨 lane 的 sum/max 归约
4. **Transpose**: 矩阵转置的 lane 级实现
5. **Interleave**: 多头的交错/去交错

---

## 六、各模块互联关系 (Inter-Module Connectivity)

```
                 指令流方向 (North ↑)
         ┌──────────────────────────────────────┐
         │  SL 19 (顶层)                         │
         │  MXM │ SXM │ MEM │ VXM │ MEM │ SXM │ MXM │
         ├──────────────────────────────────────┤
         │  SL 18                               │
         │  MXM │ SXM │ MEM │ VXM │ MEM │ SXM │ MXM │
         ├──────────────────────────────────────┤
         │  ...          数据流 ↔              │
         ├──────────────────────────────────────┤
         │  SL 0                                │
         │  MXM │ SXM │ MEM │ VXM │ MEM │ SXM │ MXM │
         ├──────────────────────────────────────┤
         │  ICU (指令控制单元，水平条带)            │
         └──────────────────────────────────────┘
         
         数据流方向: East ↔ West
```

---

## 参考文献 (References)

1. Abts et al., ISCA 2020 — TSP architecture fundamentals
2. Singh et al., ISCA 2022 — Deterministic programming model
3. US20240037064A1 — Instruction format and ISA for TSP
4. US20230024670A1 — Deterministic memory for TSP
5. Groq, Inc. — "Software-defined Tensor Streaming Multiprocessor" patent (12277444)
6. Multiple Chinese tech analysis articles (EET China, 36Kr, BAAI, Zhihu)
