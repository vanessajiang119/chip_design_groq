# Layer 2: NoC 拓扑与编译器数据布局深入分析

> **时间**: 20260519-1700
> **类型**: Working Document — 编译器数据布局策略与片上互联机制

---

## 1. 片上互联的流式速率匹配

### 1.1 指令流与数据流的交汇

Groq TSP 最独特的设计之一是**两维流以不同速度行进**：

```
指令流 (垂直): ICU 每 cycle 向上传递一条指令
               每个 tile 在指令到来时执行
               速度: 1 tile/cycle (20 cycles 覆盖全芯片)

数据流 (水平): 数据在 superlane 内以全宽水平流动
               每 cycle 可以跨越多个功能单元
               速度: 1-2 功能单元/cycle
```

### 1.2 流水线填充时间

```
指令从 ICU 到 Tile 19: 20 cycles
数据从 MEM 到 MXM:   通常 1-2 cycles

编译器必须补偿这个 skew:
  数据提前 18-19 cycles 从 MEM 发出
  指令和数据在 MXM 精确 meeting
```

### 1.3 Stream 的物理实现

每个 Stream 在物理上是一个**分布式流寄存器文件 (SRF)**：

```
SRF 分布:
  ┌─────┬─────┬─────┬─────┬─────┐
  │ 2 B │ 2 B │ 2 B │ 2 B │ ... │  ← 每 lane 32 B
  ├─────┼─────┼─────┼─────┼─────┤
  │ MXM │ SXM │ MEM │ VXM │ MEM │  ← 每个 stream 在每个 slice 有寄存器
  └─────┴─────┴─────┴─────┴─────┘

每个 stream 位宽: 320 channels × 32 B = 10,240 B (全芯片宽度)
每个 stream 存储: 10,240 B × 深度(每 slice 的寄存器)
```

32 东向 + 32 西向 = 64 streams × 10,240 B ≈ 655 KB 作为 SRF 存储。

---

## 2. SXM 交换网络架构

### 2.1 SXM 的两种工作模式

#### 模式 A: 片上数据重组

```
输入: 来自 MEM 或 MXM 的 512B 向量 (32 B × 16 lanes)
操作: 每个 lane 的数据可以:
  - 移位 (shift left/right)
  - 旋转 (rotate)
  - 广播 (broadcast)
  - 置换 (permute)
输出: 重新排列后的 512B 向量
```

#### 模式 B: 片间路由

```
SXM 作为网络交换机:
  输入: 从 C2C 链路到达的数据
  路由: 根据编译器预置的路由表
  输出: 
    - 转发到本地 MEM storage
    - 转发到本地计算单元 (MXM/VXM)
    - 转发到其他 C2C 链路继续传输
```

### 2.2 SXM 作为网络交换机的逻辑

```
        TSP-A (交换模式)
    ┌────────────────────┐
    │  ... → SXM → C2C ────→ TSP-B
    │         ↑
    │        C2C ←──────── TSP-C
    └────────────────────┘

TSP 同时是:
  - 处理端点 (processing endpoint)
  - 网络交换机 (network switch)
  - 两者角色由编译器静态分配
```

### 2.3 片间路由与 Dragonfly 拓扑

Groq 采用的 Dragonfly 拓扑特点：

```
层次 1 (组内): 8 TSP 全连接 mesh
层次 2 (组间): Dragonfly 组拓扑
层次 3 (全局): 最高 145 组，5 跳可达任何节点

路由策略 (编译器静态):
  源路由 (source routing) — 发送方指定完整路径
  无动态路由决策 — 路径在编译时固定
  无拥塞 — 流量模式已知，链路带宽预先分配
```

---

## 3. 编译器数据布局的详细策略

### 3.1 张量布局问题形式化

给定:
- 模型计算图 G = (V, E), V 为张量, E 为操作
- 芯片资源: 40 MEM 单元, 每单元 5.5 MB, 16-32 banks
- 计算资源: 40 MXM, 20 VXM, 40 SXM
- 通信资源: 40 × 512 B/cycle 水平数据路径

