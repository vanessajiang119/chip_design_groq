# Layer 2 Deep Dive: 内存布局优化 — Stream 分配与 SRAM 管理
## Memory Layout Optimization — Stream Allocation & SRAM Management

**Created:** 20260519-1100  
**Analyst:** Groq Compiler Architecture Expert  
**Layer:** 2 (Deep Technical Analysis)

---

## 1. TSP 内存层次全景

### 1.1 物理层次

```
层次 1: Streaming Registers (SR)  — 芯片上最快的存储
  容量: 64 个/通道 (32 East + 32 West)
  带宽: 32 bytes/stream/cycle
  位置: 在每个 tile 的路由器中
  管理: 编译器精确分配每个 stream 的生命周期

层次 2: Local SRAM — Tile 本地存储
  容量: ~11 MB/tile (推测), 总计 220 MB
  延迟: 4 cycles (load/store)
  管理: 编译器分配所有数据的物理地址

层次 3: Weight Tile Buffers — MXM 专用
  容量: 320 × 320 × 2 bytes ≈ 204.8 KB/tile (FP16)
  加载: 所有 4 个 tile 可在 40 cycles 内加载
  角色: systolic array 的权重缓冲区

层次 4: Inter-Chip Links — 芯片间通信
  带宽: 多颗 TSP 间的连接
  延迟: 编译器已知的固定延迟 (无拥塞)
  拓扑: DRAGONFLY / ROTATIONAL
```

### 1.2 编译器对内存的管理范围

Groq 编译器管理的不仅仅是 "地址分配"：

```
┌─────────────────────────────────────────┐
│ 编译器内存管理范围                          │
│                                          │
│  1. 地址分配 (Address Assignment)         │
│     - 每个张量的 SRAM 基础址               │
│     - Liveness 分析回收中间结果的内存        │
│                                          │
│  2. 布局变换 (Layout Transformation)      │
│     - NHWC ↔ NCHW ↔ Groq 自定义布局        │
│     - 插入显式的 layout transpose 操作     │
│                                          │
│  3. Stream 分配 (Stream Allocation)       │
│     - 64 个 logical stream 的分配          │
│     - 方向选择 (East vs West)             │
│     - 生命周期管理 (alloc → free)          │
│                                          │
│  4. Bank 冲突避免 (Bank Conflict Avoidance)│
│     - 访问模式分析                         │
│     - 数据填充和排列调整                    │
│     - 时间维度的访问交错                    │
│                                          │
│  5. Tiling (分块)                         │
│     - 大张量分块适配 SRAM 容量              │
│     - Tile 调度顺序优化                     │
│     - 双缓冲策略                           │
└─────────────────────────────────────────┘
```

---

## 2. Stream 寄存器分配

### 2.1 分配问题的形式化

Stream 分配可以建模为**图着色寄存器分配**的变体：

```
输入:
  - 张量的 liveness 区间: 每个中间张量从 producer 发射到 consumer 消费的时间区间
  - 64 个可用的 stream 寄存器 (每个通道)

问题:
  - 将张量分配到 stream 寄存器
  - 满足: liveness 重叠的张量不能分配到同一个 stream
  - 目标: 最小化 spill (spill 到 SRAM 导致额外延迟)

约束:
  - Producer (例如 MXM) 的产出 stream 必须在消费者 (例如 VXM) 之前保持活跃
  - Stream 的方向固定 (MXM 产出是 East 还是 West 取决于布局位置)
  - 跨芯片 stream 需要占用两个芯片的资源
```

### 2.2 分配算法

```haskell
-- Stream 分配算法 (概念性)
allocateStreams :: Graph -> [LiveInterval] -> Allocation
allocateStreams graph intervals = 
    case graphColoring intervals 64 of  -- 64 种颜色 (stream 寄存器)
        Right allocation -> allocation
        Left  conflict   -> insertSpill (head conflict) >> allocateStreams graph intervals'

-- 当 stream 不够用时的 spill 策略
insertSpill :: LiveInterval -> Graph
insertSpill interval = 
    -- 在 producer 后插入 MEM store
    -- 在 consumer 前插入 MEM load
    -- 释放中间的 stream 寄存器
    graph `withOpBefore` consumer (MEMStore interval)
          `withOpAfter`  producer (MEMLoad  interval)
```

