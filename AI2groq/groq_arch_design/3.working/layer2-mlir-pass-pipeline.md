# Layer 2 Deep Dive: MLIR Pass Pipeline 设计
## MLIR Pass Pipeline Design for Groq TSP

**Created:** 20260519-1030  
**Analyst:** Groq Compiler Architecture Expert  
**Layer:** 2 (Deep Technical Analysis)

---

## 1. MLIR 框架回顾 / MLIR Framework Recap

MLIR (Multi-Level Intermediate Representation) 是 LLVM 项目下的编译器基础设施框架，核心概念：

- **Dialect** (方言): 一组类型化操作 (ops)、类型、属性的命名空间
- **Operation** (操作): 带操作数、结果、区域 (region) 的有向图节点
- **Pass** (优化遍): 对 IR 图执行变换/分析的模块
- **Conversion** (转换): 在不同 dialect 间翻译

Groq 利用 MLIR 的这些核心抽象来构建其前端编译流。

---

## 2. Groq 的 MLIR Dialect 层次

### 2.1 Dialect 层次结构 (推测)

基于 MLIR 的一般实践和 Groq TSP 硬件特性，可以推断其 dialect 层次：

```
Top-Level (框架层)
    HLO Dialect / StableHLO     ← PyTorch/TF 的顶层语义
    TOSA Dialect                ← 标准 ML 算子集 (可选)
         │
         ▼
Middle-Level (Groq 抽象层)
    GroqGraph Dialect           ← 图级算子、tensor 形状、数据类型
    GroqLinalg Dialect          ← 线性代数级 (matmul, conv, reduce)
    GroqLayout Dialect          ← 内存布局与数据移动表达
         │
         ▼
Low-Level (硬件感知层)
    GroqSlice Dialect           ← TSP 功能列级别 (MXM_op, VXM_op, MEM_op, SXM_op)
    GroqStream Dialect          ← stream 级数据流 (SR 分配、stream 操作)
    GroqQueue Dialect           ← 指令队列级 (queue 分配、SYNC)
         │
         ▼
Target (发射层)
    GroqEmission Dialect        ← 接近 TSP ISA 的微操作
    (→ Haskell Backend 接受此 IR)
```

### 2.2 关键 Dialect 详解

#### GroqGraph Dialect

```
功能: 表达 ML 计算图，不包含硬件细节

Ops:
  %g.emm = groq_graph.matmul %A, %B
      : (tensor<256x512xfp16>, tensor<512x128xfp16>) -> tensor<256x128xfp16>
  
  %g.act = groq_graph.relu %g.emm
      : tensor<256x128xfp16> -> tensor<256x128xfp16>

属性:
  - 张量形状 (static shapes only — 确定性要求)
  - 数据类型 (fp16/bf16/int8)
  - 布局 (NHWC/NCHW)
```

#### GroqSlice Dialect

```
功能: 表达 TSP 功能列级别的操作，每个 op 对应一个具体 slice 类型

Slice 类型映射:
  MXM_op : 矩阵乘/卷积/线性层   → MXM slice
  VXM_op : 向量操作/激活/batch norm → VXM slice
  MEM_op : 内存读写              → MEM slice
  SXM_op : 数据重排/移位/转换    → SXM slice
  
Ops:
  %m.result = groq_slice.mxm %A_tile, %B_tile
      : !groq_slice.mxm, memref<320x320xfp16>, memref<320x320xfp16> -> memref<320x320xfp16>
  
  %v.result = groq_slice.vxm.relu %m.result
      : !groq_slice.vxm, memref<320x320xfp16> -> memref<320x320xfp16>
```

#### GroqStream Dialect

```
功能: 表达数据在 TSP 芯片上的流式移动

关键概念:
  - Stream ID: 每个逻辑通道的 64 个 stream (32E + 32W)
  - Stream 类型: eastbound (右移), westbound (左移), local (本 tile)
  - Stream 生命周期: 从 MEM load 到 MEM store 之间的时序区间

Ops:
  %s = groq_stream.alloc {direction = "east", channel = 3}
  groq_stream.send %s, %val {from = "vxm_3", to = "mxm_5", cycle = 42}
  groq_stream.recv %s {at = "mxm_5", cycle = 47}
  groq_stream.free %s
```

---

## 3. Pass Pipeline 详细设计

### 3.1 整体流水线