求:
- 张量到 MEM 单元的映射 f: V → MEM_id
- 张量到 bank 的映射 g: V → bank_id  
- 访问时序 t: V × {read,write} → clock_cycle
- 流分配 s: V → {stream_id, direction}

满足约束:
- 容量: Σsize(V_i) ≤ 5.5 MB per MEM
- Bank 冲突: 同一 bank 的两次访问至少间隔 1 cycle
- 数据依赖: 消费者必须在生产者之后执行
- 时序可行性: 所有指令在可用周期内

### 3.2 启发式策略

#### 步骤 1: 层分区 (Layer Partitioning)

```
对于 Transformer Block:
  ├── Attention 部分 → 通常放在相邻 MEM 单元
  ├── FFN (MLP) 部分 → 可能分布在多个 MEM 单元
  └── Residual 连接 → 在 MEM 之间做数据路由
```

#### 步骤 2: 张量分配 (Tensor Allocation)

优先级策略:
1. **权重**: 静态分配，整个模型生命周期常驻 SRAM
2. **KV-cache**: 动态分配，每个 token 更新，需要频繁读写
3. **中间激活**: 临时分配，用完即释放

```
MEM 单元使用策略:
  MEM[L] (左): 倾向于存储被左侧 MXM 频繁读取的权重
  MEM[R] (右): 倾向于存储被右侧 MXM 频繁读取的权重
  VXM 附近的 MEM: 存储向量操作所需的激活
```

#### 步骤 3: Stream 分配

```
张量 → Stream 的映射规则:
  1. 大张量: 分配到多个 Stream 分片传输
  2. 数据重用: 分配到广播 Stream (multi-cast)
  3. 链式传输: 分配到同一 Stream 级联
  
方向选择:
  东向 Stream: 从左到右的数据流动
  西向 Stream: 从右到左的数据流动
  双向 Stream: 用于 MEM ↔ VXM 的频繁交换
```

### 3.3 Bank 冲突避免详解

#### 问题场景

假设两个 MXM 操作需要同时从两个不同的 MEM 单元读取数据：

```
Cycle N:
  MEM[0] bank 3: 读操作 A
  MEM[1] bank 3: 读操作 B   ← 不同 MEM 单元无冲突

Cycle N:
  MEM[0] bank 3: 读操作 A
  MEM[0] bank 3: 读操作 C   ← 同一 bank 冲突!
```

#### 解决方案

编译器使用 **bank 交错 (bank interleaving)** 和 **偏移放置 (offset placement)**：

```
策略 1: 地址交错
  地址 0x0000 → bank 0
  地址 0x0040 → bank 1
  地址 0x0080 → bank 2
  ...  (连续访问分布在相邻 bank)

策略 2: 张量对齐
  Tensor A: 从 bank 0 开始放置
  Tensor B: 从 bank 8 开始放置 (偏移)
  确保并发访问落在不同 bank

策略 3: 时序偏移
  如果必须访问同一 bank:
    Cycle N: 访问 A
    Cycle N+1: 访问 B (时序错开 1 cycle)
```

---

## 4. 编译器调度示例: Transformer Layer

### 4.1 Single TSP 上的 Layer 调度

假设一个自注意力层在单个 TSP 上的执行流水：

```
Timeline (cycles, 简化):
┌───────────┬──────────────────────────────────────────┐
│ Phase     │ 操作                                      │
├───────────┼──────────────────────────────────────────┤
│ T=0-100   │ 从外部 MEM (或 C2C) 加载权重到片上 SRAM    │
│ T=100-200 │ QKV 投影: MEM → MXM → MEM                 │
│ T=200-300 │ Attention score: MEM → VXM/MXM → MEM       │
│ T=300-400 │ Softmax: VXM (多 step) → MEM               │
│ T=400-500 │ Attention output: MEM → MXM → MEM          │
│ T=500-600 │ 输出投影 + Residual: MEM → MXM/VXM → MEM   │
│ T=600-700 │ FFN1 + FFN2 + Residual                     │
└───────────┴──────────────────────────────────────────┘
```

