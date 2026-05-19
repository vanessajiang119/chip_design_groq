# Layer 2 Deep Dive: 调度器算法 — List Scheduling, Modulo Scheduling, ILP
## Scheduler Algorithms — List Scheduling, Modulo Scheduling, ILP Solving

**Created:** 20260519-1050  
**Analyst:** Groq Compiler Architecture Expert  
**Layer:** 2 (Deep Technical Analysis)

---

## 1. 调度问题的形式化定义

### 1.1 输入

```
- DAG G = (V, E)
  - V: 操作集合 (每个操作有 type: MXM/VXM/MEM/SXM)
  - E: 数据依赖边 (从 producer 到 consumer)

- 硬件资源 R:
  - MXM_slices: 4 个 (推测)
  - VXM_slices: 4 个 (推测)
  - MEM_slices: 8 个 (推测)
  - SXM_slices: 4 个 (推测)
  - Queues: 144 个, 每个有最大深度 QD
  - Streams: 64/通道

- 操作延迟表 L(op_type):
  - MXM_matmul:    40 cycles (320×320 matmul)
  - MXM_conv:      50 cycles (3×3 conv, 特定配置)
  - VXM_relu:      2 cycles
  - VXM_add:       2 cycles
  - MEM_load:      4 cycles (SRAM → stream)
  - MEM_store:     4 cycles (stream → SRAM)
  - SXM_permute:   3 cycles
```

### 1.2 输出

```
为每个队列 q ∈ [1..144] 生成:
  - 指令序列 I_q = [i_{q,0}, i_{q,1}, ..., i_{q,n_q}]
  - 每条指令 i 有:
    - opcode
    - 操作数 (stream IDs, 地址, 立即数)
    - 发射周期 issue_cycle(i)
    - 完成周期 complete_cycle(i) = issue_cycle(i) + latency(i)

约束:
  ∀ 操作 i, j:
    (i, j) ∈ E ⇒ complete_cycle(i) < issue_cycle(j)  -- 数据依赖
  ∀ 队列 q: |I_q| ≤ QD  -- 队列深度
    
  ∀ 资源 r, 周期 t:
    同一周期使用同一资源的操作数 ≤ 1  -- 资源冲突
```

---

## 2. List Scheduling — 基础调度器

### 2.1 算法框架

List Scheduling 是 Groq 调度器的**基础骨架**，更复杂的策略（模调度、ILP）在其上叠加：

```
算法: GroqListScheduler
输入: DAG G = (V, E), 资源 R
输出: 调度方案 S

1. 优先级计算 (Priority Calculation)
   for each v ∈ V:
     priority(v) = height(v) + criticality(v)
     // height(v) = 到出口节点的最长路径长度
     // criticality(v) = 操作的资源稀缺程度

2. 候选集初始化
   ready = {v ∈ V | pred(v) = ∅}  // 无前驱的操作

3. 主循环
   while ready ≠ ∅:
     // 选择最高优先级操作
     v = select_highest_priority(ready)
     
     // 确定最早发射周期
     t_earliest = max({cycle(i) + delay(i, v) | i ∈ pred(v)})
     
     // 资源预留
     t = find_free_slot(v, t_earliest, R)
     
     // 分配到队列
     q = assign_queue(v)
     
     // 记录调度
     schedule(v, q, t)
     
     // 更新候选集
     ready = ready ∪ {succ(v) | ∀ pred(u) ∈ scheduled}
```

### 2.2 优先级启发式

对于 TSP 架构，优先级计算需要考虑额外的维度：

```haskell
-- 优先级计算 (综合了多个启发式)
priority :: Operation -> Float
priority op = 
    w1 * criticalPathHeight op    -- 关键路径权重
    + w2 * resourcePressure op    -- 资源压力权重
    + w3 * queueDistance op       -- 队列距离权重
    + w4 * streamPressure op      -- Stream 压力权重
    - w5 * slack op               -- 松弛度 (优先级反比)

-- 关键路径高度
criticalPathHeight op = case opType op of
    MXM_Op -> 1 + maxHeight children  -- MXM 操作在关键路径上的概率高
    MEM_Op -> 0.5 + maxHeight children  -- MEM 操作较轻
    _      -> maxHeight children

-- 资源压力: 该类型资源的竞争程度
resourcePressure op = 
    remainingOpsOfType (opType op) / totalSlices (opType op)
```

