# Round 3: Scale-out LPU 系统与机架级架构

> 创建时间: 2026-05-19
> 状态: Research Complete

## 一、GroqNode 服务器规格

### 1.1 GroqNode 4U 服务器

| 参数 | 规格 |
|------|------|
| **型号** | GroqNode Server |
| **外形** | 4U 机架式 |
| **尺寸** | 7.0" (H) × 17.2" (W) × 29" (D) |
| **GroqCard 数量** | 最多 8 张 |
| **宿主 CPU** | 2× AMD EPYC 7313 (3 GHz, 16C/32T, 155W TDP) |
| **宿主内存** | 1 TB DDR4-3200 ECC (16× 64GB RDIMMs) |
| **电源** | 4 × 2000W 冗余 (220-240VAC) |
| **网络** | 200Gb/s HDR InfiniBand 或 Ethernet NIC |

### 1.2 GroqCard 规格

| 参数 | 规格 |
|------|------|
| **型号** | GC1-010B |
| **外形** | 双宽、全高、3/4 长 PCIe Gen 4 ×16 |
| **TSP 芯片** | 1 × GroqChip (14nm, 900 MHz) |
| **计算性能** | 750 TOPS (INT8), 188 TFLOPS (FP16) |
| **片上 SRAM** | 230 MB/chip |
| **内存带宽** | 80 TB/s (片内) |
| **典型功耗** | ~240W (典型), 375W (最大) |
| **C2C 连接器** | 88 个 RealScale C2C 连接器 |

## 二、系统部署层级

### 2.1 GroqRack 配置

```
GroqRack（标准部署）
├── 1 个管理节点（冗余）
├── 8 个计算节点
│   └── 每个节点 8 张 GroqCard
├── 合计: 72 个 TSP
├── 总片上 SRAM: 72 × 230 MB = 16.56 GB
├── 总计算性能: 72 × 750 TOPS = 54,000 TOPS (INT8)
└── 机架内延迟: 1.6 μs
```

### 2.2 Argonne ALCF 部署（实际系统）

| 参数 | 数值 |
|------|------|
| **节点数** | 9 个 GroqNode |
| **TSP 数** | 72 个 |
| **网络拓扑** | Dragonfly 多芯片拓扑 |
| **用途** | AI 推理研究 |
| **编程方式** | GroqWare 套件 + MLIR 接口 |

### 2.3 最大扩展配置

| 参数 | 数值 |
|------|------|
| **机架数** | 145 个 |
| **TSP 总数** | 10,440 个 |
| **全局 SRAM** | > 2 TB |
| **端到端延迟** | < 3 μs |
| **最大网络跳数** | 5 跳 |
| **带宽/TSP** | ~14 GB/s (超出 264 TSPs 后) |

## 三、功耗分析

### 3.1 各级功耗估算

| 层级 | 组件功耗 | 合计功耗 |
|------|---------|---------|
| **单个 TSP** | ~40W (典型), 375W (峰值) | 40-375W |
| **GroqNode 服务器** | 8 TSPs × ~240W + 主机 ~300W | ~2.2 kW (典型) |
| **GroqRack（72 TSPs）** | 9 × 2.2 kW | ~19.8 kW (典型) |
| **最大系统（145 机架）** | 145 × 19.8 kW | ~2.87 MW (典型) |

注：早期 5U GroqNode（2020 版）整机功耗 ~3.3 kW，后续优化降低。

### 3.2 功耗效率对比

| 指标 | Groq TSP | NVIDIA A100 | NVIDIA H100 |
|------|---------|------------|------------|
| **TOPS/W (INT8)** | ~3.1 (750/240) | ~1.5 (624/400) | ~2.0 (1979/700) |
| **每卡功耗** | ~240W (典型) | ~400W (TDP) | ~700W (TDP) |
| **内存功耗优势** | 无 HBM（纯 SRAM） | 需要 HBM 堆叠 | 需要 HBM 堆叠 |
| **互联功耗** | 低（TSP 兼交换机） | 高（额外交换机） | NVSwitch 额外功耗 |

## 四、散热方案

### 4.1 标准散热：风冷

Groq 声明其 LPU/GroqRack **"无需复杂冷却和电力基础设施"**：
- 标准风冷设计
- 不需要液冷
- 4U 机箱内置风扇组
- 适合标准数据中心部署

### 4.2 先进散热研究：微喷冷却（Microjet Cooling）

**IEEE ITherm 2024 论文**（普渡大学 + Groq Inc.）探索了直接片上微喷冷却：

> 论文标题: "Direct-On-Chip Hotspot Targeted Microjet Cooling for Ultra-fast Inference at Scale Running on Groq Language Processing Unit (LPU)"

| 参数 | 效果 |
|------|------|
| **喷嘴配置** | 定制入口喷嘴直径、间距、流量 |
| **热点匹配** | 根据芯片功率分布定制喷头 |
| **温度均匀性** | 逻辑芯片上温差 < 4°C |
| **热耦合** | 显著降低 LPU 与相邻 chiplet 的热耦合 |
| **适用场景** | 未来高密度 LPU 部署 |

### 4.3 散热方案路线

```
Gen 1: 标准风冷
  └── 适用于 ~40W/TSP 典型负载
  └── 4U 机箱风扇组
  └── 标准数据中心部署

Gen 2: 增强风冷 + 微喷（研发中）
  └── 针对热点定向冷却
  └── 更高功率密度
  └── < 4°C 芯片温度均匀性

Gen 3: 液冷（未来可能）
  └── 适应更高密度 TSP
  └── 更大规模部署的能效优化
```

## 五、网络接口与扩展

### 5.1 RealScale C2C 连接

- 每个 GroqNode 有 **88 个 RealScale C2C 连接器**
- 支持 **32 个 RealScale 外部端口** 用于集群互联
- 支持 200Gb/s HDR InfiniBand 作为主机网络

### 5.2 系统弹性

- **8+1 冗余节点设计** — 9 个节点中 1 个为冗余
- 编译器可在运行时适应可用 TSP 数量
- 无单点故障路径

## 六、Groq LPU 编程栈

| 层级 | 组件 |
|------|------|
| **应用框架** | PyTorch, TensorFlow (通过 GroqFlow) |
| **编译器** | Groq Compiler（静态调度） |
| **中间表示** | MLIR (Multi-Level Intermediate Representation) |
| **驱动** | GroqWare 套件 |
| **硬件** | GroqCard (TSP) |

## 七、关键参考

- GroqNode Server Specification (groq.sa)
- GroqRack Specification (groq.sa)
- ALCF Argonne Groq System Overview
- IEEE ITherm 2024: "Direct-On-Chip Hotspot Targeted Microjet Cooling for Groq LPU"
- Groq Blog: "Introducing the LPU"
- EET China / EDN China: Groq LPU Architecture Deep Dives
