# Round 2: Haskell 后端与静态调度算法深度分析
## Haskell Backend & Static Scheduling Algorithm — Deep Analysis

**Created:** 20260519-1010  
**Author:** Groq Compiler Architecture Expert  
**Status:** Complete

---

## 1. Haskell 后端 — 为何选择 Haskell？

### 1.1 历史背景 / Historical Context

Groq 编译器团队由 **Satnam Singh**（Groq Fellow）领导，他此前在 Xilinx 领导 Haskell 硬件设计工具（Lava DSL）的开发，在 Google 参与了 MLIR 的设计，在 Facebook 参与了 PyTorch 编译器工作。这套编译器完全反映了他的技术路线。

### 1.2 Haskell 的选择理由

| 维度 | 解释 |
|------|------|
| **类型安全** | 硬件调度不容出错 — Haskell 的类型系统在编译时捕获调度冲突 |
| **纯函数式** | 不可变数据 + 无副作用 = 确定性编译，与 TSP 的确定性哲学一致 |
| **DSL 能力** | EDSL (Embedded DSL) 模式可以用 do-notation 描述硬件流水线 |
| **Lava 传承** | Haste DSL 继承自 Xilinx Lava，是经过验证的硬件描述方法 |
| **并发建模** | 用 monad 建模 144 个指令队列的并行行为 |
| **形式化验证** | Haskell 生态支持模型检查 (model checking) 和时序逻辑验证 |

### 1.3 编译器架构

```
MLIR Frontend (Groq Dialect IR)
         │
         │  IR emitted as Haskell AST / textual format
         ▼
┌─────────────────────────────────────┐
│       Haskell Backend               │
│                                     │
│  ┌──────────┐   ┌──────────────┐   │
│  │ Scheduler │   │  Allocator   │   │
│  │ (调度器)  │   │ (资源分配器)  │   │
│  └────┬─────┘   └──────┬───────┘   │
│       │                 │           │
│       ▼                 ▼           │
│  ┌─────────────────────────────┐   │
│  │    Haste DSL / CodeGen      │   │
│  └──────────┬──────────────────┘   │
│             │                       │
│  ┌──────────▼──────────────────┐   │
│  │   Assembler (TSP machine code) │
│  └─────────────────────────────┘   │
└─────────────────────────────────────┘
         │
         ▼
   TSP Instruction Binary (IOP format)
```

---

## 2. Haste DSL — 硬件编程语言

### 2.1 Haste 的设计理念

Haste 是 Groq 的 **Haskell 嵌入式领域专用语言**（EDSL），用于直接编程 TSP。它在 ICFP 2023 的 FHPNC 分会上首次公开。

核心特性：
- **Lava-like combinators**: 用高阶函数组合硬件流水线
- **线性代数原生**: 直接表达矩阵乘法、卷积等运算
- **时序精确**: 每条 Haskell 表达式对应确定数量的 TSP 周期
- **类型级约束**: 用 Haskell 类型系统保证流水线宽度/深度匹配

### 2.2 Haste 示例结构（概念性）

```haskell
-- 概念性示例：一个简单的矩阵乘法在 Haste 中的描述
matmul :: MXMSlice -> MEMSlice -> Stream (Matrix Float) -> Stream (Matrix Float) -> Haskell ()
matmul mxm mem a b = do
    -- 从 MEM 加载矩阵 A 和 B
    a_stream <- memLoad mem a_addr
    b_stream <- memLoad mem b_addr
    
    -- 在 MXM slice 上执行矩阵乘法
    result <- mxmMultiply mxm a_stream b_stream
    
    -- 将结果存回 MEM
    memStore mem result_addr result
    
    -- 同步所有队列
    sync
```

*注: 这是概念性代码，实际 Haste API 细节未公开。*

### 2.3 Haste 与 MLIR 的关系

Haste 并非替代 MLIR 前端，而是作为**硬件代码生成的目标**：
- MLIR 前端处理框架无关的高层优化
- Haskell 后端接收 lower 后的 IR，用 Haste 描述 TSP 指令序列
- 调度器在 Haskell 中实现，直接操作 Haste AST

---

## 3. 静态调度算法 — 核心技术

### 3.1 调度问题的规模 / Scale of the Scheduling Problem

| 资源 | 数量 | 调度约束 |
|------|------|----------|
| 独立指令队列 | 144 | 每个队列有自己的 PC，编译器控制其顺序 |
| SIMD 通道 | 320 (20 tiles × 16 lanes) | 通道间数据可交换 |
| 逻辑流 (Streams) | 64/通道 (32E + 32W) | 有限的流寄存器命名空间 |
| 共享 SRAM | 220 MB | 无缓存，编译器分配所有内存 |
| 功能列 | 5 种 (ICU/MEM/VXM/MXM/SXM) | 每种操作绑定到特定列类型 |

### 3.2 调度算法核心思想

**核心原则: "Software-defined hardware" — 编译器在编译时决定一切。**

#### 3.2.1 静态 ILP 调度 (Static Instruction-Level Parallelism)

传统 CPU 在硬件中做 ILP（指令级并行）调度（Tomasulo 算法、重排序缓冲区）。Groq 将其完全移动到编译器：

```
CPU 方法:                    Groq 方法:
  乱序发射 (硬件)        ⟹     编译时分配发射周期
  寄存器重命名 (硬件)     ⟹     编译时分配流寄存器
  分支预测 (硬件)        ⟹     无分支/预测在编译时确定
  缓存一致性 (硬件)      ⟹     SRAM 静态分配
```

