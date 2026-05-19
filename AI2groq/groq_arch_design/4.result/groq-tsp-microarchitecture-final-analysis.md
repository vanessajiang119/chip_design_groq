# Groq TSP 微架构深度分析 — 最终综合报告
# Groq TSP Microarchitecture Deep Analysis — Final Synthesis Report

> 创建时间: 2026-05-19T1800
> 分析层级: Layer 1 (TSP 微架构) + Layer 2 (五模块详细设计)
> 流程: Planning → Research (3 Rounds) → Working (5 Sub-modules) → Result

---

## 一、执行摘要 (Executive Summary)

本报告对 Groq TSP (Tensor Streaming Processor) 芯片的微架构进行了系统性的深度分析。TSP 是一颗 **14nm、900MHz、725mm²** 的 AI 推理加速器，其核心创新是 **功能分片 (Functional Slicing)** 架构 — 将传统处理器核心按功能类型分解为独立的垂直切片 (ICU, MEM, VXM, MXM, SXM)，由编译器完全静态调度。

### 核心数据

| 参数 | 数值 |
|------|------|
| 制程 | 14nm |
| Die 尺寸 | 25mm × 29mm (725 mm²) |
| 频率 | 900 MHz (最高 1.25 GHz) |
| 片上 SRAM | ~220-230 MB |
| 内存带宽 | 80 TB/s |
| SIMD 通道 | 320 (20 SL × 16 lanes) |
| 指令队列 | 144 (独立) |
| MAC 总数 | 409,600 (4 planes × 320 × 320) |
| 向量 ALU | 5,120 (320 × 16) |
| 流水线深度 | 20 级/功能切片 |
| TDP | ~300W |
| INT8 性能 | 750-1000 TOPS |
| FP16 性能 | 188-205 TFLOPS |

---

## 二、架构总览 (Architecture Overview)

### 2.1 功能分片架构 (Functional Slicing)

TSP 将芯片组织为 2D 网格，列 (slice) 按功能划分，行 (tile/Super Lane) 按数据流划分：

```
指令流 (North ↑)           数据流 (East ↔ West)
                           ←───────────────→
┌──────┬──────┬──────────┬──────────────────┬──────────┬──────┬──────┐
│      │      │          │  20 Super Lanes   │          │      │      │
│ MXM  │ SXM  │   MEM    │   (16 lanes each) │   MEM    │ SXM  │ MXM  │
│      │      │          │                   │          │      │      │
│ 矩阵  │ 开关  │  存储    │  VXM (向量引擎)   │  存储    │ 开关  │ 矩阵  │
│ ×2   │ ×2   │   ×2     │    ×1 (中心)      │   ×2     │ ×2   │ ×2   │
│      │      │          │                   │          │      │      │
└──────┴──────┴──────────┴──────────────────┴──────────┴──────┴──────┘
                                        ↑
                                   以 VXM 为中心镜像
                                   两个准独立"半球"

┌──────────────────────────────────────────────────────────────┐
│                       ICU (指令控制单元)                        │
│               <3% die area | 144 queues | 集中控制             │
└──────────────────────────────────────────────────────────────┘
```

### 2.2 核心设计原则

1. **完全确定性执行**: 消除所有响应式硬件 (无缓存、无仲裁器、无分支预测、无乱序执行)
2. **编译器调度一切**: 编译器在编译时精确调度每条指令和每个数据移动的 cycle
3. **流式数据模型**: 数据以流的方式在生产者和消费者之间传递，无需寄存器文件中间存储
4. **功能分片**: 同功能单元垂直堆叠，控制逻辑共享，面积效率最大化
5. **链式执行**: 结果直接从功能单元流向下一个功能单元

---

## 三、五模块详细分析 (Five Modules Deep Analysis)

### 3.1 ICU — 指令控制单元

**关键参数**:
- 面积占比: <3% die (< ~8 mm²)
- 指令队列: 144（每队列 32-64 条指令深度）
- 指令格式: VLIW 包 (含所有功能切片的操作字段)
- 同步机制: SYNC (暂停) / NOTIFY (恢复) / DESKEW (多 TSP 对齐)

