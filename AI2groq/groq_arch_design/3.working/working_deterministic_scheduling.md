# Working: 确定性调度算法 — Layer 2 深度分析

> 创建时间: 2026-05-19
> 分析层级: Layer 2 — 编译器静态调度算法与数据结构

---

## 1. 调度问题定义

Groq 编译器需要解决一个高度约束的全局调度问题：

### 1.1 调度输入

```
输入:
  ├── 计算图 (来自 MLIR) — 节点: 操作, 边: 数据依赖
  ├── 硬件模型 — 144 队列, 20 SuperLanes, 320 lanes
  ├── 延迟表 — 每条指令的 cycle 延迟
  ├── 资源约束 — 每切片每 cycle 最多 N 条指令
  └── SRAM 分配 — 220 MB 静态分配
```

### 1.2 调度输出

```
输出:
  ├── 每条指令的发射 cycle
  ├── 每条指令的目标功能切片和 SuperLane
  ├── 每个 stream 的 ID、方向、时序
  ├── 每个数据包的网络路由路径
  └── SRAM 地址分配
```

### 1.3 约束条件

1. **数据依赖**: 消费者必须在生产者完成之后开始
2. **资源限制**: 每切片每 cycle 指令数不超过上限
3. **Stream 资源**: 总并发流不超过 64/通道
4. **SRF 深度**: 流缓冲区不溢出
5. **内存端口**: SRAM 访问端口冲突避免
6. **网络带宽**: 功能切片间数据总线宽度限制

## 2. 调度算法架构

### 2.1 编译器工具链概览

```
用户代码 (Python, C++)
     │
     ▼
GroqFlow (Python frontend)
     │  张量计算图 + 模型定义
     ▼
MLIR (Multi-Level Intermediate Representation)
     │  TBDialect — Groq 自定义方言
     │  Tiling, fusion, buffer allocation
     ▼
Groq Compiler (Haskell backend)
     │  静态调度 + 代码生成
     ▼
TSP 二进制 (.groqbin)
```

### 2.2 调度阶段

```
阶段 1: 计算图优化
  └── 算子融合 (fuse element-wise ops)
  └── 内存规划 (buffer 复用)
  └── 张量分片 (tiling for 320 lanes)

阶段 2: 资源分配
  └── 流 ID 分配
  └── SRAM bank 分配
  └── 功能切片指派

阶段 3: 时序调度 (核心)
  └── 列表调度 (list scheduling) + 约束传播
  └── 每个队列的指令序列生成
  └── 流水线平衡

阶段 4: 验证
  └── 时序正确性检查
  └── 资源冲突检查
  └── 延迟预测 (cycle-accurate)
```

### 2.3 列表调度 (List Scheduling) 核心

编译器使用改进的列表调度算法：

```
伪代码:
  ready_list = {无依赖的节点}
  scheduled = {}
  time = 0
  
  while ready_list not empty:
    for each 功能切片类型 t:
      available = {n ∈ ready_list | n.type == t}
      // 按 criticality 排序
      sort(available, key = critical_path_length, desc)
      // 在时间槽内安排
      schedule(available[:slot_limit[t]], time)
      remove scheduled from ready_list
    
    // 更新 ready_list
    for each 已完成操作:
      将其消费者的依赖计数减 1
      if 依赖计数 == 0:
        加入 ready_list
    
    time = time + 1
```

## 3. 延迟模型

### 3.1 指令延迟表

编译器维护精确的指令延迟表，每条指令有固定延迟：

| 指令类型 | 延迟 (cycles) | 执行单元 |
|---------|--------------|---------|
| MATMUL (INT8, 320×320) | ~900 | MXM |
| VECTOR_ADD | ~20 | VXM |
| VECTOR_MUL | ~20 | VXM |
| GELU | ~30 | VXM |
| LOAD (512B) | ~12 | MEM |
| STORE (512B) | ~12 | MEM |
| SHIFT | ~18 | SXM |
| PERMUTE | ~18 | SXM |

### 3.2 确定性延迟的来源