### 2.3 资源预留

`find_free_slot` 是调度器的核心 — 它需要同时检查多个资源维度：

```
find_free_slot(v, t_earliest, R):
  对 t = t_earliest to t_earliest + MAX_SEARCH:
    检查:
      1. op_type(v) 对应的 slice 在 t 是否空闲
      2. 目标队列 q 在 t 是否有空位
      3. 可用的 stream 寄存器足够
      4. 不会导致 bank conflict (如果是 MEM op)
      5. 跨芯片通信情况下, 远程 TSP 在 t 可用
      
    如果全部满足:
      return t
  否则:
    失败 → 触发 ILP 求解器 (见 Section 4)
```

---

## 3. Modulo Scheduling — 循环流水

### 3.1 为什么需要模调度

ML 推理工作负载的典型结构是**循环密集型**：

```
矩阵乘法 = 三重嵌套循环 (tiling over M, N, K)
卷积    = 六重嵌套循环 (batch, channel_out, channel_in, height, width, kernel)
Transformer = 序列上的循环 + batch 内并行的矩阵乘法
```

对于这些循环，经过 tiling 展开后，循环体被重复多次。模调度 (Modulo Scheduling) 用于**流水化循环体的每次迭代**。

### 3.2 模调度在 Groq TSP 上的应用

```
循环体 (1 次迭代):
  LD_A:  MEM[addr_a + i] → stream 1    [4 cycles]
  LD_B:  MEM[addr_b + i] → stream 2    [4 cycles]
  MUL:   MXM matmul stream_1, stream_2 → stream_3  [40 cycles]
  ST_C:  MEM[stream_3] → addr_c + i    [4 cycles]

模调度后的流水线 (Initiation Interval II = 1 cycle):

  Cycle 0:  LD_A (iter 0)
  Cycle 1:  LD_B (iter 0)
  Cycle 2:  LD_A (iter 1)    ← iter 1 在 iter 0 的 LD_B 后一个周期就开始了!
  Cycle 3:  LD_B (iter 1)
  Cycle 4:  LD_A (iter 2)
  Cycle 5:  LD_B (iter 2)
  ...
  Cycle 40: MUL (iter 0)     ← 40 cycle 延迟后, 第一个 matmul 出结果
  Cycle 41: MUL (iter 1)
  Cycle 42: MUL (iter 2)
  Cycle 43: ST_C (iter 0)    ← 写回开始
  Cycle 44: ST_C (iter 1)

关键参数:
  II (Initiation Interval) = 1 cycle
  Total cycles = N + II * (trip_count - 1)
                = 47 + 1 * (TILE_COUNT - 1)
```

### 3.3 最小 Initiation Interval 的计算

```haskell
-- 计算理论最小 II
minII :: LoopBody -> HardwareConfig -> Int
minII body config = max (resMII body config) (recMII body)

-- 资源约束 II: 由资源瓶颈决定
resMII body config = 
    maximum [ceiling (opCount body res / available res) 
            | res <- resources config]

-- 例如:
--   MXM ops/trip: 1, MXM slices: 1 → 1
--   MEM ops/trip: 2, MEM slices: 2 → 1
--   VXM ops/trip: 1, VXM slices: 1 → 1
--   resMII = max(1, 1, 1) = 1

-- 循环依赖 II: 由循环携带的依赖决定
recMII body = 
    maximum [ceiling (latency d / distance d) 
            | d <- loopCarriedDependencies body]
```

### 3.4 模调度器在 Groq 编译器中的位置

```
MLIR 前端展开循环为静态操作序列
        ↓
Haskell 调度器:
  步骤 1: 检测循环模式 (循环边界检测)
  步骤 2: 确定 II (尝试 II = 1, 2, 4, ... 直到成功)
  步骤 3: 模调度 (将迭代展开并交错)
  步骤 4: 展开边界处理 (prologue + kernel + epilogue)
  步骤 5: 铺设到 144 个队列
```

---

## 4. ILP 求解 — 冲突解决优化

### 4.1 ILP 在调度中的角色

