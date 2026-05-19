# Working: Streaming Dataflow 模型 — Layer 2 深度分析

> 创建时间: 2026-05-19
> 分析层级: Layer 2 — Streaming dataflow 实现机制

---

## 1. Stream 的概念与生命周期

### 1.1 定义

在 Groq TSP 中，**stream** 是一个在功能切片间流动的数据序列。与传统处理器的"指令→寄存器→指令"模式不同，TSP 的流模型中没有显式的通用寄存器文件——数据以流的形式直接在生产者和消费者之间传递。

### 1.2 Stream 的组成

每个 stream 由以下属性标识：
- **Stream ID** (0-31): 流的唯一标识符
- **方向** (East/West): 在芯片上的流动方向
- **数据类型**: INT8/FP16/FP32 等
- **长度**: 张量元素的个数
- **时序**: 编译器确定的每 cycle 数据到达时间

### 1.3 Stream 生命周期

```
阶段 1: 创建 (Produce)
  生产者功能单元 (如 MEM) 将数据加载到 stream 中
  └── 编译器指定: 起始 cycle、流 ID、方向
  
阶段 2: 传输 (Transport)
  数据在功能切片间以 1 cycle/跳 的速度传播
  └── 通过流式寄存器文件 (SRF) 传递
  └── 每个 SuperLane 中的 SRF 存储流数据
  
阶段 3: 消费 (Consume)
  消费者功能单元在指定 cycle 读取 stream
  └── 编译器确保数据到达时指令也在该位置
  
阶段 4: 终止 (Terminate)
  stream 到达最终消费者后释放
  └── Stream ID 可被重用
```

### 1.4 Stream 与 Tensor 的关系

```
Tensor (逻辑视图)          Stream (物理视图)
┌─────────────┐           ┌────┬────┬────┬────┐
│ [row][col]   │  映射为    │ t0 │ t1 │ t2 │ t3 │ ...
│ shape=(M,N)  │  ──────▶  └────┴────┴────┴────┘
│ dtype=int8   │           Stream ID=5, Eastbound
└─────────────┘           每 cycle 一个 element
```

编译器将张量分片 (tiling) 并映射到物理流上，利用空间并行性。

## 2. Stream Register File (SRF) 的微架构

### 2.1 SRF 结构

每个 SuperLane 中的流式寄存器文件是数据流动的核心基础设施：

```
一个 SuperLane 的 SRF:
┌─────────────────────────────────────────┐
│  Stream Register File (SRF)             │
│  ├── 32 个 Eastbound 流槽位             │
│  │    ├── 每个槽位: 512 字节宽           │
│  │    └── 深度: ~4-8 个元素 (FIFO)      │
│  ├── 32 个 Westbound 流槽位             │
│  │    ├── 每个槽位: 512 字节宽           │
│  │    └── 深度: ~4-8 个元素 (FIFO)      │
│  └── 旁路: 直接通道 (zero-cycle bypass) │
└─────────────────────────────────────────┘
```

### 2.2 SRF 操作

- **写**: 上游功能单元在计算的最后一个 cycle 将结果写入 SRF
- **读**: 下游功能单元在第一个 cycle 从 SRF 读取
- **旁路**: 如果生产者和消费者在同一 SuperLane 且相邻切片间没有缓冲，数据可以直接传递

### 2.3 SRF 大小计算

每个 SuperLane:
- 64 流 × 512 字节/流 = 32 KB (数据 + 元数据)
- 20 SuperLanes × 32 KB = **640 KB 总 SRF 容量**
- 相对于 220 MB 总 SRAM，SRF 占比很小

## 3. 流数据的具体流动路径

### 3.1 张量加载场景

```
场景: VXM 计算需要两个输入张量 A 和 B

Step 1: MEM 加载
  MEM slice → stream_id=3, Eastbound
  └── 从 SRAM 地址 0x1000 读取 A, 每 cycle 512 字节
  └── 耗时: ceil(size_A / 512) cycles

Step 2: Stream 传输
  stream(3, East) 沿 MEM → VXM 路径传递
  └── 1 cycle MEM→VXM 跳转
  └── 通过 SRF 缓冲

Step 3: VXM 消费
  VXM 在预定 cycle 读取 stream(3)
  └── 与从 stream(4, West) 读取的 B 对齐
  └── 执行向量运算

Step 4: VXM 产生结果
  VXM → stream(7, West) 
  └── 结果流向下游 MEM 或 MXM
```

### 3.2 矩阵乘法数据流

```
场景: MXM 执行 C = A × B

数据流:
  MEM ──stream(A)──▶ MXM ──stream(C)──▶ MEM
                    ▲
  MEM ──stream(B)──┘

编译器安排:
  t=0:    MEM 开始加载 A (stream_id=1, East)
  t=10:   MEM 开始加载 B (stream_id=2, West)  
  t=100:  MXM 开始接收 A, 启动矩阵乘
  t=105:  MXM 开始接收 B
  t=1000: MXM 开始输出 C (stream_id=5, East)
  t=1050: MEM 开始存储 C
```