#### 3.2.2 List Scheduling 变体

基于对 TSP ISA 的研究可以推断，调度器核心是某种 **改进的 List Scheduling**：

```
输入: DAG of operations (来自 MLIR 前端的 Groq IR)
   
1. 拓扑排序: 按依赖关系确定操作优先级
2. 资源检查: 每个操作要占用哪个 function slice (MXM/VXM/MEM/SXM)
3. 队列分配: 分配到 144 个队列中的某个
4. 周期分配: 确定指令的精确发射周期
5. 流分配: 分配 stream 寄存器 (64/通道)
6. 冲突检测: 检测 resource hazard + data hazard
7. 回退/重试: 冲突时调整发射周期

输出: 每个队列的指令序列 + 精确周期表
```

#### 3.2.3 模调度 (Modulo Scheduling) 推测

对于 ML 推理中的循环体（如矩阵乘法 tiling、卷积 sliding window），编译器几乎必然使用 **模调度** 来流水化循环执行：

```
经典模调度概念 (Modulo Scheduling):
  Iteration 0:  [LD][MAC][ST]
  Iteration 1:       [LD][MAC][ST]
  Iteration 2:            [LD][MAC][ST]
  
  Initiation Interval (II) = 1 cycle (每个周期启动一个新 iteration)

Groq TSP 的模调度优势:
  - 无缓存，无内存冲突 ⇒ 可预测的 II
  - 144 个队列 ⇒ 更多的并行模展开空间
  - 所有数据流 timing 已知 ⇒ 精确的模调度公式
```

#### 3.2.4 ILP 求解器辅助调度

对于调度中的关键部分（如多芯片通信、资源竞争热点），编译器可能使用 **ILP (Integer Linear Programming)** 求解器找到最优解：

- **目标函数**: 最小化总执行周期数
- **约束条件**: 资源上限、依赖边、队列容量、流寄存器上限
- **求解规模**: 由于硬件确定性，约束是线性的而非动态的，ILP 高效

### 3.3 144 个队列的协同调度

这是 Groq 调度器最具挑战性的部分。不同于传统 VLIW 处理器（通常 4-8 个 issue slots），Groq 有 144 个队列：

```
每个队列 = 一个独立的功能列 × 一个 tile 行

布局:
  列类型: ICU  MEM  VXM  MXM  SXM    (5 种)
  行数:    20  (tiles)
  总计:    5 × 20 = 100 (但 MEM 更多，总计 144)

调度器需要保证:
  1. 同一指令在同一个队列连续发射
  2. 不同队列的指令间满足 data/control 依赖
  3. 所有队列按 SYNC 指令对齐
```

**同步机制**:
- `SYNC`/`NOTIFY`: 单芯片内 144 队列的对齐指令
- `HAC` (Hardware Alignment Counters): 多芯片间的时钟同步
- `DESKEW`/`RUNTIME_DESKEW`: 时钟漂移补偿

### 3.4 内存布局优化 / Memory Layout Optimization

编译器负责所有 SRAM 分配，没有硬件缓存来弥补次优布局：

```
优化目标:
  1. 减少 bank conflict
  2. 匹配 stream 访问模式
  3. 最小化内存碎片

优化手段:
  - 张量平铺 (Tensor Tiling): 将大矩阵切分为 SRAM bank 友好的小块
  - 布局转换 (Layout Transform): NHWC ↔ NCHW ↔ 自定义格式
  - 双缓冲 (Double Buffering): 计算/加载重叠
  - Liveness 分析: 精确的生命周期分析以减少内存占用
```

---

## 4. 形式化验证 / Formal Verification

Satnam Singh 在 2024 年演讲中特别提到：

> *"Applying formal verification techniques using temporal logic and model checking to verify the functionality of our chip designs."*

这反映在编译器后端：
- **类型级证明**: Haskell 类型系统保证调度不违反硬件约束
- **模型检查**: 用时序逻辑验证 144 队列间的死锁自由
- **等价性检查**: 验证调度后的代码在数学上等价于原始 IR

---

## 5. 关键洞察 / Key Insights

### 5.1 Haskell 后端的不可替代性

Groq 编译器最核心的竞争力 — 静态调度器 — 全部在 Haskell 中实现。这意味着：
- **竞争对手无法复用**（闭源 + 小众语言）
- **人才壁垒高**（Haskell + 编译器 + 硬件的大牛极其稀缺）
- **调试困难**（MLIR 前端 + Haskell 后端 = 两层 black box）

### 5.2 调度算法的计算复杂度

全静态调度 144 个队列是一个 **NP-hard** 问题。Groq 的解法:
1. 硬件确定性简化了约束（无需考虑动态行为）
2. 功能切片减少了调度维度（每个操作只能到特定列）
3. 图结构规则（ML 计算图是 DAG）使 ILP 求解可行
4. 可能使用启发式 + ILP 求解的混合方案

### 5.3 确定性哲学的一致性

从硬件设计到编译器，到 DSL 设计，再到形式化验证，"确定性"贯穿始终。这不是偶然 — 它是 Groq 相对于 GPU（CUDA 全动态调度）的根本差异化。

---

**Next**: [Round 3 — 内存布局与深度源码分析](./round-3.md)