**工作原理**:
ICU 位于芯片底部，作为水平条带控制所有功能切片。指令从 ICU 出发，沿垂直方向 (North) 向上传播，每 cycle 传播一个 Super Lane。从 ICU 到顶层 SL 19 需要 20 cycles。ICU 内部的 144 个独立指令队列由编译器静态管理 — 编译器在编译时已精确决定了每个 queue 在每个 cycle 应该发射什么指令。

**关键创新**:
- 集中控制逻辑节省了大量芯片面积 (传统设计中每个核心 15-25% 用于控制)
- 144 队列并行发射实现高指令级并行 (ILP)
- MIMD 风格：不同功能切片可同时执行不同指令

---

### 3.2 MEM — 存储切片

**关键参数**:
- 总容量: 220-230 MB SRAM
- MEM 切片: 40 (20 SL × 2)
- 每切片容量: ~5.5 MB (2 tiles × ~2.75 MB)
- 总带宽: 80 TB/s
- 存储层次: 单级 SRAM (无缓存、无 DRAM)
- 地址管理: 编译器静态分配 (无 MMU/TLB)

**工作原理**:
每个 Super Lane 包含 2 个 MEM 切片 (左右对称)。数据通过 Stream ID (0-31) + 方向 (E/W) 进行寻址，而非传统的内存地址。MEM 切片作为数据流的生产者和消费者 — 读操作将 SRAM 数据加载到数据流中，写操作将流数据存储回 SRAM。

**80 TB/s 带宽的实现**:
- 88 MEM tiles × 2 ports × 32 bytes × 900 MHz × 2 (RD+WR) ≈ 10 TB/s 基础带宽
- 乘以细粒度 bank 级并行 (每 tile 8-16 banks) → 80 TB/s

**与 GPU 对比**:
- TSP: 230 MB SRAM, 80 TB/s, ~5-10ns 延迟, 完全确定性
- H100: 80 GB HBM + ~50 MB cache, ~3 TB/s, ~100-200ns, 统计性

---

### 3.3 VXM — 向量执行模块

**关键参数**:
- 每 Super Lane: 16 ALU × 32 bytes/lane
- 全芯片: 320 ALU × 16 子单元 = 5,120 运算单元
- 向量宽度: 320 elements/cycle (全芯片 SIMD)
- 流水线深度: 20 级
- 支持精度: INT8/INT16/FP16/BF16/FP32/FP8
- 专有技术: TruePoint Numerics (100-bit 中间累加)

**工作原理**:
VXM 位于每个 Super Lane 的中心，作为向量运算引擎。所有 16 lanes 在每 cycle 执行同一条指令 (SIMD)。VXM 从东西方向的数据流接收操作数，执行向量运算后，结果直接流向 MEM (存储) 或 MXM/SXM (进一步处理)，无需寄存器文件中间步骤。

**TruePoint Numerics**:
Groq 的专有精度技术，使用 100-bit 累加器保证无精度损失。权重和激活值可用 INT8/FP16 低精度存储，累加时扩展为 100-bit，输出时按需量化。相比 BF16 精度无损且速度提升 2-4×。

---

### 3.4 MXM — 矩阵执行模块

**关键参数**:
- 架构: Weight-stationary systolic array
- 每 MXM: 4 planes × 320×320 = 409,600 MACs
- 每 Super Lane: 2 MXM (左右)
- 数据流: Weight-stationary (权重固定，激活值流过)
- 权重加载: 4 planes × 102,400 weights/plane < 40 cycles
- Systolic 子单元: 16×16 supercell

**工作原理**:
MXM 采用经典的 systolic array 架构，权重预加载到 4 个 320×320 MAC 平面中保持不动 (weight-stationary)，输入激活值从数据流进入并在阵列中流动，部分和在 vertical 方向传播累加。

**4 Planes 的用途**:
1. **大矩阵分解**: 4 个 320×320 块独立运算
2. **FP16 精度**: 4 planes 分别处理高低字节后组合
3. **批量并行**: 4 个 batch 共享权重

**与传统对比**:
| 特性 | TSP MXM | Google TPU | NVIDIA Tensor Core |
|------|---------|------------|-------------------|
| 矩阵维度 | 320×320 | 128×128 | 16×16 |
| 数据流方式 | Weight-stationary | Systolic | SIMT warp-level |
| 编译器控制 | 完全 | 部分 | 动态 |