### 2.3 East vs West 方向选择

```haskell
-- 方向选择启发式
chooseDirection :: TileLayout -> Operation -> Direction
chooseDirection layout op
    | producerRow layout op < consumerRow layout op = East
    | otherwise = West

-- 方向冲突解决
resolveDirectionConflict :: Operation -> Operation -> (Direction, Direction)
resolveDirectionConflict opA opB
    | bothEast opA opB && streamExhausted East = 
        (East, East)  -- 其中一个走 SRAM 迂回
    | otherwise =
        (directionA, directionB)  -- 支持
```

---

## 3. SRAM Bank 冲突避免

### 3.1 Bank 结构

TSP 的 SRAM 被组织为多 bank（通常为 32 或 64 bank），每个 bank 是独立读写端口：

```
Bank 0:  [addr 0, addr 32, addr 64, ...]
Bank 1:  [addr 1, addr 33, addr 65, ...]
...
Bank 31: [addr 31, addr 63, addr 95, ...]

冲突条件:
  同一 cycle 访问同一 bank 的不同地址 ⇒ 串行化
  同一 cycle 访问同一 bank 的相同地址 ⇒ 正常 (broadcast)

编译器策略:
  1. 避免同一 cycle 两个 stream 访问同 bank
  2. 如果必须访问, 确保访问的是同一地址
  3. 或者通过 padding 将冲突地址分散到不同 bank
```

### 3.2 Bank 冲突检测

```haskell
data BankConflict = BankConflict
    { cycle    :: Cycle
    , bankID   :: Bank
    , stream1  :: StreamID
    , stream2  :: StreamID
    , addr1    :: Address
    , addr2    :: Address
    }

detectBankConflicts :: Schedule -> [BankConflict]
detectBankConflicts schedule = 
    [ conflict 
    | cycle <- cycles schedule
    , access1 <- memAccessesAt schedule cycle
    , access2 <- memAccessesAt schedule cycle
    , access1 /= access2
    , bankOf access1 == bankOf access2
    , addrOf access1 /= addrOf access2
    ]
```

### 3.3 缓解策略

```
策略 1: Padding
  在张量维度上添加 padding, 改变 bank 映射
  例: [64] → [68] (padding 4), 使得原本冲突的 stride 不再冲突

策略 2: 访问交错
  将同一 bank 的访问在时间上错开 1-2 cycles
  代价: 总延迟增加

策略 3: 数据重排
  改变张量在 SRAM 中的存储顺序
  例: 转置存储, 使后续主循环中流式访问不冲突
```

---

## 4. Tiling 策略

### 4.1 Matrix Multiplication Tiling

矩阵乘法是 ML 中最核心的运算。TSP 的 MXM slice 硬连线的 systolic array 是 320×320。编译器需要将任意形状的矩阵乘法分块：

```
矩阵乘法: C[M,N] = A[M,K] @ B[K,N]

Tiling 层次:
  Level 0: [M, N, K] ← 原始维度
  Level 1: [M/Tm, N/Tn, Tm, Tn, K]  ← 外分块 (适配 SRAM 容量)
  Level 2: [M/Tm, N/Tn, Tm/320, Tn/320, 320, 320, K/Tk, Tk]  ← MXM 分块
  Level 3: [..., 320, 320, K/320, 320]  ← Systolic 阵列利用

编译器选择 Tiling 参数:
  Tm: 由 SRAM 容量决定 (可以存多少行 A 的 tile)
  Tn: 由 SRAM 容量决定 (可以存多少列 B 的 tile)
  Tk: 由 MXM 的吞吐决定 (减少 A/B 的 reload)
  Tile 调度顺序: 最优的是 loop interchange 后的排序
```

