# Layer 2 Deep Dive: Haskell 类型系统与 Haste DSL
## Haskell Type System & Haste DSL Design

**Created:** 20260519-1040  
**Analyst:** Groq Compiler Architecture Expert  
**Layer:** 2 (Deep Technical Analysis)

---

## 1. Haskell 类型系统在编译器中的角色

### 1.1 类型驱动的编译器设计

Groq 编译器后端用 Haskell 实现不是历史偶然 — Haskell 的类型系统被**主动用作编译期正确性保证工具**。具体来说：

| 类型特性 | 在编译器中的应用 |
|----------|-----------------|
| GADTs (Generalized Algebraic Data Types) | 编码 IR 节点类型约束，确保只能在正确类型的操作上应用变换 |
| Type Families | 不同 dialect 间类型的多态转换 |
| Phantom Types | 标记 stream/queue 的硬件资源 ID |
| Monad Transformers | 组合调度器的多个效应 (状态、错误处理、日志) |
| Linear Types (via `linear-base`) | 保证 stream 资源不会被重复使用/忘记释放 |
| Dependent Types (via singletons) | 周期计数、队列深度等硬件参数的类型级表示 |

### 1.2 GADT 编码的例子

```haskell
{-# LANGUAGE GADTs, DataKinds, KindSignatures #-}

-- 硬件资源类型
data SliceType = MXM | VXM | MEM | SXM | ICU
data QueueID = Q1 | Q2 | ... | Q144  -- 144 个队列

-- TSP 指令的类型安全表示
data TSPInst (s :: SliceType) where
    MXMMatMul  :: Matrix a -> Matrix b -> TSPInst MXM
    VXMReLU    :: Vector a -> TSPInst VXM
    MEMStore   :: Address -> TSPInst MEM
    MEMLoad    :: Address -> TSPInst MEM
    SXMPermute :: Permutation -> TSPInst SXM
    SYNC       :: TSPInst ICU
    NOTIFY     :: TSPInst ICU

-- 安全调度: 只能将 MXM 指令分配到 MXM 队列
schedule :: TSPInst s -> QueueID s -> ScheduledInst
schedule (MXMMatMul a b) = \case
    MXMQueue qid -> ScheduledMXM qid (MXMMatMul a b)
    _            -> error "Type mismatch!"  -- 编译期捕获!
```

### 1.3 Monad 堆栈用于调度器

```haskell
-- 调度器 monad 堆栈 (推测)
newtype Scheduler a = Scheduler
    { runScheduler :: State SchedulingState
                   -> Except SchedulingError
                   -> Writer [LogEntry]
                   -> IO a  -- 或者纯计算
    }

-- 调度状态
data SchedulingState = SchedulingState
    { queuePrograms :: Map QueueID [ScheduledInst]
      -- ^ 每个队列的指令序列
    , streamAlloc   :: Map StreamID (Maybe Value)
      -- ^ stream 寄存器分配状态
    , cycleCounter  :: Int
      -- ^ 当前调度周期
    , pendingSyncs  :: Set QueueID
      -- ^ 等待同步的队列
    , chipConfig    :: ChipConfig
      -- ^ 芯片配置 (单芯片/多芯片)
    }

-- 调度错误
data SchedulingError
    = ResourceConflict StreamID Cycle
    | QueueOverflow QueueID
    | UnsatisfiableDependency InstID InstID
    | SyncDeadlock [QueueID]
```

---

## 2. Haste DSL 设计

### 2.1 Haste 定位

Haste 是 Groq 的 **TSP 硬件编程 DSL**，嵌入在 Haskell 中。它继承自 **Lava**（Xilinx 的 Haskell 硬件描述库），提供：

- 高层组合子来描述线性代数运算
- 类型安全的硬件结构表达
- 到 TSP ISA 的精确映射

### 2.2 Haste 的核心抽象

```haskell
-- Stream 类型: 表示 TSP 上流动的数据
data Stream a = Stream
    { streamId   :: StreamID
    , direction  :: Direction  -- East | West
    , channel    :: Channel
    , lanes      :: Range
    , timing     :: Timing
    }

-- 功能 Slice 句柄
data MXMSlice = MXMSlice
    { sliceRow    :: TileRow
    , config      :: MXMConfig
    }
data VXMSlice = VXMSlice
    { sliceRow    :: TileRow
    , config      :: VXMConfig
    }

-- 线性代数组合子
class LinearAlgebra a where
    matmul  :: MXMSlice -> Stream (Matrix a) -> Stream (Matrix a) -> Stream (Matrix a)
    add     :: VXMSlice -> Stream (Vector a) -> Stream (Vector a) -> Stream (Vector a)
    relu    :: VXMSlice -> Stream (Vector a) -> Stream (Vector a)
    reduce  :: VXMSlice -> Stream (Vector a) -> Stream (Scalar a)
```

