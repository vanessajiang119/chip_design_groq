# Working: 指令级并行与 144 队列 — Layer 2 深度分析

> 创建时间: 2026-05-19
> 分析层级: Layer 2 — 指令队列仲裁、依赖跟踪、ILP 实现

---

## 1. 144 队列的物理组织

### 1.1 队列分配

144 个指令队列在功能切片间的分布：

```
芯片布局视角:

                              (功能切片列)
                  MXM  MEM  VXM  MEM  SXM  MXM  MEM  ...
                  ┌────┬────┬────┬────┬────┬────┬────┐
  SuperLane 0     │    │    │    │    │    │    │    │
  SuperLane 1     │    │    │    │    │    │    │    │
  ...             │ 144 个队列垂直分布         │    │
  SuperLane 19    │    │    │    │    │    │    │    │
                  └────┴────┴────┴────┴────┴────┴────┘
                   ▲    ▲    ▲    ▲    ▲    ▲    ▲
                   │    │    │    │    │    │    │
                MXM_q   MEM_q VXM_q MEM_q SXM_q MXM_q

队列到功能切片的映射:
  └── 每个功能切片类型有自己的队列集合
  └── 队列物理上位于 ICU 中 (芯片底部)
  └── 队列的指令注入到 SuperLane 0 的指令管道
```

### 1.2 队列的微架构

每个指令队列是一个简单的 FIFO，其结构：

```
┌─────────────────────────────┐
│ Instruction Queue (IQ)      │
├─────────────────────────────┤
│ 深度: ~16-32 条指令         │
│ 宽度: ~64-128 bits          │
│                             │
│ ┌────┬────┬────┬────┬────┐  │
│ │ I0 │ I1 │ I2 │ ... │ In │  │
│ └────┴────┴────┴────┴────┘  │
│   ▲                         │
│   └── head pointer           │
│                             │
│ 功能:                       │
│  └── 按序发射               │
│  └── 无重排序               │
│  └── 无 OoO 窗口            │
│  └── 无 reservation station  │
└─────────────────────────────┘
```

**关键**: 这些队列是**简单的 FIFO**，没有传统处理器中 ROB (Reorder Buffer)、reservation station 等复杂结构。编译器负责将所有指令按正确顺序放入队列。

## 2. 队列仲裁

### 2.1 "无仲裁" 的仲裁

严格来说，TSP **没有硬件仲裁器**。每个队列的发射时序由编译器确定。

编译器保证：
```
cycle t 所有队列的发射集合:
  Queue 0 (MEM):  发射 LOAD 指令 ✓
  Queue 1 (MEM):  发射 LOAD 指令 ✓  
  Queue 2 (VXM):  发射 VECTOR_ADD 指令 ✓
  ...
  Queue 143:       发射 NOP ✓
  
没有冲突，因为:
  └── 编译器确保每个功能切片的发射数量不超过上限
  └── 编译器确保每个 SRAM bank 端口无冲突
  └── 编译器确保 SRF 流 ID 无冲突
```

### 2.2 每 cycle 发射逻辑

每个队列的发射逻辑极其简单：

```
每个 cycle:
  1. 检查 head 指令是否已到发射时间
  2. 如果到时间，则发射
  3. 否则等待

不需要:
  └── 检查资源可用性 (编译器已保证)
  └── 检查数据可用性 (编译器已保证)
  └── 检查冲突 (编译器已保证)
  └── 检查异常 (TSP 无异常)

硬件复杂度: 一个比较器 + 一个计数器
```

### 2.3 发射带宽

| 指标 | 值 |
|------|-----|
| 队列总数 | 144 |
| 每 cycle 可发射 | 80+ 条指令 |
| 每队列每 cycle | 0-1 条指令 (取决于编译器安排) |
| 功能切片超量发射 | 是的 — MXM 6条/cycle, MEM 44条/cycle |

## 3. 依赖跟踪

### 3.1 无硬件依赖跟踪

