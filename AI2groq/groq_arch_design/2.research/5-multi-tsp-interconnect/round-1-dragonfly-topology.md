# Round 1: Groq Multi-TSP Dragonfly 拓扑分析

> 创建时间: 2026-05-19
> 状态: Research Complete

## 一、Dragonfly 拓扑概述

Groq 的 Multi-TSP 互联采用 **软件定义的 Dragonfly 拓扑（software-defined Dragonfly topology）**，在 ISCA 2022 获奖论文 *"A Software-defined Tensor Streaming Multiprocessor for Large-scale Machine Learning"* 中详细描述。每个 TSP 同时扮演 **计算端点（endpoint）** 和 **网络交换机（network switch）** 的角色。

Dragonfly 拓扑的核心思想：用高 radix 的路由器将网络组织为 **group（组）**，组内全连接，组间用少量 global link 互联。

## 二、拓扑参数详解

### 2.1 每个 TSP 的物理链路

| 参数 | 数值 |
|------|------|
| **Local links（局部链路）** | 7 条 — 用于节点内（intra-node）互联 |
| **Global links（全局链路）** | 4 条 — 用于跨节点和跨机架互联 |
| **合计物理链路** | 11 条 C2C（Chip-to-Chip）链路 |
| **每链路带宽** | 25 Gbps/lane × 4 lanes = **100 Gbps** |
| **SerDes 速率** | 30 Gbps per lane（第一代 TSP） |
| **每链路有效带宽** | ~15 GB/s（单向上） |

### 2.2 系统封装层级

```
Level 1: Node（节点 / Group）
├── 8 TSPs 在一个 4U 机箱
├── 7 local links × 8 TSPs = 全连接拓扑（all-to-all）
├── 所有 global link 聚合为 32 端口虚拟路由器
└── Dragonfly 的 "group"

Level 2: Rack（机架）
├── 9 Nodes × 8 TSPs = 72 TSPs
├── 其中 8 个计算节点 + 1 个冗余节点
├── 机架内通过 global link 互联
└── 半端口用于内部，半端口用于跨机架

Level 3: Max System（最大系统）
├── 145 机架 × 72 TSPs = 10,440 TSPs
├── 全局共享 SRAM > 2 TB
└── 端到端延迟 < 3 μs
```

### 2.3 虚拟路由器设计

每个 Node（8 TSPs）的 4 条 global link 聚合为 **32 端口虚拟路由器**：
- 这是 Dragonfly 拓扑中的 "group" 构建块
- 高 radix 虚拟路由器减少了网络直径
- 最大系统任意两 TSP 之间的 **最大跳数为 5 跳**

### 2.4 带宽扩展曲线

| TSP 规模 | 每 TSP 全局带宽 | 注释 |
|----------|-----------------|------|
| < 16 TSPs | 极高（利用密集节点内布线） | 节点内全连接 |
| 16–264 TSPs | ~50 GB/s | 3 跳 Dragonfly 内 |
| > 264 TSPs（至 10,440） | ~14 GB/s | Dragonfly 提供扁平带宽 |
| 全局 bisection 带宽 | 随规模近似线性扩展 | 软件定义路由避免了拥塞 |

## 三、Dragonfly 拓扑对比

| 特性 | Groq Dragonfly | InfiniBand Fat-Tree | NVIDIA NVSwitch |
|------|---------------|-------------------|-----------------|
| 网络直径 | 最大 5 跳 | O(log N) | 1 跳（单平面） |
| 路由方式 | 编译器静态调度 | 自适应路由（通常） | 硬件路由 |
| 死锁避免 | 编译器保证 | VC 隔离 | 硬件保证 |
| 每跳延迟 | 极低（无头/尾开销） | 中等 | 低 |
| 控制开销 | ~2.5% | 较高（包头部） | 中等 |
| 扩展性 | 10,440 TSPs | 数千节点 | 数百 GPU |

## 四、物理层实现

### 4.1 链路类型

| 链路类型 | 电缆 | 距离 | 速率 |
|----------|------|------|------|
| 节点内（local link） | 铜缆 34 AWG | 0.75m | 30 Gbps/lane |
| 机架内 | QSFP 铜缆 | < 2m | 25 Gbps/lane |
| 跨机架 | 有源光缆 | 长距离 | 25 Gbps/lane |

### 4.2 关键指标

- **每 TSP 功耗**: ~40W（典型负载），最大 ~375W（GroqCard 峰值）
- **每 TSP SRAM**: 220-230 MiB
- **全局内存总量**: > 2 TB（10,440 TSPs 时）
- **端到端延迟**: < 3 μs（任意两 TSP 间）
- **控制开销**: 仅 ~2.5% 头部/尾部标记

## 五、技术优势总结

1. **平坦带宽** — Dragonfly 提供近似常数的每节点全局带宽，突破传统拓扑的带宽瓶颈
2. **低直径** — 最大 5 跳连接任意两个 TSP，10,440 节点规模下远优于 Fat-Tree
3. **无动态竞争** — 编译器预调度消除了链路冲突和拥塞
4. **TSP 即交换机** — 消除专用交换机硬件，每 TSP 的 global link 直接构建虚拟路由器
5. **软件定义的灵活性** — 拓扑参数可通过编译器重新配置，适应不同 workload

## 六、关键参考

- ISCA 2022: "A Software-defined Tensor Streaming Multiprocessor for Large-scale Machine Learning"
- ISCA 2020: "Groq: A TSP for Deep Learning" (Abts et al.)
- ALCF Groq System Overview (Argonne Leadership Computing Facility)
- GroqNode Server Specification (groq.sa)
