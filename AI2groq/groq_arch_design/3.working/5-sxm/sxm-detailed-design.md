# SXM — 移位执行模块详细设计分析
# SXM — Shift/Switch Execution Module Detailed Design Analysis

> 创建时间: 2026-05-19T1730
> 分析层级: Layer 2 (微架构深度展开)

---

## 1. 概述 (Overview)

SXM (Switch Execution Module) 是 Groq TSP 的数据移动与形状变换引擎。根据 Groq 专利 US20240037064A1，SXM 实现为 **lane switching slice**，可以将数据从任意数据通道路由到任意其他数据通道。SXM 承担了传统芯片中 crossbar、shuffle network、permuter 和部分网络接口的功能。

### 命名变体 (Naming)

| 来源 | 名称 | 强调功能 |
|------|------|---------|
| ISCA 2020 | SXM | Switch Execution Module |
| Groq 专利 | NET / Lane Switching Slice | 网络/通道切换 |
| 部分分析 | SXM | Shift Execution Module |
| 功能描述 | Permute/Shuffle | 排列/重排 |

### 架构位置

```
每个 Super Lane 包含 2 个 SXM:
  MXM → SXM → MEM → VXM → MEM → SXM → MXM
          ↑                     ↑
        SXM_L                 SXM_R

SXM 作为 MEM 和计算单元 (MXM/VXM) 之间的数据路由枢纽
```

---

## 2. 功能集 (Function Set)

### 核心功能

| 功能 | 操作 | 描述 |
|------|------|------|
| **Shift** | 移位 | 向量元素左移/右移，移出位丢弃，空缺填 0 |
| **Rotate** | 旋转 | 循环移位，移出位补到另一侧 |
| **Permute** | 排列 | Lane 间任意元素重排 |
| **Broadcast** | 广播 | 将单 lane 数据复制到所有/部分 lanes |
| **Gather** | 收集 | 从多个 lane 收集数据到目标 lane |
| **Scatter** | 散播 | 将一个 lane 的数据分发到多个 lane |
| **Transpose** | 转置 | 矩阵转置的 lane 级实现 |
| **Interleave** | 交错 | 多数据流的交错合并 |
| **Select** | 选择 | 按 mask 选择特定 lanes |
| **Pack/Unpack** | 打包/解包 | 数据格式重组 |

### SXM 数据流角色

```
典型神经网络中的 SXM 应用:

Attention 层:
  MEM(Q) → SXM(路由/重排) → MXM(Q×Kᵀ) → SXM(转置) → VXM(Softmax)
  MEM(K) → SXM(路由/重排) ↗               SXM(重排) → MXM(×V)
  MEM(V) → SXM(路由) ────────────────────────────── ↗
  MXM(out) → SXM(重排) → MEM(写回)

全连接层:
  MEM(weights) → SXM(广播) → MXM(矩阵乘) → SXM(收集) → MEM(写回)
```

---

## 3. Crossbar 实现 (Crossbar Implementation)

### 1D Tiled Crossbar 架构

基于专利描述，SXM 的 crossbar 实现推测如下:

```
SXM Crossbar (20 lanes × 32 bytes/lane):
                    输出 Lanes
         ┌──────────────────────────────────────────┐
         │ Lane 0  Lane 1  Lane 2  ...  Lane 19     │
         │  ┌─┐    ┌─┐    ┌─┐          ┌─┐         │
 输入    │  │ │    │ │    │ │          │ │         │
 Lane 0 ─┼─┤ ├───►│ │    │ │    ...   │ │         │
         │  │ │    │ │    │ │          │ │         │
 Lane 1 ─┼─┤ ├────┤ ├───►│ │    ...   │ │         │
         │  │ │    │ │    │ │          │ │         │
 Lane 2 ─┼─┤ ├────┤ ├────┤ ├───►...  │ │         │
         │  │ │    │ │    │ │          │ │         │
   ...   │  ...    ...    ...          ...         │
         │  │ │    │ │    │ │          │ │         │
Lane 19 ─┼─┤ ├────┤ ├────┤ ├───►...  │ │         │
         │  └─┘    └─┘    └─┘          └─┘         │
         └──────────────────────────────────────────┘
         
         虚线: 可编程连接 (编译器配置)
```

### Crossbar 参数