### 4.2 双缓冲 (Double Buffering)

```
朴素执行 (无双缓冲):
  LD W[0] → MXM → ST R[0]
  LD W[1] → MXM → ST R[1]
  LD W[2] → MXM → ST R[2]
  ...
  总时间 = TILE_COUNT × (LD + MXM + ST)

双缓冲执行:
  LD W[0]               → stream 1
  LD W[1]               → stream 2  (在第一个 MXM 期间预加载)
  MXM W[0] (并 LD W[2])
  MXM W[1] (并 LD W[3])
  ...
  总时间 ≈ LD + TILE_COUNT × max(LD, MXM, ST)

编译器负责:
  1. 分配两个 buffer (ping & pong)
  2. 调度 LD → MXM → ST 重叠
  3. 确保 stream 方向正确
```

### 4.3 卷积 Tiling

卷积的 Tiling 更加复杂，因为需要处理空间维度的滑动窗口：

```
卷积: O[N, Cout, Hout, Wout] = I[N, Cin, H, W] ★ K[Cout, Cin, Kh, Kw]

Tiling 策略:
  1. Im2Col + GEMM: 
     将卷积展开为矩阵乘法 (内存占用大)
  2. Winograd 变换:
     对小卷积核 (3×3) 减少乘法次数
  3. 直接卷积 Tiling:
     按输出通道和空间位置分块

编译器选择:
  取决于卷积参数和硬件资源 (SRAM 容量)
```

---

## 5. 实际案例: Multi-Head Attention 的编译器优化

Transformer 的 MHA 是展现编译器能力的理想案例：

```
原始计算:
  Q = input @ W_Q      [B, S, D] @ [D, D] = [B, S, D]
  K = input @ W_K      [B, S, D] @ [D, D] = [B, S, D]
  V = input @ W_V      [B, S, D] @ [D, D] = [B, S, D]
  S = Q @ K^T          [B, H, S, Dh] @ [B, H, Dh, S] = [B, H, S, S]
  A = softmax(S)       [B, H, S, S]
  O = A @ V            [B, H, S, S] @ [B, H, S, Dh] = [B, H, S, Dh]
  output = O @ W_O     [B, S, D] @ [D, D] = [B, S, D]

编译器优化:
  1. 融合 Q, K, V 的投影 (三个 MXM 合并为一个批次)
  2. S = Q @ K^T 的 tiling (按 head 维度)
  3. softmax 在 VXM 上流水化 (与 MXM 的 S 计算重叠)
  4. O = A @ V 的 tiling 与 stream 复用
  
  最终: 所有中间张量通过 stream 传递，无需写回 SRAM
```

---

## 6. 关键洞察 / Key Insights

1. **无缓存 = 更强大但更严格**: 没有硬件的缓存一致性、TLB 或 bank 冲突解决逻辑，编译器必须完全替代这些传统硬件功能。这不仅需要代码生成，更需要整个编译器工具链的分析能力。

2. **Stream 是 Groq 的内存抽象精髓**: 与 GPU 的 shared memory 或 CPU 的 cache line 不同，Groq 的 stream 是**时序化的** — 一个 stream 不仅携带数据值，还携带精确的时序信息。这使得 producer 可以 "知道" consumer 何时需要数据，从而实现提前推送。

3. **Tiling 策略决定性能**: 在 GPU 上，不完美的 tiling 可以通过缓存弥补；在 Groq 上，不良的 tiling 直接导致 SRAM 溢出或访问冲突。Tiling 策略是编译器优化中影响性能最大的因素之一。

4. **布局转换是关键开销**: TSP 没有通用内存布局硬件支持。任何布局不匹配（例如 NHWC 输入、NCHW 权重）都需要显式的 SXM 操作来转换。编译器需要最小化布局转换的总数量。

---

**Phase 3 完成。下一个阶段: Phase 4 — 最终结果汇总**
