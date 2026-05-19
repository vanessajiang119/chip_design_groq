# Multi-TSP 互联架构分析 — 研究规划

> 创建时间: 2026-05-19
> 分析师: Groq Multi-TSP Interconnect Expert
> 状态: Planning

## 1. 研究目标

深入分析 Groq TSP 之间的互联拓扑和 scale-out 架构，重点理解：

- **Dragonfly 拓扑**在 10,440 TSP 规模下的设计原理
- **TSP 间通信**的数据传递机制、延迟和带宽
- **编译器静态网络调度** — 确定性路由与链路负载均衡
- **Scale-out LPU 系统** — 机架级架构、功耗、散热方案

## 2. 递归研究架构

```
Layer 1: Multi-TSP 互联架构分析
  ├── Layer 2: Dragonfly 拓扑参数
  │   ├── Radix、group size、global link 配置
  │   ├── 死锁避免策略（确定性 vs adaptive 路由）
  │   └── 与 InfiniBand/HPC 拓扑对比
  ├── Layer 2: TSP 间通信协议
  │   ├── 消息格式与数据包结构
  │   ├── 同步机制（barrier、fence）
  │   ├── 通信延迟与带宽参数
  │   └── Channel/tile 级别的物理实现
  ├── Layer 2: 编译器网络调度
  │   ├── 静态路由分配算法
  │   ├── 链路负载均衡策略
  │   └── 确定性 timing 保证
  └── Layer 2: 系统级架构
      ├── 机架 / LPU 系统布局
      ├── 功耗密度分析
      └── 散热方案（微喷冷却）
```

## 3. 搜索策略

### Round 1: Dragonfly 拓扑基础 + Groq ISCA 2022
- 搜索关键词: `Groq dragonfly topology`, `Groq ISCA 2022 multi-TSP`, `Groq TSP interconnect software-defined`
- 目标: 获取 Dragonfly 拓扑在 Groq 中的具体实现参数

### Round 2: TSP 通信 + 编译器调度
- 搜索关键词: `Groq TSP-to-TSP communication latency bandwidth`, `Groq static routing compiler`, `Groq network schedule deterministic`
- 目标: 理解 TSP 间通信的具体机制和编译器调度方法

### Round 3: Scale-out LPU + 系统架构
- 搜索关键词: `Groq LPU rack system scale-out`, `Groq cooling microjet`, `Groq LPU power consumption`
- 目标: 获取机架级系统架构和散热方案细节

## 4. 输出计划

| 阶段 | 交付物 | 格式 |
|------|--------|------|
| Phase 1 | 规划文档 | `planning.md` |
| Phase 2 | Round 1-3 搜索结果 | `round-1.md` ~ `round-3.md` |
| Phase 3 | Layer 2 深度分析（4 topics） | `3.working/*.md` |
| Phase 4 | 汇总报告 | `4.result/aggregated-report.md` |

## 5. 参考来源

- ISCA 2022: "A Software-Defined Interconnect for Multi-TSP Systems" (Jouppi et al.)
- ISCA 2020: "Groq: A TSP for Deep Learning" (Abts et al.)
- Hot Chips 2022: Groq LPU presentation
- Groq Blog: Technical deep dives
- IEEE Micro: Groq TSP special issue