| 参数 | 数值 |
|------|------|
| 输入通道 | 320 (20 SL × 16 lanes) |
| 输出通道 | 320 |
| 每通道宽度 | 32 bytes |
| 总 crossbar 宽度 | 10,240 bytes (320×32) |
| 实现方式 | 1D tiled crossbar 或 permuter circuit |
| 路由 | 编译器静态预配置 |
| 延迟 | 1-2 cycles (推测) |

### Tiled Crossbar vs 全 Crossbar

| 特性 | 全 Crossbar | Tiled Crossbar (SXM) |
|------|------------|-------------------|
| 复杂度 | O(N²) | O(N × tile_size) |
| 面积 (N=320) | ~1M 连接点 | ~20K 连接点 (tile=16) |
| 延迟 | ~1 cycle | ~1-2 cycles |
| 灵活性 | 任意排列 | 块内任意, 块间有限 |

实际 SXM 可能实现为混合结构:
- 16-lane block 内: 全 crossbar (任意排列)
- Block 间: 固定/有限模式

---

## 4. Permute 操作详解 (Permute Operations)

### 基本排列模式

```
1) 恒定移位 (Constant Shift):
   Input:   [A0, A1, A2, ..., A15]
   Shift 3: [0,  0,  0,  A0, ..., A12]
   
2) 旋转 (Rotate):
   Input:   [A0, A1, A2, ..., A15]
   Rot 3:   [A13, A14, A15, A0, A1, A2]
   
3) 反向 (Reverse):
   Input:   [A0, A1, A2, ..., A15]
   Reverse: [A15, A14, A13, ..., A0]
   
4) 广播 (Broadcast):
   Input:   [A0, A1, A2, ..., A15]
   Bcast 0: [A0, A0, A0, ..., A0]
   
5) 交错 (Interleave):
   Input A: [A0, A1, A2, ..., A7]
   Input B: [B0, B1, B2, ..., B7]
   Interleave: [A0, B0, A1, B1, ..., A7, B7]
```

### 编译器预配置

SXM 的 permute 模式在编译时确定:

```
// 伪代码: 编译器配置 SXM
sxm_config_t config;
config.lane_map[0] = 3;    // Lane 0 输出从 Lane 3 输入
config.lane_map[1] = 7;    // Lane 1 输出从 Lane 7 输入
...
config.broadcast_enable = 0;
config.rotate_amount = 0;

// 在程序执行前配置 SXM
SXM_configure(&config, stream_id);
```

### 延迟分析

| 操作 | 估计延迟 (cycles) |
|------|-----------------|
| 简单移位 | 1 |
| Lane 内旋转 | 1 |
| Lane 间排列 (block 内) | 1 |
| Lane 间排列 (block 间) | 1-2 |
| 广播 | 1 |
| 收集/散播 | 1-2 |
| 全 crossbar | 2 |

---

## 5. 与其他模块的交互 (Inter-module Interaction)

### 数据流连接

```
SXM 的输入/输出连接:

西侧连接:
  ← 从西侧 MXM/MEM 接收数据
  → 向西侧 MXM/MEM 发送数据

东侧连接:
  ← 从东侧 MXM/MEM 接收数据  
  → 向东侧 MXM/MEM 发送数据

垂直连接 (C2C/PCIe):
  ↑ 向上连接到更高 SL 的 SXM
  ↓ 向下连接到更低 SL 的 SXM
  
片外连接:
  C2C (Chip-to-Chip): 多 TSP 间直连
  PCIe: 主机通信
```

### C2C (Chip-to-Chip) 接口

SXM 承担片间通信功能:

```
TSP 0                     TSP 1
┌─────────────────┐      ┌─────────────────┐
│ ...              │      │              ...│
│ SXM ──C2C Link──┼──────┼── SXM          │
│ ...              │      │              ...│
└─────────────────┘      └─────────────────┘

C2C 特性:
  - 高带宽片间互联 (推测: 数百 GB/s)
  - 编译器静态调度通信
  - 无自适应路由 — 通信模式在编译时已知
  - DESKEW 指令同步多 TSP
```

---

## 6. 典型操作序列 (Typical Operation Sequences)

### Sequence 1: 矩阵乘前数据准备

```
操作: 将 MEM 中的数据路由到 MXM 进行矩阵乘

SXM 操作序列:
1. MEM_L → SXM_L: 读取权重数据
2. SXM_L: Permute 排列 (将数据排布为 MXM 所需格式)
3. SXM_L → MXM_L: 将排列后的权重传入 MXM 的权重寄存器
4. MEM_R → SXM_R: 读取激活值数据
5. SXM_R → MXM_R: 将激活值传入 MXM

编译器调度:
  权重加载 < 40 cycles
  激活值流持续输入
```

