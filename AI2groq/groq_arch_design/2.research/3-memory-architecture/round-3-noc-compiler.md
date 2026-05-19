# Round 3: Groq TSP 片上互联与编译器优化

> **时间**: 20260519-1630
> **重点**: SXM 交换模块、片上流式 NoC、编译器数据布局策略

---

## 1. SXM (Switch Execution Module) — 片上互联核心

### 1.1 SXM 的功能

SXM 是 Groq TSP 的**交换执行切片**，负责：

| 功能 | 说明 |
|------|------|
| **片上数据路由** | 在功能 slice 之间传递数据（MXM ↔ MEM ↔ VXM） |
| **数据重组** | 移位(shift)、旋转(rotate)、重排(swizzle) |
| **张量重塑** | tensor reshape、维度置换 |
| **片间路由** | 通过芯片间链路（C2C）将张量转发到其他 TSP |

### 1.2 每 Superlane 中的 SXM 布局

```
左MXM → 左SXM → 左MEM → VXM → 右MEM → 右SXM → 右MXM
                ↓                                  ↓
           片上数据路由                        片间数据路由
```

每个 Superlane 有 **2 个 SXM 单元**（左右对称），这意味着：
- 全芯片共 **40 个 SXM 单元**
- 每个 SXM 可以独立进行数据路由

---

## 2. 片上 NoC — 确定性流式互连

### 2.1 与传统 NoC 的对比

| 特性 | 传统 Crossbar | GPU Mesh NoC | Groq 流式 NoC |
|------|--------------|-------------|---------------|
| **路由方式** | 动态路由 | 动态仲裁 | **编译器静态调度** |
| **拥塞控制** | 硬件拥塞检测 | 硬件拥塞管理 | **不需要 — 无拥塞** |
| **仲裁** | 硬件仲裁器 | 硬件调度器 | **无仲裁器** |
| **延迟** | 可变 | 可变 | **固定延迟** |
| **协议** | 请求-响应 | load-store | **生产者-消费者流** |

### 2.2 两维流模型

```
        北 (指令流: ICU → Tile 19 → ... → Tile 0)
         ↑
         │    ┌─────────────────────────────┐
         │    │ MXM SXM MEM VXM MEM SXM MXM │
  西 ←───┼────┤                             ├───────→ 东 (数据流)
         │    │                             │
         │    └─────────────────────────────┘
         │          每个 Superlane × 16 lanes
         ↓
         ICU (指令控制单元)
```

- **指令流**: 垂直方向（南→北），从 ICU 向上传播，每 cycle 穿过一个 tile
- **数据流**: 水平方向（东/西），在每个 superlane 内流动
- **计算发生**: 指令流和数据流在精确的 cycle 于功能单元交汇

### 2.3 带宽分配

| 互联路径 | 带宽 | 说明 |
|----------|------|------|
| **片上流带宽** | **>60 TB/s** | 片上流寄存器文件(stream register file) |
| **片外 C2C 链路** | **512 GB/s** | 16 路 × 4 通道 × 25-30 Gbps |
| **片外节点内** | 8 TSP 全连接 | 节点内全互联 mesh |
| **片外机架间** | Dragonfly 拓扑 | 任意两点最多 5 跳 |

### 2.4 无仲裁的设计哲学

> "我们移除了所有反应式硬件，例如仲裁器和缓存。"

移除仲裁器的可行性：
- 所有通信模式在编译时已知
- 数据流是**生产者-消费者**模型，而非请求-响应
- 编译器可以交错安排 stream 时序避免冲突
- 不存在运行时竞争条件

---

## 3. 片间互联拓扑

### 3.1 系统层次

```
TSP 芯片 (1 个)
  └── TSP Node (8 个 TSP)
       │  └── 7 条本地 C2C 链路 (内部全连接 mesh)
       │  └── 4 条全局链路 (节点间通信)
       └── TSP Rack (9 个 Node = 72 TSP)
            └── Dragonfly 组拓扑
                 └── Max System (145 Racks = 10,440 TSP)
                      └── 任意两点最多 5 跳
```

### 3.2 引脚与链路

每个 TSP 芯片有 **11 个引脚**：

| 链路类型 | 数量 | 连接目标 | 总带宽 |
|----------|------|----------|--------|
| **本地链路** | 7 | 同节点内其他 TSP | 7 × 100 Gbps = 700 Gbps |
| **全局链路** | 4 | 跨节点/机架 | 4 × 100 Gbps = 400 Gbps |
| **合计** | 11 | | **1.1 Tbps per chip** |

### 3.3 同步机制

