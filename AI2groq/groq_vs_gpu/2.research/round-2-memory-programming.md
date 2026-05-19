# Round 2: Memory Hierarchy & Programming Model Comparison

> 搜索时间: 2026-05-18
> 范围: 存储层次、数值格式、编程模型、编译器哲学

## 1. Groq TSP Memory Hierarchy

### 1.1 SRAM-Only Design
Groq TSP 采用 **纯 SRAM 片上存储** 设计，完全无 DRAM/HBM：

| 层级 | 容量 | 带宽 | 延迟 | 说明 |
|------|:----:|:----:|:----:|------|
| MEM Slice SRAM | 220 MB | 80 TB/s | 固定（几周期） | 88 独立 SRAM bank，编译器静态分配 |
| Stream Registers | — | — | 0 周期 | 32 eastbound + 32 westbound per lane |
| No L1/L2 Cache | N/A | N/A | N/A | 无缓存层次 |
| No DRAM/HBM | N/A | N/A | N/A | 无片外内存 |

### 1.2 流式数据模型
- 数据从 MEM 读出后以流（stream）形式在所有计算切片间传递
- MEM → VXM/MXM/SXM 直接推送，无需寄存器文件中转
- Stream 携带 flow ID (0-31) 和方向（east/west）
- 编译器精确调度每个数据元素到达每个计算单元的时间

### 1.3 TruePoint 数值格式
| 格式 | 用途 | 说明 |
|------|------|------|
| FP32 | Attention logits, softmax | 高精度关键路径 |
| BlockFP | MoE 权重 | 分块共享指数，2-4x 加速无损 |
| FP8 | 激活值 | E4M3/E5M2 混合精度 |
| INT8 | 推理量化 | 750 TOPS |
| **100-bit 累加** | 所有运算 | 内部精度，结果可转 FP32/BF16 |

### 1.4 多芯片扩展
- Chip-to-Chip (C2C) Links: 每 TSP 11 条物理链路（7 local + 4 global）
- 8 TSP/node，最多 145 racks (10,440 TSPs)
- 编译时静态调度 Send/Recv，无运行时握手，包开销仅 2.5%

---

## 2. GPU Memory Hierarchy

### 2.1 HBM 演进

| 代际 | 带宽/GPU | 容量/GPU | 代表 GPU |
|------|:--------:|:--------:|----------|
| HBM2 | 900 GB/s | 16-32 GB | V100 |
| HBM2e | 2 TB/s | 40-80 GB | A100 |
| HBM3 | 3.35 TB/s | 80 GB | H100 |
| HBM3e | 4.8 TB/s | 141 GB | H200 |
| HBM3e | 8 TB/s | 192 GB | B200 |

### 2.2 缓存层次对比

| 层级 | GPU | 容量 | 延迟 | 管理方式 |
|------|-----|:----:|:----:|----------|
| Register File | 每 SM | 64K-256K regs | 0 周期 | 编译器分配 |
| Shared Mem/L1 | 每 SM | 128-256 KB | ~20 周期 | 可配置（SW 或 HW） |
| L2 Cache | 全局 | 40-96 MB | ~200 周期 | HW 管理 |
| HBM | 全局 | 80-192 GB | ~400-800 周期 | HW 管理 |

### 2.3 GPU 延迟隐藏机制
- 零开销 warp 切换：切换上下文无需保存/恢复（寄存器在片上）
- 大量并发线程（H100: 最大 53,248 线程）隐藏 HBM 访问延迟
- L1/L2 cache 减少平均访问延迟
- 缺点是延迟可变（cache miss, DRAM refresh, bank conflict）

---

## 3. 编程模型对比

### 3.1 GroqFlow / MLIR 编译器

| 特性 | 说明 |
|------|------|
| 输入 | PyTorch, Keras, ONNX |
| 编译流程 | 图捕获 → MLIR 重写 → 静态张量放置 → 周期级调度 → 二进制 |
| 调度方式 | 编译时确定每条指令在哪个周期执行在哪个功能单元 |
| 多芯片 | 编译器自动将计算图切分到多个 TSP |
| 确定性 | 调度结果独立于输入数据，每次运行完全相同 |

关键特点：
- 编译器需要解决复杂的 ILP/CSP（整数线性规划/约束满足）问题
- 144 条指令队列，编译器精确控制每周期每条队列的发射
- 无需运行时调度器、无需仲裁器

### 3.2 CUDA 编程模型

| 特性 | 说明 |
|------|------|
| 线程层次 | Grid → Block → Warp (32 threads) → Thread |
| 调度层次 | GigaThread Engine → Block Scheduler → Warp Scheduler |
| 内存模型 | Global → Shared → Local (register) — 程序员显式管理 |
| 同步 | __syncthreads (block内), atomic operations (全局) |
| 延迟隐藏 | 硬件 warp 调度，零成本上下文切换 |

CUDA 的 Three-Level Scheduler:
1. **GigaThread Engine**: 将 thread blocks 分发到 SMs
2. **Block Scheduler**: 每个 SM 管理多个 thread blocks
3. **Warp Scheduler**: 每 cycle 选择一个 ready warp 发射

### 3.3 编译器哲学：静态 vs 动态

| 维度 | Groq TSP | NVIDIA GPU |
|------|----------|------------|
| 调度时机 | 编译时（静态） | 运行时（动态） |
| 延迟确定性 | 完全确定（所有内存延迟固定） | 不确定（缓存/HBM 抖动） |
| 编译器复杂度 | 极高（ILP/CSP 求解） | 中等 |
| 硬件复杂度 | 极低（无调度器/仲裁器） | 高（复杂 warp 调度器） |
| 适用场景 | 固定计算图（推理） | 通用并行计算 |
| 分支处理 | 预测执行（计算所有分支） | SIMT divergence（路径串行化） |
| 收敛趋势 | 编译器支持更多动态特性 | 运行时支持更多确定性（CUDA Graphs） |

### 3.4 其他编程框架

| 框架 | 抽象层次 | 性能 | 适用场景 |
|------|---------|:----:|----------|
| **Triton** | 类 Python，block 级编程 | 90-96% cuBLAS | 自定义算子开发 |
| **OpenCL** | 底层跨平台 | 50-80% CUDA | 异构计算 |
| **SYCL** | C++ 单源跨平台 | 60-85% CUDA | 跨厂商移植 |

---

## 4. 关键发现

1. **Groq 的成功关键不是带宽本身，而是确定性**：编译器精确调度消除了运行时开销，使 80 TB/s SRAM 带宽被充分利用
2. **GPU 用复杂度换灵活性**：复杂的 warp 调度器 + 缓存层次 + 一致性协议使 GPU 能处理任意计算模式，但代价是延迟可变
3. **收敛趋势明显**：GPU 侧通过 CUDA Graphs/FlashAttention 引入更多确定性；Groq 侧通过编译器支持更多动态特性
4. **编程模型反映硬件哲学**：GroqFlow 的"编译一次，运行确定" vs CUDA 的"运行时调度，延迟隐藏"

Sources: Groq ISCA 2020/2022, Zellic Research, NVIDIA CUDA Programming Guide, GroqFlow GitHub, Triton documentation.