---

### 3.5 SXM — 移位/交换执行模块

**关键参数**:
- 每 Super Lane: 2 SXM (左右)
- 全芯片 SXM: 40
- 核心实现: Tiled 1D crossbar / permuter circuit
- 延迟: 1-2 cycles (大部分操作)
- 额外功能: C2C 片间通信, PCIe 接口

**工作原理**:
SXM 实现了 lane 之间的任意数据重排。数据从 16 lanes 进入 SXM，通过 tiled crossbar 重新排列后输出。编译器在编译时配置排列模式 (permute pattern) — 模式一旦设置即可在该数据流传输期间保持不变。

**核心功能**:
- Shift/Rotate (移位/旋转)、Permute (任意排列)、Broadcast (广播)
- Gather/Scatter (收集/散播)、Transpose (转置)、Interleave (交错)
- 多 TSP 互联的 C2C 接口

**关键技术实现**:
Crossbar 采用 tiled 结构减少面积: 每 16×16 lane block 内实现全 crossbar，block 间使用有限连接。这种设计在灵活性和面积之间取得平衡。

---

## 四、数据流模型详解 (Dataflow Model)

### 4.1 正交数据流 (Orthogonal Dataflow)

TSP 最独特的设计是**指令流和数据流的正交**:

```
          指令流 (垂直, North ↑)
          每个 cycle 一个 SL
          ┌───┐
SL 19 ◄───┤   │───► 数据流
          └───┘
           ...
          ┌───┐
SL 1 ◄────┤   │───►
          └───┘
          ┌───┐
SL 0 ◄────┤   │───►
          └───┘
          ┌──────────────────────┐
          │  ICU (指令发射)       │
          └──────────────────────┘
          
数据流: 水平 (East ↔ West), 32 bytes/lane/cycle
指令流: 垂直 (North), 所有 SL 接收同一指令
```

### 4.2 Wavefront 传播

```
时间 t=0:  ICU 发射指令到 SL 0
           SL 0 MXM 开始计算

时间 t=1:  ICU 发射到下一条指令到 SL 0
           SL 0 MXM 继续, SL 1 MXM 开始

时间 t=2:  SL 0、SL 1、SL 2 同时在流水线中
           ...
时间 t=19: 所有 20 个 SL 同时在流水线中
           
→ 稳态: 每个 SL 处于流水线的不同阶段
→ 类似"波纹"wavefront 在垂直方向传播
```

### 4.3 链式执行 (Chaining)

```
MEM(加载A) → SXM(路由) → MXM(Q×K) → VXM(Softmax) → ...
  ↑            ↑            ↑           ↑
  数据源       数据重排     矩阵乘      激活函数

关键: 中间结果从不写入存储器 — 直接在功能单元间流动
```

---

## 五、编译器角色 (Compiler Role)

### 5.1 编译器可见资源

```
编译器在编译时具有完全的硬件可见性:
├── 320 SIMD 通道
├── 144 个独立指令队列
├── 64 个逻辑流/通道 (32E + 32W)
├── 220 MB SRAM 地址空间
├── 所有指令的精确延迟
├── 所有功能切片的资源冲突
└── 所有数据流的路由路径
```

### 5.2 静态调度算法

```
Input: 神经网络计算图 (ONNX/TensorFlow/MLIR)
Output: 每条指令的精确 cycle 级时间表

步骤:
1. 前端: MLIR 降级 → Tensor → Stream IR
2. 计算图 → 数据流图 (DFG)
3. 拓扑排序 + 资源分配
4. 静态列表调度 (List Scheduling):
   - 每个操作分配执行时间
   - 解决资源冲突 (cycle 偏移)
   - 分配流 ID 和方向
5. 插入同步指令 (SYNC/NOTIFY/DESKEW)
6. 生成 VLIW 指令包
7. 生成 SRAM 地址映射
```

### 5.3 与动态调度的对比