| 机制 | 功能 |
|------|------|
| **HAC** (Hardware Aligned Counters) | 多 TSP 间 cycle 级时钟同步 |
| **DESKEW 指令** | 校准跨 TSP 链路的偏斜 |
| **SYNC/NOTIFY** | 同步芯片上所有指令队列 |

> TSP 同时充当 **处理端点** 和 **网络交换机** — 编译器控制它何时扮演哪个角色。

---

## 4. 编译器数据布局优化

### 4.1 编译器面临的全局优化问题

> "编译器必须同时解决：lowering、layout、SRAM allocation、stream timing、function unit scheduling、cross-chip partition、network routing、和 synchronization。"

这是一个**多维联合优化问题**：

```
优化变量:
  ├── 张量布局 (哪个 MEM 单元？哪个 bank？)
  ├── SRAM 分配 (生命周期管理，空间复用)
  ├── Stream 时序 (每个 stream 何时出发)
  ├── 功能单元调度 (MXM/VXM/SXM 何时执行)
  ├── 跨芯片 partition (哪些层在哪些芯片上)
  └── 路由决策 (片上路径 + 片间路径)
```

### 4.2 数据布局阶段 (Data Layout)

**目标**: 将张量映射到 MEM 单元和 bank，最小化 bank 冲突和数据搬移距离。

**约束条件**:
- 每个 MEM 单元容量限制 (5.5 MB)
- Bank 访问冲突避免（同一 cycle 不能两次访问同一 bank）
- 数据局部性（靠近使用该数据的计算单元）

**策略**:
1. **权重存储**: 固定分配在靠近 MXM 的 MEM 单元
2. **激活/KV-cache**: 动态分配，编译器管理生存期
3. **跨 chip 张量并行**: 按输出通道切分（weight column split）

### 4.3 Stream 调度阶段 (Stream Scheduling)

```
编译器决策示例:

Cycle 0: MEM[L] 读取权重 W → Stream E0 (东向)
Cycle 1: Stream E0 到达 MXM[L]
Cycle 2: MXM[L] 开始矩阵乘
...
Cycle N: MEM[R] 读取激活 A → Stream W0 (西向)
Cycle N+1: Stream W0 到达 VXM
...
```

### 4.4 资源共享与冲突解决

| 冲突类型 | 编译器解决方案 |
|----------|---------------|
| **SRAM bank conflict** | 静态 bank 分配，通过偏移地址避免同时访问 |
| **Stream collision** | 时序上交错出发，或使用不同方向的 stream |
| **MEM 端口竞争** | 交错安排读写周期，利用 SRAM 双端口 |
| **C2C 链路争用** | 编译器显式分配链路时间槽，无动态竞争 |

### 4.5 跨芯片扩展策略

Groq 编译器支持多种并行策略：

| 策略 | 说明 | 适用场景 |
|------|------|----------|
| **Tensor Parallelism (TP)** | 按输出通道/head 切分 | Linear 层、Attention |
| **Pipeline Parallelism (PP)** | 按 layer 切分 | 深层网络 |
| **组合 TP+PP** | 同时使用两种并行 | 大模型 (70B+) |

---

## 5. 编译器复杂度对比

```
               GPU (CUDA)          Groq TSP
               ──────────          ──────────
硬件状态空间     大 (S_hw)             小 (S_hw)
  └─ 缓存           ✓                无
  └─ 分支预测       ✓                无  
  └─ 乱序执行       ✓                无
  └─ 动态调度       ✓                无

编译器状态空间    小 (S_compiler)     大 (S_compiler)
  └─ 调度时机      运行时               编译时
  └─ 内存管理      硬件/运行时           编译器
  └─ 网络路由      N/A                 编译器
  └─ 冲突解决      硬件                 编译器

设计哲学:        硬件复杂,编译器简单   硬件简单,编译器复杂
```

> 复杂度没有消失 — 只是从硬件运行时 **转移** 到了编译器。

---

## 6. 关键洞察

1. **SXM 是 NoC 的核心** — 40 个 SXM 单元提供了片上 + 片间的全面互联
2. **无仲裁器是可行的** — 因为所有流量模式在编译时已知
3. **编译器是真正的 "大脑"** — 负责布局、调度、路由、冲突解决的全局优化
4. **确定性是这一切的基石** — 没有确定性就没有静态调度的可行性

### 参考文献

1. Abts, D. et al., *"A Software-defined Tensor Streaming Multiprocessor for Large-scale Machine Learning"*, ISCA 2022.
2. *"The Virtuous Cycles of Determinism: Programming Groq's Tensor Streaming Processor"*, Satnam Singh, 2022 Keynote.
3. *"Groq Shares Recipe for TSP Nodes, Systems"*, The Next Platform, Sep 2020.
4. *"确定性的边界：从 GPU 到 Groq 的 AI 芯片谱系学"*, 知乎深度分析.
