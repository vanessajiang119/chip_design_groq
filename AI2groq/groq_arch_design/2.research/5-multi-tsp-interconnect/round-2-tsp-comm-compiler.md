# Round 2: TSP 间通信与编译器网络调度

> 创建时间: 2026-05-19
> 状态: Research Complete

## 一、TSP 间通信机制

### 1.1 通信模型：Producer-Consumer Stream

Groq 将单 TSP 的 **producer-consumer 流式编程模型** 扩展到全局多 TSP 系统：

- **数据以流（stream）形式在 TSP 间传递**
- **编译器预先协调** send/receive 指令，消除 request/response 往返延迟
- **无硬件流控** — 完全由软件调度避免溢出/欠载
- 使用 **ISA 级 "deskew" 指令** 对齐多链路数据，保持分布式 TSP 的同步锁步编程模型

### 1.2 消息格式

| 参数 | 数值 |
|------|------|
| **负载（payload）** | 320 字节向量（对齐 TSP 的 320-lane SIMD 宽度） |
| **编码开销** | 仅 ~2.5%（最小头部/尾部标记） |
| **无数据包头** | 因为路由由编译器静态决定 |
| **无握手协议** | send/receive 按时序执行 |

### 1.3 数据包结构（推测）

由于完全软件调度，Groq 的 C2C 链路传输可能采用极简格式：
```
┌──────────────────────────────────────────┐
│  Control Bits (~2.5%)                     │
│  ┌──────────────┬──────────┬──────────┐   │
│  │ Stream ID    │ Sequence │ ECC/CRC  │   │
│  └──────────────┴──────────┴──────────┘   │
├──────────────────────────────────────────┤
│  Payload: 320-byte Vector Data            │
│  ┌──────────────────────────────────┐     │
│  │ 320 × FP8/INT8/FP16 elements     │     │
│  └──────────────────────────────────┘     │
└──────────────────────────────────────────┘
```

## 二、同步机制

### 2.1 Hardware Alignment Counter（HAC）

每个 TSP 拥有独立的 **硬件对齐计数器**，用于多芯片同步：

1. **HAC 校准** — 当两个 TSP 互联时，一方发送 HAC 值，对方回显，差值即为链路延迟
2. **Parent-Child 关系** — Parent 周期发送 HAC 值，Child 调整自身 HAC 抵消时钟漂移
3. **生成树协议** — 可跨多跳网络建立 spanning tree，扩展至整个系统

### 2.2 DESKEW 指令

```
DESKEW:
  功能: 停止处理后续指令，直到 HAC 溢出
  用途: 跨 TSP 对齐执行时间
  变体: RUNTIME_DESKEW — 运行时重新同步本地时间与全局时间
```

### 2.3 SYNC/NOTIFY 指令（单 TSP 内）

- **SYNC**: 暂停所有 144 个指令队列
- **NOTIFY**: 广播到所有队列恢复同步执行

### 2.4 Plesiosynchronous 操作

Groq 系统 **并非真正全局同步**，而是提供 **伪同步（plesiosynchronous）** 的假象：

- 每个 TSP 有独立的时钟源
- HAC + SAC（Software Alignment Counter）检测和补偿时钟漂移
- 结果是所有 TSP 仿佛在 lockstep 中运行
- "提供了一种大型单核同步系统的假象"

## 三、编译器网络调度

### 3.1 静态路由分配

Groq 编译器的网络调度是其核心创新：

```
Compiler 静态调度流程：
1. 分析计算图（ML model graph）
2. 为每个张量分配产生 TSP + 消费 TSP
3. 计算全局数据流路径
4. 为每段通信分配精确时间槽
5. 生成 send/receive 指令序列（精确到 cycle）
```

### 3.2 Source-Based Routing（源路由）

- **所有路由决策在编译时由编译器决定**
- 源 TSP 的指令流确定每个数据包的路径和时间
- 无运行时路由决策，无数据包头，无握手机制
- 编译器拥有 **全局视图**，可进行全网络负载均衡

### 3.3 编译器调度的优势

| 方面 | 传统网络 | Groq 编译器调度 |
|------|---------|----------------|
| 路由决策 | 运行时（自适应路由） | 编译时（静态） |
| 链路冲突 | 动态避免（重传/退避） | 编译时完全消除 |
| 控制开销 | 高（包头 + 握手） | 极低（~2.5%） |
| 带宽利用率 | 受拥塞影响下降 | 75-90% 峰值利用率 |
| 延迟抖动 | 有（排队延迟） | 零（确定性） |
| 路径多样性 | 保守使用 | 可同时使用 A→B→C 和 A→C |

### 3.4 链路负载均衡策略

编译器的全局视图使其能够实现传统网络无法达到的负载均衡：

- **同时利用多条路径** — 例如同时使用直达路径 A→C 和间接路径 A→B→C
- **动态网络会保守地不使用 A→B→C**，因为担心干扰 B 的带宽
- **编译器可以精确计算每条链路的占用率**，做到零冲突的完美调度

### 3.5 确定性定时保证

- 编译器 **精确知道每个程序段的执行周期数**
- 数据无关的执行时间（不依赖输入数据值）
- 所有 TSP 在 lockstep 中执行
- 数据传输使用 **指令指针作为隐式时间戳** — 不需要 request/response

## 四、路由与死锁避免

### 4.1 Groq 的死锁避免策略

由于 **所有路由由编译器静态决定**，Groq 采用与通用 Dragonfly 不同的死锁避免方法：

- **确定性路由（Deterministic routing）** — 编译器选择的路由路径保证无环
- **无需 VC（Virtual Channel）隔离** — 传统 Dragonfly 需要 VC shifting 来避免死锁
- **编译器保证无循环依赖** — 从调度层面消除死锁可能
- **无自适应路由** — 简化了死锁避免的复杂度

### 4.2 与传统 Dragonfly 死锁避免对比

| 方法 | 传统 Dragonfly | Groq Dragonfly |
|------|---------------|----------------|
| VC shifting | 需要 | 不需要（编译器保证） |
| Escape VC | 需要 | 不需要 |
| 自适应路由 | 常见 | 不使用 |
| 死锁检测 | 硬件机制 | 编译时验证 |
| 非最小路由 | Valiant 需要特殊处理 | 编译器可控 |

## 五、性能数据

### 5.1 通信延迟

| 操作 | 延迟 | 对比 |
|------|------|------|
| 8 TSPs AllReduce | 2.1 μs | 快于 NVIDIA A100 (同等配置) |
| 端到端系统（任意 TSP 对） | < 3 μs | 10,440 TSPs 规模 |
| 单机架延迟 | 1.6 μs | 8 个计算节点 |

### 5.2 计算性能

| 应用 | 性能 |
|------|------|
| 分布式矩阵乘法（650k×650k, 100 TSPs） | ~100x 加速 vs NVIDIA V100 集群 |
| BERT-Large 推理 | 平均 1,225 μs 延迟，近线性吞吐扩展 |
| Cholesky 分解 | 1.5× 性能提升，22.4 FP16 TFLOPS/节点 |

## 六、关键参考

- ISCA 2022: "A Software-defined Tensor Streaming Multiprocessor for Large-scale Machine Learning"
- ISCA 2020: "Groq: A TSP for Deep Learning"
- Stanford EE380 Talk (Dennis Abts, Groq Chief Architect)
- SC23 Supercomputing: "Strong Scaling of State-of-the-Art LLM Inference with Groq"
- Groq Patent 12277444: "Software-defined Tensor Streaming"