```
Phase 1: 图级优化 (Graph-Level Optimization)
  ┌─────────────────────────────────────┐
  │ groq-canonicalize                   │  规范折叠
  │ groq-inline                         │  内联子图
  │ groq-constant-fold                  │  常量折叠 (权重折叠)
  │ groq-dce                            │  死代码消除
  │ groq-eliminate-dead-tensors         │  无效中间张量删除
  └─────────────────────────────────────┘

Phase 2: 稀疏性优化 (Sparsity Optimization) [可选]
  ┌─────────────────────────────────────┐
  │ groq-detect-sparse-pattern          │  检测稀疏模式
  │ groq-insert-sparse-ops              │  插入稀疏操作
  │ groq-skip-zero-macs                 │  跳过零值 MAC 操作
  └─────────────────────────────────────┘

Phase 3: 算子融合 (Operator Fusion)
  ┌─────────────────────────────────────┐
  │ groq-fuse-mxm-vxm                   │  MXM+VXM 融合 (减少中间张量)
  │ groq-fuse-activation                │  Activation 融合 (ReLU等)
  │ groq-fuse-batch-norm                │  BN 融合到卷积
  │ groq-fuse-conv-bias                 │  卷积+偏置融合
  └─────────────────────────────────────┘

Phase 4: 布局优化 (Layout Optimization)
  ┌─────────────────────────────────────┐
  │ groq-analyze-access-pattern         │  分析数据访问模式
  │ groq-choose-layout                  │  选择最佳布局
  │ groq-insert-layout-transpose        │  插入布局转置 op
  │ groq-eliminate-redundant-transpose  │  消除冗余转置
  └─────────────────────────────────────┘

Phase 5: 类型提升 (Type Promotion / FP16)
  ┌─────────────────────────────────────┐
  │ groq-promote-to-fp16                │  FP32 → FP16
  │ groq-insert-quantize-dequantize     │  INT8 量化插入
  │ groq-verify-precision               │  精度验证
  └─────────────────────────────────────┘

Phase 6: 图分区 (Graph Partition)
  ┌─────────────────────────────────────┐
  │ groq-partition-across-chips         │  跨多芯片分区
  │ groq-insert-inter-chip-send-recv    │  插入芯片间通信
  │ groq-balance-chip-load              │  跨芯片负载均衡
  │ groq-partition-to-queues            │  映射到 144 队列
  └─────────────────────────────────────┘

Phase 7: Lower to Hardware Dialect
  ┌─────────────────────────────────────┐
  │ convert-groq-graph-to-slice         │  Graph → Slice 级
  │ convert-groq-slice-to-stream        │  Slice → Stream 级
  │ convert-groq-stream-to-queue        │  Stream → Queue 级
  │ allocate-slice-resources            │  分配 slice 资源
  │ allocate-stream-registers           │  分配 stream registers
  └─────────────────────────────────────┘

Phase 8: 验证 (Verification)
  ┌─────────────────────────────────────┐
  │ groq-verify-op-support              │  算子支持验证
  │ groq-verify-stream-bounds           │  Stream 不溢出
  │ groq-verify-timing-consistency      │  时序一致性
  └─────────────────────────────────────┘

  ↓ IR emitted to Haskell backend
```

### 3.2 关键 Pass 详解

#### `groq-fuse-mxm-vxm`

算子融合是 ML 编译器中最重要的优化。在 TSP 上，MXM（矩阵乘法）和 VXM（向量操作）的融合可以避免中间张量写回 SRAM：

```
融合前:
  MXM:    C[M,N] = A[M,K] @ B[K,N]
  Write:  MEM[C] = C                      # 写入 SRAM
  Read:   MEM[C] → VXM                    # 从 SRAM 读取
  VXM:    D[M,N] = ReLU(C[M,N])           # 逐元素操作
  Write:  MEM[D] = D

融合后:
  MXM:    C[M,N] = A[M,K] @ B[K,N]
  Stream: C → VXM directly (stream, 无需 SRAM)
  VXM:    D[M,N] = ReLU(C[M,N])
  Write:  MEM[D] = D
  
  节省: 2 次 SRAM 访问 (一次写入 + 一次读取)
```

#### `groq-partition-to-queues`

这个 Pass 将 DAG 操作分配到 144 个指令队列中：

```
分配策略:
  1. 按功能列类型分组: 所有 MXM 操作 → MXM 队列池
  2. 按 tile 行分配: 考虑数据 locality
  3. 按依赖链分配: 相关操作放同一队列减少同步
  4. 负载均衡: 每个队列的指令数大致平衡
  
约束检查:
  - 每个队列 ≤ 硬件队列深度
  - 同队列内指令顺序满足依赖
  - 跨队列同步通过 SYNC/NOTIFY
```

---

## 4. MLIR 前端与 Haskell 后端的接口

### 4.1 IR 传输格式

MLIR 前端输出给 Haskell 后端的 IR 格式推测：

```
可能格式 1: MLIR 文本格式 (*.mlir)
  ─ 标准 MLIR 人类可读格式
  ─ Haskell 后端解析 MLIR AST

可能格式 2: LLVM 字节码 (*.bc)
  ─ 编译为 LLVM IR 再序列化
  ─ Haskell 通过 FFI 调用 LLVM 解析器

可能格式 3: 自定义协议缓冲区
  ─ Protobuf 格式传输 Groq IR
  ─ 性能最优，不易读

最可能的是 格式 1 + 3 — 开发用 MLIR 文本，生产用 Protobuf
```

### 4.2 接口契约

Haskell 后端期望从 MLIR 前端接收：

```
输入:
  - 已分区的操作图 (每个操作标记了队列 ID)
  - 每个操作的延迟预算 (cycle 约束)
  - 内存布局信息 (地址分配)
  - 流寄存器分配信息

Haskell 后端负责:
  - 精确的 cycle-level 调度
  - 冲突检测与解决
  - 指令编码
  - 二进制生成 (IOP)
```

---

## 5. 关键洞察 / Key Insights

1. **MLIR 并非 Groq 编译器的核心——调度器才是**。MLIR 前端处理约 70% 的优化工作（图级优化、融合、布局），但最关键的 30%（调度、编码）在 Haskell 中。

2. **Groq Dialect 的设计反映了硬件架构**。每个 Dialect 层的划分（Graph → Slice → Stream → Queue）直接映射到 TSP 的物理层次结构。这不是巧合——这是硬件优先的编译器设计哲学。

3. **Pass 顺序的敏感度**。MLIR pass pipeline 的设计对最终性能影响巨大——融合 pass 必须在分区 pass 之前（否则 fusion 会跨队列边界），布局 pass 必须在降低到 stream 层之前。

4. **静态形状的约束**。MLIR 前端的所有 pass 都假设静态张量形状。动态 shape 需要额外的 pass 来插入 shape 推断或 pad-to-static 转换。

---

**Next**: [Layer 2: Haskell 类型系统与 Haste DSL](./layer2-haskell-type-system.md)