为什么 TSP 的指令延迟是固定的？
1. **无 cache miss**: 所有访存都是 SRAM，延迟固定
2. **无 bank conflict**: 编译器确保 bank 不冲突
3. **无仲裁延迟**: 所有路径预先安排
4. **无数据相关延迟**: 浮点/整数操作的延迟固定
5. **静态流水线**: 无流水线交错

## 4. 数据结构

### 4.1 调度表 (Schedule Table)

编译器生成的核心数据结构是一个**二维调度表**：

```
行: 时间 (cycle 0, 1, 2, ...)
列: 指令队列 (0-143)

Schedule[cycle][queue] = 指令

示例:
Cycle 0:  [LOAD(R0), LOAD(R1), NOP, ..., VXM_ADD, ...]
Cycle 1:  [LOAD(R2), LOAD(R3), MXM_START, ..., ...]
...
Cycle N:  [STORE(R10), ..., ..., ..., ..., ..., ...]
```

### 4.2 流分配表 (Stream Allocation Table)

```
StreamID | 方向 | 源切片 | 目标切片 | 开始 cycle | 长度 | 数据类型
---------|------|--------|----------|-----------|------|--------
0        | East | MEM_3  | VXM_1    | 45        | 512  | INT8
1        | West | MXM_0  | MEM_2    | 200       | 256  | FP16
...      | ...  | ...    | ...      | ...       | ...  | ...
```

### 4.3 资源使用矩阵 (Resource Utilization Matrix)

```
            MXM  MXM  MXM  ...  VXM  VXM  ...  MEM  MEM
             s0   s1   s2       s0   s1       s0   s1
Cycle 0:    [1]  [0]  [0]      [1]  [1]      [1]  [1]
Cycle 1:    [1]  [1]  [0]      [0]  [1]      [1]  [0]
...
```

编译器使用此矩阵来确保没有资源冲突。

## 5. 调度优化的挑战

### 5.1 NP-hard 的调度问题

全局调度是 NP-hard 的，编译器使用启发式算法：
- **关键路径优先**: 最长路径上的指令先调度
- **资源平衡**: 均匀分布负载到所有功能切片
- **贪心着色**: 流 ID 分配使用贪心算法

### 5.2 编译器 vs 硬件调度的权衡

| 维度 | 硬件动态调度 (GPU) | 编译器静态调度 (Groq) |
|------|-------------------|---------------------|
| 调度质量 | 运行时自适应 | 编译时全局优化 |
| 灵活性 | 应对任意输入 | 输入形状固定 |
| 开销 | 面积 + 功耗 | 编译时间 + 编译器复杂度 |
| 可预测性 | 低 (P99 抖动) | 高 (完全确定性) |
| 动态负载 | 优秀 | 差 |

### 5.3 编译器复杂度的量化

GroqFlow 编译器使用 MLIR 和 Haskell，其复杂度体现在：
- **MLIR Dialect 定义**: TBDialect 描述 TSP 操作
- **Haskell 后端**: 函数式编程简化调度算法实现
- **数万行代码**: 实现精确的硬件模型和调度算法
- **编译时间**: 复杂模型可能需要数分钟到数小时编译

## 6. 同步与屏障的调度

### 6.1 SYNC 指令的插入

编译器在以下位置插入 SYNC:
1. 模型层边界 (Layer i → Layer i+1)
2. 计算阶段转换 (前向 → 反向)
3. 张量重用时 (资源重新分配前)
4. 流 ID 回收前

### 6.2 同步开销最小化

编译器尝试通过以下方式最小化 SYNC 开销：
- **NOTIFY 替代 SYNC**: 点对点通知比全局屏障更轻量
- **延迟容忍**: 通过调度隐藏屏障等待时间
- **流水线化**: 将 SYNC 与有用计算重叠

## 7. 结论与关键发现

1. **调度问题本质是 NP-hard**: Groq 使用改进的列表调度 + 启发式
2. **完整的延迟模型是基础**: 所有指令、内存、网络的延迟必须精确已知
3. **编译器复杂度巨大**: 数万行 MLIR + Haskell 代码
4. **静态调度的优势**: 确定性和低硬件开销
5. **静态调度的代价**: 编译时间长，动态负载处理能力差
6. **调度质量决定性能**: 编译器越好，芯片利用率越高