### 4.2 多 TSP 上的 Pipeline 并行

```
TSP 0: Layer 0-5  |  TSP 1: Layer 6-11 | TSP 2: Layer 12-17
───────────────────┼────────────────────┼──────────────────────
  MEM: W0-W5       |  MEM: W6-W11       |  MEM: W12-W17
  MXM: QKV proj    |  MXM: QKV proj     |  MXM: QKV proj
  VXM: softmax     |  VXM: softmax      |  VXM: softmax
  C2C: send out    |  C2C: recv + send  |  C2C: recv activations
```

### 4.3 多 TSP 上的 Tensor 并行

```
TSP 0: 前 50% 的 FFN 神经元       |  TSP 1: 后 50% 的 FFN 神经元
──────────────────────────────────┼─────────────────────────────────
  MEM: W[:, 0:4096]               |  MEM: W[:, 4096:8192]
  MXM: 320×320 × N 个 MAC         |  MXM: 320×320 × N 个 MAC
  All-reduce: 通过 C2C 交换部分和  |  All-reduce: 通过 C2C 交换部分和
```

---

## 5. 编译器复杂度与挑战

### 5.1 编译时间

Groq 编译器面对的是一个 NP-hard 级别的联合优化问题。其典型编译时间：

| 模型规模 | 编译时间估计 | 说明 |
|----------|-------------|------|
| 小模型 (<1B) | 分钟级 | 较少约束 |
| 中等模型 (1-10B) | 小时级 | 布局调度复杂 |
| 大模型 (70B+) | 天级 | 大量跨 chip 约束 |

### 5.2 可扩展性挑战

```
单芯片:  20 superlanes, 144 指令队列, 64 streams
8 芯片:  160 superlanes, 1,152 指令队列, 512 streams
72 芯片:  1,440 superlanes, 10,368 指令队列
```

约束数量随芯片数 **超线性增长**。

### 5.3 编译器的关键技术

| 技术 | 说明 |
|------|------|
| **Integer Linear Programming (ILP)** | 用于建模优化问题 |
| **Graph Coloring** | 用于 bank 分配和 stream 分配 |
| **List Scheduling** | 用于指令时序安排 |
| **Modulo Scheduling** | 用于流水线循环（如 attention heads） |
| **Dynamic Programming** | 用于张量放置决策 |

---

## 6. 优劣势定量总结

### 6.1 确定性架构的优势

| 指标 | Groq TSP | 传统 GPU | 倍数 |
|------|----------|----------|------|
| 延迟方差 | 0 (完全确定) | ~15-30% 抖动 | 极大 |
| 小 batch 带宽利用率 | 75-90% | ~1% | 75-90× |
| 编译器 vs 硬件复杂度 | 编译器大, 硬件小 | 硬件大, 编译器小 | - |
| 功耗效率 (推理) | ~1-3 J/token | ~10-30 J/token | 10× |
| 确定性 SLA | ✓ Guaranteed | ✗ Probabilistic | - |

### 6.2 局限性

1. **编译时间长** — 不适合快速迭代的实验
2. **容量限制** — 230 MB 对大模型不足，需大量芯片
3. **不支持训练** — 没有动态调度能力
4. **软件生态** — 远不如 CUDA 成熟
5. **单芯片算力限制** — 188 TFLOPS (FP16) vs H100 989 TFLOPS

---

## 7. 参考文献

1. Abts, D. et al., ISCA 2020/2022.
2. *"The Virtuous Cycles of Determinism"*, Satnam Singh, 2022.
3. *"How is Groq so Fast?"* — Security Boulevard, 2024.
4. *"确定性的边界"* — 知乎, 2025.
5. *"算力之巅的逆向行驶：深度解析 Groq LPU 的确定性架构逻辑"* — EET China, 2025.