| 特性 | TSP (静态调度) | GPU (动态调度) |
|------|--------------|---------------|
| 调度时机 | 编译时 | 运行时 |
| 调度器 | 编译器 | 硬件 warp scheduler |
| 资源冲突解决 | 编译时预测 | 硬件仲裁 |
| 适应性 | 固定程序最优 | 动态变化适应 |
| 硬件占用 | 无调度硬件开销 | ~10-20% area |
| 可预测性 | Cycle 级精确 | 统计性 |

---

## 六、面积与功耗分布 (Area & Power Distribution)

### 面积分布 (725 mm² total)

| 模块 | 估算面积 | 占比 | 说明 |
|------|---------|------|------|
| SRAM (MEM) | ~290-360 mm² | ~40-50% | 230 MB + ECC + 冗余 |
| MXM (矩阵乘) | ~145-180 mm² | ~20-25% | 409,600 MACs |
| VXM (向量) | ~72-108 mm² | ~10-15% | 5,120 ALUs + 数据路径 |
| SXM (交叉开关) | ~72 mm² | ~10% | Crossbar + C2C + PCIe |
| ICU (控制) | ~4-8 mm² | <3% | 指令队列 + 解码 |
| 其他 (时钟/布线/I/O) | ~72-108 mm² | ~10-15% | |

### 功耗分布 (300W TDP)

| 模块 | 估算功耗 | 占比 |
|------|---------|------|
| SRAM 阵列 | ~120-150W | ~40-50% |
| MXM MAC 阵列 | ~60-75W | ~20-25% |
| VXM ALU | ~30-45W | ~10-15% |
| SXM Crossbar | ~30W | ~10% |
| ICU | ~3-5W | ~1-2% |
| 时钟/布线/漏电 | ~30-45W | ~10-15% |

---

## 七、关键设计决策权衡 (Key Trade-offs)

### 7.1 SRAM-only vs DRAM

| 权衡 | SRAM (选择) | DRAM (放弃) |
|------|------------|------------|
| 确定性 | 固定延迟 ✓ | 可变延迟 ✗ |
| 带宽 | 80 TB/s ✓ | ~3 TB/s ✗ |
| 延迟 | 5-10ns ✓ | 100-200ns ✗ |
| 容量 | 230 MB ✗ | 80 GB ✓ |
| 成本 | 高昂 ✗ | 便宜 ✓ |

### 7.2 功能分片 vs 传统多核

| 权衡 | 功能分片 | 传统多核 |
|------|---------|---------|
| 控制逻辑效率 | <3% ✓ | 15-25% ✗ |
| 同构性 | 列内同构 ✓ | 核内异构 |
| 扩展性 | 增加 tile 数 | 增加核数 |
| 灵活性 | 流式模型受限 ✗ | 通用 ✓ |

### 7.3 编译时调度 vs 运行时调度

| 权衡 | 编译时 | 运行时 |
|------|-------|-------|
| 可预测性 | Cycle 级 ✓ | 统计性 ✗ |
| 硬件效率 | 高 (无调度硬件) ✓ | 中 (有调度硬件) ✗ |
| 灵活性 | 固定程序最优 ✗ | 动态适应 ✓ |
| 编译器复杂度 | 极高 ✗ | 低 ✓ |

---

## 八、性能特征 (Performance Characteristics)

### 8.1 延迟分析

| 操作 | 延迟 (cycles) | 延迟 (ns@900MHz) |
|------|-------------|-----------------|
| SRAM 读 | 2-3 | 2.2-3.3 |
| SIMD 向量 ADD | 1-2 | 1.1-2.2 |
| FP16 向量 MUL | 2-3 | 2.2-3.3 |
| FP32 向量 FMA | 4-5 | 4.4-5.6 |
| 矩阵乘 (320×320) | 320+ | 355+ |
| 指令垂直传播 (SL 0→19) | 20 | 22.2 |
| 片内总延迟 (LD→结果) | ~30-50 | ~33-56 |
| 片间 C2C 传播 | 50-100 | ~55-111 |

### 8.2 吞吐量

| 模型 | 批处理 | 吞吐量 | 延迟 |
|------|--------|--------|------|
| ResNet-50 | batch-1 | 20,400 img/s | <49 μs |
| BERT-base | batch-1 | — | 130 μs tail |
| Mixtral 8×7B | — | 480 tokens/s | — |

---