### Sequence 2: Attention 中的 Softmax 重排

```
操作: Attention score 矩阵的转置 + Softmax

SXM 操作序列:
1. MXM_L → SXM_L: 接收 Q×Kᵀ 结果
2. SXM_L: Transpose (矩阵转置)
3. SXM_L → VXM: 将转置结果传入 VXM
4. VXM: 执行 Softmax
5. VXM → SXM_R: 将 attention 权重传入 SXM_R
6. SXM_R → MXM_R: 将 attention 权重传入 MXM_R × V
```

### Sequence 3: 跨 lane 归约

```
操作: 跨 16 lanes 求和归约

SXM 操作序列:
1. MEM → SXM: 16 lanes 的数据
2. SXM: Tree Reduction
   - Level 1: Lane 0+1, 2+3, ..., 14+15 → 8 个部分和
   - Level 2: 8 → 4 个部分和
   - Level 3: 4 → 2 个部分和
   - Level 4: 2 → 1 个最终结果
3. SXM → MEM: 归约结果写回
```

---

## 7. 面积与功耗 (Area & Power)

### SXM 面积分解 (推测)

| 子模块 | 单个 SXM | 全芯片 (40 SXM) |
|--------|---------|----------------|
| Crossbar 网络 (320×32B) | ~4 mm² | ~160 mm² |
| Permuter 逻辑 | ~1 mm² | ~40 mm² |
| 缓冲/流水线寄存器 | ~1 mm² | ~40 mm² |
| C2C/PCIe 接口 | ~2 mm² | ~80 mm² |
| 控制/配置逻辑 | ~0.5 mm² | ~20 mm² |
| **SXM 总计** | **~8.5 mm²** | **~340 mm²** |

注: 实际面积可能更小，因为 crossbar 分为多个 tiled 结构。

### 面积优化

Tiled crossbar 显著减少面积:

```
全 crossbar 面积: O(N²) = O(320²) ≈ 102,400 交叉点
Tiled crossbar: O(N × k) = O(320 × 16) ≈ 5,120 交叉点 (每 tile)
20 tiles × 5,120 ≈ 102,400 — 实际上不会采用全连接

更合理:
  16×16 tile 内部: 256 交叉点
  20 tiles: 5,120 交叉点
  每 tile 32 bytes: 163,840 位交叉点
```

---

## 8. 编程模型视角 (Programming Model View)

### 编译器视角

编译器将 SXM 视为可编程数据路由网络:

```
// 伪代码: SXM 操作在编译器 IR 中的表示
Stream s1 = MEM.read(address_A, east);     // MEM → 东向流
Stream s2 = SXM.permute(s1, pattern_B);    // SXM 重排
Stream s3 = MXM.matmul(s2, weights);       // MXM 矩阵乘
Stream s4 = SXM.broadcast(s3, lane_0);     // SXM 广播
Stream s5 = VXM.activate(s4, RELU);        // VXM 激活
MEM.write(s5, address_C, west);            // 写回 MEM
```

### Stream 模型

```
每个数据流在 SXM 处可以:
1. Pass-through: 直接通过，无修改
2. Permute: 一次性重排
3. Broadcast: 复制到多个 lanes
4. Gather: 从多个 lane 收集
5. Route: 改变方向 (E↔W)

编译器在编译时选择最佳的路由和排列方案
```

---

## 9. 关键技术挑战 (Technical Challenges)

### 物理设计挑战

| 挑战 | 描述 | TSP 方案 |
|------|------|---------|
| 布线拥塞 | Crossbar 需要大量互连线 | Tiled 结构减少布线 |
| 延迟 | 大 crossbar 延迟高 | 1D tiled + 流水线化 |
| 面积 | Crossbar 面积 O(N²) | Tiled 结构 O(N×k) |
| 功耗 | 长互线高动态功耗 | 编译器优化减少切换 |

### 编译器挑战

| 挑战 | 描述 | 解决方案 |
|------|------|---------|
| 路由优化 | 最小化数据移动延迟 | 静态路由规划 |
| 排列选择 | 从多种排列中选最优 | 编译时枚举和评估 |
| 冲突避免 | 避免 SXM 资源冲突 | 流水线调度 |
| 片间通信 | 多 TSP 同步 | DESKEW + 静态规划 |