TSP 完全没有硬件依赖跟踪机制。没有：
- **Scoreboarding**: 不需要跟踪寄存器使用情况
- **Tomasulo 算法**: 不需要 reservation stations
- **Register Renaming**: 不需要映射逻辑寄存器到物理寄存器

### 3.2 编译器如何管理依赖

编译器通过以下数据结构管理依赖：

```
每个指令节点的依赖信息:
{
  instruction: MXM_MATMUL,
  consumer_of: [stream_3, stream_5],  // 消费哪些流
  producer_of: [stream_7],             // 产生哪些流
  earliest_cycle: 100,                 // 最早可发射时间
  latest_cycle: 150,                   // 最晚可发射时间
  functional_slice: MXM,
  superlane: 3
}
```

### 3.3 依赖分析算法

编译器执行的依赖分析：

```
1. Stream 级依赖:
   stream 3 (produced by MEM at t=10)
   stream 3 (consumed by VXM at t=15)
   → VXM 必须在 t ≥ 10 + SRF_prop_delay 时才能开始

2. 跨队列依赖:
   Queue 5 (MEM) 在 t=10 发射 LOAD stream_3
   Queue 12 (VXM) 在 t=15 发射 ADD stream_3
   → Queue 12 的发射在 Queue 5 的发射之后至少 5 cycles

3. 同步依赖:
   SYNC 指令 → 所有队列都必须到达 SYNC 点
   → 编译器插入 NOP 或有用工作以对齐所有队列
```

## 4. ILP (指令级并行) 的实现

### 4.1 ILP 的来源

TSP 的 ILP 来自以下几个层面：

```
层面 1: 功能切片并行
  └── MXM 在做矩阵乘法的同时
  └── VXM 在做向量运算
  └── MEM 在加载/存储数据
  └── SXM 在做数据重排
  └── 这些完全不冲突，可 100% 并行

层面 2: 同一功能切片的多发射
  └── MEM 有 44 条指令/cycle 的带宽
  └── 可以同时处理多个独立的内存访问
  └── 编译器利用内存级并行 (MLP)

层面 3: 流水线并行
  └── 不同 SuperLane 在同一时间处理不同数据
  └── 20 级 SuperLane 流水线深度提供 Pipeline ILP

层面 4: 流并行
  └── 32 个 Eastbound + 32 个 Westbound 流
  └── 独立流可以同时处理不同数据
```

### 4.2 ILP 的量化分析

```
ResNet-50 推理的典型指令分布:
  总指令数: ~50,000
  总 cycles: ~2,000
  平均 IPC: ~25 指令/cycle

  理论最大 IPC: 80+ 指令/cycle
  实际 IPC: ~25-40 (取决于计算模式)
  利用率: ~30-50%

  利用率不达 100% 的原因:
    └── 同步开销
    └── 数据依赖链限制
    └── 资源冲突 (编译器安排)
    └── 模型形状不规则
```

### 4.3 IPC (Instruction Per Cycle) 与带宽关系

```
对于矩阵乘法 (GEMM):
  
  计算指令 vs 数据搬运指令的比例:
    └── MXM 计算: ~40% 指令  
    └── MEM 搬运: ~55% 指令
    └── VXM/SXM: ~5% 指令
  
  内存带宽限制:
    └── 80 TB/s SRAM 带宽
    └── 9.2 TB/s 片内数据移动带宽
  
  对于计算密集操作 (如 GEMM):
    └── IPC 较高 (计算和数据搬运可重叠)
  
  对于 memory-bound 操作 (如 embedding):
    └── IPC 受限于内存带宽
```

## 5. 与 GPU ILP 的对比

### 5.1 GPU ILP 的实现

```
GPU (NVIDIA):
  ILP 通过以下方式实现:
    └── Warp Scheduler: 每 cycle 选择一个 warp 发射
    └── 多 warp 交错隐藏延迟
    └── Scoreboarding: 跟踪 warp 内依赖
    └── 指令重排序: 在 warp 内有条件重排
    
  ILP 的代价:
    └── 复杂的调度硬件
    └── Warp 切换的功耗
    └── 非确定性延迟
```