编译器确保所有时序对齐，避免流水线气泡。

## 4. Chaining (链式传递)

### 4.1 基本 Chaining

Chaining 是 TSP 性能的关键——中间结果不写回 SRAM，直接传递给下一个功能单元：

```
无 Chaining (普通模式):
  VXM: 计算结果 → MEM: 写SRAM → MEM: 读SRAM → VXM: 使用
  └── 额外的 SRAM 读/写延迟和功耗

有 Chaining:
  VXM: 计算结果 ──stream──▶ VXM: 直接使用
  └── 数据在 SRF 中传递, 零额外延迟
```

### 4.2 Chaining 的微架构实现

Chaining 依赖于 SRF 的直接旁路路径：
- 当生产者和消费者在相邻的功能切片时，数据通过 SRF 直接传递
- 不需要仲裁——编译器已经确定了路径和时间
- 每个 chaining 步骤节省：1 次 SRAM 写 + 1 次 SRAM 读 = **~10 cycle + ~10 pJ** (估计)

### 4.3 Chaining 链的长度

理论上 chaining 可以跨越任意多个功能单元：
```
MEM → MXM → VXM → MEM → MXM → SXM → ...
```
但在实际中受限于：
- **流 ID 数量**: 每 SuperLane 只有 64 个流
- **SRF 深度**: 有限的 FIFO 深度
- **编译器调度复杂度**: 长链更难调度

## 5. 流量控制与缓冲区管理

### 5.1 无动态流控

由于所有时序在编译时已知，TSP **不需要动态流控**：
- 无握手信号 (ready/valid)
- 无反压 (backpressure)
- 无需 buffer 占用跟踪

### 5.2 编译器保证

编译器确保：
1. 生产者不会在消费者未准备好之前发送数据
2. SRF 不会上溢（消费者读取速度 >= 生产者写入速度）
3. SRF 不会下溢（生产者写入速度 >= 消费者读取速度，或在开始时间上同步）

### 5.3 最小开销

数据包仅有头部/尾部标记 (~2.5% 开销)，无流控逻辑，这是确定性的关键优势。

## 6. Stream 同步原语

### 6.1 SYNC 指令

```
SYNC: 全局屏障
  └── 等待所有先前的流操作完成
  └── 用于阶段转换或模型层之间的同步
  └── 编译器安排 SYNC 的位置以最小化等待时间
```

### 6.2 NOTIFY 指令

```
NOTIFY: 点对点通知
  └── 队列 A 通知队列 B: 某流已完成
  └── 用于跨队列的轻量级同步
  └── 编译器安排 NOTIFY 以减少全局屏障
```

## 7. 为什么 Streaming Dataflow 能节省功耗？

### 7.1 消除数据移动

传统架构中，80% 的能耗用于数据搬运。TSP 的流模型显著减少：
- **无 Register File 读写**: 流数据直接传递
- **无 Cache 层次**: 数据不走 L1/L2 cache
- **无 DRAM 访问**: 220 MB SRAM 在片上

### 7.2 消除控制开销

- **无调度器动态功耗**: 编译器已完成
- **无仲裁器**: 无总线/网络仲裁
- **无地址翻译**: 编译器已知所有物理地址

### 7.3 量化估计

| 能耗项 | GPU 估计 | Groq TSP 估计 | 节省 |
|--------|---------|--------------|------|
| 指令调度 | 15% 总功耗 | ~0% | ~15% |
| 缓存层次 | 25% 总功耗 | ~0% | ~25% |
| 数据搬运 | 20% 总功耗 | ~10% | ~10% |
| 控制逻辑 | 20% 总功耗 | ~3% | ~17% |
| **总计** | **80% overhead** | **~13% overhead** | **~67%** |

## 8. 关键限制

1. **流 ID 数量有限**: 64 个逻辑流/通道可能成为复杂模型的瓶颈
2. **静态编译**: 动态形状或不规则计算难以处理
3. **SRF 深度**: 有限 FIFO 深度限制了长 pipeline 的 bubble 容忍度
4. **仅 220 MB SRAM**: 大模型需要分片和高效复用
5. **编译器复杂度**: 全局调度的 NP-hard 问题需要启发式算法

## 9. 结论

Streaming dataflow 是 Groq TSP 架构的基石。通过将数据移动从"隐式"（cache/register 决定）变为"显式"（编译器安排），TSP 消除了传统处理器中大部分非确定性开销。Stream chaining 和 SRF 旁路是实现高能效计算的关键微架构特性，但其高度依赖编译器的静态分析能力，对不规则工作负载不友好。