List Scheduling 是贪心算法，不一定找到最优解。当遇到**调度冲突**（找不到 `find_free_slot`）时，Groq 的编译器可能回退到 ILP 求解：

```
触发条件:
  1. List scheduling 遇到无法解决的资源冲突
  2. 跨芯片通信的时间不匹配
  3. 关键路径上的延迟无法满足
  
ILP 求解:
  对调度的局部子图 (subgraph) 构建整数线性规划
  
  Variables:
    issue_t[v] ∈ ℕ: 操作 v 的发射周期
    
  Objective:
    minimize max(complete_cycle[v])
    
  Constraints:
    ∀ (u,v) ∈ E: complete_cycle[u] < issue_t[v]
    ∑ op_type(v, r, t) ≤ available[r, t]  ∀ resource r, time t
    ...

  求解范围: 局部 (5-20 个操作的窗口)
  求解器: 可能是 Gurobi, CPLEX, 或自定义分支定界
```

### 4.2 约束的双重性

ILP 求解器的强大之处在于可以表达跨资源的复杂约束：

```
双重资源约束示例:
  操作: 在 VXM 3 上执行 ADD
  约束 1: VXM 3 在周期 t 空闲
  约束 2: 输入数据 stream 在周期 t 之前到达 VXM 3
  约束 3: 输出 stream 在周期 t+2 之后可用
  约束 4: 目标 MEM slice 在周期 t+2 空闲
  约束 5: 所有 4 个约束同时满足
```

### 4.3 混合方法: List Scheduling + ILP

最可能的实现是混合方法：

```
Phase 1: 粗粒度 List Scheduling
  - 对整个 DAG 使用list scheduling
  - 生成近似调度
  - 标记冲突区域

Phase 2: 局部 ILP 优化
  - 对冲突区域 (subgraph ≤ 20 ops) 构建 ILP
  - 求解精确最优局部调度
  - 替换冲突区域的近似调度

Phase 3: 全局验证
  - 验证局部求解不破坏全局约束
  - 如果失败，扩大 ILP 窗口重试
```

---

## 5. 确定性 vs 性能的权衡

### 5.1 静态调度的代价

| 方面 | Groq (全静态) | GPU (动态) |
|------|--------------|-----------|
| **编译时间** | 长 (分钟级) | 短 (秒级 JIT) |
| **运行时开销** | 趋近于 0 | 有硬件调度开销 |
| **硬件复杂度** | 低 (无调度逻辑) | 高 (warp scheduler) |
| **代码密度** | 低 (所有操作展开) | 高 (动态线程) |
| **不规则计算** | 差 | 好 |
| **可预测性** | 极好 | 差 |

### 5.2 静态调度器设计空间

```
                ILP 精确求解
                    ↑
                    最优但慢
       ┌─────────────────────────┐
       │  Groq 调度器            │
       │  (混合方法)             │
       │                         │
  List │  ┌─────┐  ┌──────────┐ │  模调度
  Sched│  │ 贪心│→ │ILP 局部  │ │  ←─── (循环密集型)
    →  │  │调度 │  │优化      │ │
       │  └─────┘  └──────────┘ │
       └─────────────────────────┘
                    ↓
               更快的编译
```

---

## 6. 关键洞察 / Key Insights

1. **调度器的算法层次**: Groq 调度器不是单一算法，而是一系列算法的堆叠：
   - 外层: List Scheduling (整个 DAG)
   - 中层: Modulo Scheduling (循环体)
   - 内层: ILP Solving (冲突区域)

2. **确定性简化了调度**: 传统编译器面临的不确定性（缓存缺失？分支预测失败？）在 Groq 上不存在，这使得 ILP 求解高效且有效。

3. **编译时间的瓶颈**: 对于 LLM（千亿参数），DAG 中的操作数可能是百万级。全图 ILP 求解不可行，但贪心 + 局部 ILP 的混合方法是可扩展的。

4. **TSP 架构是调度器友好的**: 功能切片将操作映射到特定列，减少了调度维度。如果所有操作类型都可以在任何单元执行，调度复杂度会高得多。

---

**Next**: [Layer 2: 内存布局优化 — Stream 分配与 SRAM 管理](./layer2-memory-layout.md)