## 九、局限性与未来方向 (Limitations & Future)

### 当前局限

1. **SRAM 容量限制**: 230 MB 无法容纳大模型 (如 Llama 2 70B 需 ~140 GB)
2. **编译器负担**: 静态调度对编译器要求极高，编译时间长
3. **灵活性不足**: 不规则控制流效率低
4. **成本**: 14nm SRAM 高昂，转换为更先进制程存在挑战
5. **多芯片扩展**: 需要高效的多 TSP 互联来弥补单芯片容量不足

### 未来方向

1. **更小制程**: 7nm/5nm 可大幅提升 SRAM 密度和频率
2. **HBM 混合**: 结合 SRAM 的确定性和 HBM 的大容量
3. **编译器自动化**: ML-driven 静态调度加速
4. **稀疏性支持**: 利用结构化/非结构化稀疏性提升效率
5. **训练支持**: 扩展确定性模型支持反向传播、梯度累积

---

## 十、结论 (Conclusion)

Groq TSP 通过**功能分片**和**完全确定性执行**实现了独特的架构创新:

1. **面积效率**: ICU <3% 控制逻辑占比，释放更多面积用于计算和存储
2. **确定性**: 编译器可精确预测每个程序的执行时间 — 这在传统架构中不可能实现
3. **高带宽**: 80 TB/s 纯 SRAM 带宽，远超 HBM
4. **低延迟**: 5-10ns 内存访问延迟，比 HBM 低 20×
5. **高利用率**: 编译器全局优化实现高硬件利用率

这种设计特别适合**延迟敏感的推理场景** (如 LLM 推理)，但在需要大容量存储或动态控制流的场景中受限于 SRAM 容量和确定性约束。

---

## 附录：关键数据汇总 (Key Data Summary)

### A. 芯片物理参数

| 参数 | 值 |
|------|-----|
| 制程 | 14nm FinFET |
| Die 尺寸 | 25mm × 29mm |
| Die 面积 | ~725 mm² |
| 晶体管数 | ~数亿 |
| 频率 | 900 MHz (nominal) |
| TDP | ~300W |

### B. 存储系统

| 参数 | 值 |
|------|-----|
| SRAM 总容量 | 220-230 MB |
| MEM 切片数 | 40 (20 SL × 2) |
| 每切片容量 | ~5.5 MB |
| 总带宽 | 80 TB/s |
| 访问延迟 | 2-3 cycles |
| 并发度 | 176 路访问 (88 × 2) |

### C. 计算能力

| 精度 | 峰值性能 | MAC 利用率 |
|------|---------|-----------|
| INT8 | 750-1000 TOPS | 409,600/cycle |
| FP16 | 188-205 TFLOPS | 409,600/cycle |
| FP32 (VXM) | ~5 GFLOPS | 5,120 ops/cycle |

### D. 控制系统

| 参数 | 值 |
|------|-----|
| 指令队列 | 144 |
| 每队列发射 | 1+ 指令/cycle |
| 总发射带宽 | 144+ 指令/cycle |
| 同步机制 | SYNC/NOTIFY/DESKEW |
| 控制面积 | <3% die |

---

## 参考文献 (References)

1. Abts, D. et al., "Think Fast: A Tensor Streaming Processor (TSP) for Accelerating Deep Learning Workloads", ISCA 2020
2. Singh, S. et al., "The Virtuous Cycles of Determinism: Programming Groq's Tensor Streaming Processor", ISCA 2022
3. US20240037064A1 — "Instruction Format and Instruction Set Architecture for TSP", Groq Inc.
4. US20230024670A1 — "Deterministic Memory for Tensor Streaming Processors", Groq Inc.
5. US12277444B2 — "Software-defined Tensor Streaming Multiprocessor for Large-scale ML", Groq Inc.
6. Groq Blog — "Inside the LPU: Deconstructing Groq's Speed"
7. Zellic Research — "How Is Groq So Fast? An Overview of Groq's TSP Architecture"
8. D. Abts, Stanford EE380 — "Dataflow for Convergence of AI and HPC: GroqChip"
9. EET China — "深度拆解 Groq LPU 架构"
10. 36Kr — "揭开 Groq LPU 神秘面纱"