### 5.2 TSP ILP 的实现

```
TSP:
  ILP 通过以下方式实现:
    └── 144 队列独立发射
    └── 编译器静态安排所有并行
    └── 功能切片天然并行
    
  ILP 的代价:
    └── 编译器复杂度
    └── 需要编译器预测最佳并行度
    └── 不规则负载利用率低
```

### 5.3 对比总结

| 维度 | GPU ILP | TSP ILP |
|------|---------|---------|
| 调度方式 | 硬件运行时 | 编译器编译时 |
| 并行粒度 | Warp 级 (32 threads) | 功能切片级 |
| 硬件开销 | 高 (warp scheduler + scoreboard) | 低 (简单 FIFO) |
| 动态适应性 | 强 (适应数据相关变化) | 弱 (固定计划) |
| ILP 峰值 | 依赖 warp 数 | 80+ 指令/cycle |
| 确定性 | 否 | 是 |

## 6. 编译器 ILP 提升策略

### 6.1 软件流水线 (Software Pipelining)

```
对于循环:
  for i in 0..N:
    A[i] = B[i] + C[i]

编译器转换为软件流水线:
  循环展开 + 迭代交错:
    t=0:  LOAD B[0], LOAD C[0]
    t=1:  LOAD B[1], LOAD C[1],  ADD A[0]  
    t=2:  LOAD B[2], LOAD C[2],  ADD A[1], STORE A[0]
    ...
    
  结果: 每个 cycle 执行 LOAD + ADD + STORE
  而非: LOAD→LOAD→ADD→STORE (串行)
```

### 6.2 循环展开 (Loop Unrolling)

编译器展开循环以暴露更多 ILP：
```
原始: 10 次迭代, 每次 4 条指令 (有依赖)
展开 4 次: 每次处理 4 个元素
          指令数增加但 ILP 提升
```

### 6.3 指令打包 (Instruction Bundling)

编译器将独立的指令打包到同一 cycle 的多个发射槽中：
```
Cycle t 的发射计划:
  MXM:  MATMUL(weight=W, input=X)     ← 矩阵乘法
  MEM:  LOAD(addr=next_input)          ← 预加载下一输入
  MEM:  STORE(addr=output, data=prev)  ← 存储上一结果
  VXM:  VECTOR_ADD(A, B)               ← 向量运算 (独立计算)
  SXM:  PERMUTE(stream=5)              ← 数据重排 (独立)
  
  这 5 条指令在同一 cycle 完全并行执行
```

## 7. 队列的功耗分析

### 7.1 队列面积

```
每个队列:
  └── FIFO 存储: ~16-32 条 × 128 bits = 256-512 bytes
  └── 控制逻辑: 比较器 + 计数器
  
144 队列总计:
  └── 存储: ~36-72 KB
  └── 控制: <0.5% 芯片面积
  └── 功耗: <1% 总功耗
```

### 7.2 对比 GPU 的调度硬件

```
NVIDIA A100 的 warp scheduling:
  └── 108 SMs × 64 warp 调度器
  └── 复杂的 scoreboarding + 重命名
  └── 估计 >10% 芯片面积用于调度

TSP 的队列调度:
  └── 144 简单 FIFO
  └── <0.5% 芯片面积
  
面积节省: ~20:1
```

## 8. 结论与关键发现

1. **无硬件仲裁是 TSP 的核心设计选择** — 编译器承担了所有调度复杂度
2. **144 队列的本质是 144-wide VLIW** — 编译器打包 80+ 条指令/cycle
3. **无依赖跟踪硬件** — 编译器通过 stream 依赖分析管理所有依赖
4. **ILP 来自四个层面**: 功能切片并行、多发射、流水线并行、流并行
5. **实际 IPC 约 25-40** — 理论最大 IPC 80+ 的 30-50%
6. **队列硬件极简** — <0.5% 芯片面积，<1% 功耗，远低于 GPU 调度器