### 2.3 Lava 影响的体现

从 Xilinx Lava 继承的设计模式：

```haskell
-- Lava 风格: 用高阶函数描述电路结构
-- Haste 可能类似:

-- Lava 示例 (Xilinx)
adder :: Bit -> Bit -> (Bit, Bit)
adder a b = (sum, carry)
  where sum   = xor a b
        carry = and a b

-- Haste 推测示例 (Groq TSP)
attention :: MXMSlice -> VXMSlice -> MEMSlice -> Stream (Matrix F16) -> Stream (Matrix F16) -> Stream (Matrix F16)
attention mxm vxm mem Q K = do
    -- Q @ K^T
    scores <- matmul mxm Q (transpose K)
    -- softmax 在 VXM 上
    probs  <- softmax vxm scores
    -- probs @ V
    output <- matmul mxm probs V
    return output
```

### 2.4 Haste 的编译目标

Haste 代码编译后生成的是**循环展开的、确定性的指令序列**，没有动态控制流：

```haskell
-- Haste 中的循环展开
-- 对 TSP 来说，所有循环必须在编译时完全展开

-- 概念性展开示例:
pipelineLoop :: MXMSlice -> MEMSlice -> Int -> Stream (Matrix F16) -> Haskell ()
pipelineLoop mxm mem n input = 
    sequence_ [stage i | i <- [0..n-1]]  -- 完全展开

  where
    stage i = do
        -- 所有 tile 和 timing 在编译时确定
        w <- memLoad mem (weightAddr i)
        r <- matmul mxm input w
        memStore mem (resultAddr i) r
```

---

## 3. 形式化验证 / Formal Verification Pipeline

### 3.1 Timed Trace 验证

Haskell 后端可以输出 **timed trace** — 每条指令的精确执行轨迹：

```
Program timed trace:
  Cycle    0: MEM[0] load weight_tile_0 → stream 3
  Cycle    1: MEM[1] load weight_tile_1 → stream 4
  Cycle    5: MXM[2] matmul (stream 3, stream 1) → stream 7
  Cycle    7: MXM[2] matmul (stream 4, stream 1) → stream 8
  Cycle   42: VXM[3] relu stream 7 → stream 12
  ...
  Cycle 1234: SYNC all queues
```

这个 timed trace 可以：
1. 被 **模型检查器** 验证是否为 deadlock-free
2. 被 **时序逻辑** 验证是否符合时序约束
3. 被 **等价性检查器** 验证是否在数学上等价于原始模型

### 3.2 类型级证明

Haskell 类型系统可以证明的调度性质：

```haskell
-- 类型级证明: 无死锁调度
data SafeSchedule (queues :: [QueueID]) where
    SafeNil  :: SafeSchedule '[]
    SafeCons :: (QueueNonBlocking q, AllQueuesSync queues) 
             => ScheduledInst q -> SafeSchedule queues -> SafeSchedule (q ': queues)

-- Stream 资源无冲突
data SafeStreamAlloc (streams :: [StreamID]) where
    SafeAlloc :: (NoDoubleAlloc streams, NoUseAfterFree streams) => SafeStreamAlloc streams
```

---

## 4. 关键洞察 / Key Insights

1. **类型安全 = 调度正确性**: Groq 用 Haskell 类型系统来保证调度器不会犯错。一个类型正确的调度器生成 a) 无死锁、b) 无资源冲突、c) 时序正确的指令序列。

2. **Haste 与 MLIR 的关系**: Haste 不是 MLIR 的替代品，而是互补的。MLIR 处理"做什么"，Haste 处理"怎么做"——如何用 TSP 硬件实现。

3. **Lava 传承的价值**: Xilinx Lava DSL 经过 20 年的验证，证明了 Haskell EDSL 用于硬件设计的可行性。Groq 在此之上增加了线性代数和 ML 工作负载的原生支持。

4. **形式化验证的实用性**: 当你的编译器必须精确到 cycle 级别、硬件没有容错机制时，形式化验证不是学术玩具，而是生产必要的工具。

---

**Next**: [Layer 2: 调度器算法 — List Scheduling, Modulo Scheduling, ILP](./layer2-scheduling-algorithm.md)
