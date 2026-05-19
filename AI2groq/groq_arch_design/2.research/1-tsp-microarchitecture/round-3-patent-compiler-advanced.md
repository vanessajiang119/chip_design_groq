# TSP 微架构深度分析 — Round 3 研究报告：专利与高级功能
# TSP Microarchitecture Deep Dive — Round 3: Patents & Advanced Features

> 创建时间: 2026-05-19T1500
> 来源: USPTO patents, ACM papers, compiler analysis

---

## 一、专利技术分析 (Patent Analysis)

### US20240037064A1: 指令格式与 ISA

**核心权利要求**:
1. **功能切片指令队列**: 每种功能切片类型拥有自己的指令队列
2. **VLIW 包结构**: 包含多个操作码，每个对应一个功能切片类型
3. **数据路径交叉开关**: Lane switching slice 可配置为 crossbar 或 permuter
4. **指令-数据解耦**: 指令流 (垂直) 与数据流 (水平) 完全解耦

### US20230024670A1: 确定性存储

**核心原理**:
1. 编译器生成**确定性内存访问模式**
2. 所有内存操作的时序在编译时已知
3. SRAM 阵列的**物理分区**与功能切片对齐
4. 无缓存一致性协议 — 确定性消除 snoop 开销

### US12222894B2: 编译器操作

**编译流程**:
1. 前端: MLIR → Tensor → Stream IR
2. 中间: 静态调度 + 资源分配
3. 后端: 指令包生成 (VLIW)

---

## 二、静态调度算法分析 (Static Scheduling)

### 编译器可见资源 (Compiler-Visible Resources)

编译器具有完整的硬件可见性:
```
320 SIMD channels
144 instruction queues
64 logical streams/channel (32E + 32W)
220 MB SRAM (fully addressable)
Exact instruction latencies
```

### 调度约束 (Scheduling Constraints)

1. **数据依赖**: 生产者-消费者流之间的相关性
2. **资源冲突**: 同一功能切片上的操作不能重叠
3. **流水线延迟**: 指令发射到结果可用的 cycle 数
4. **带宽限制**: 每 cycle 的数据路径带宽
5. **同步点**: SYNC/NOTIFY/DESKEW 协调

### 调度策略 (Scheduling Strategy)

```
算法: List Scheduling with Resource Constraints
输入: DFG (数据流图) + 硬件模型
输出: 每条指令的精确发射 cycle

步骤:
1. 构建数据流图 (DFG)
2. 拓扑排序操作节点
3. 分配操作到功能切片
4. 确定数据流路径和 timing
5. 解决资源冲突 (通过 cycle 偏移)
6. 插入同步指令
7. 生成 VLIW 包
```

---

## 三、多 TSP 分布式系统 (Multi-TSP System)

### Dragonfly 拓扑

Groq 使用 **Dragonfly** 拓扑连接多个 TSP:
- 每个 TSP 通过 SXM 切片连接
- 编译器预调度所有片间通信
- 无自适应路由 — 所有路由在编译时确定

### 同步机制

| 指令 | 功能 |
|------|------|
| SYNC | 暂停所有 144 个队列 |
| NOTIFY | 广播唤醒信号 |
| DESKEW | 等待 HAC (硬件对齐计数器) 溢出 |

DESKEW 在多 TSP 系统中特别重要 — 确保不同 TSP 上的计算对齐在同一个 cycle 边界。

---

## 四、面积与功耗分布推断 (Area & Power Distribution)

### 面积分布 (Area Distribution)

| 模块 | 面积占比 | 说明 |
|------|---------|------|
| SRAM (MEM) | ~40-50% | 220 MB + ECC |
| MXM (矩阵) | ~20-25% | 409,600 MACs |
| VXM (向量) | ~10-15% | 5,120 ALUs + 数据路径 |
| SXM (开关) | ~10% | Crossbar 网络 |
| ICU (控制) | <3% | 指令队列 + 解码 |
| 其他 (时钟/布线) | ~10-15% | |

### 时钟频率与电压 (Clock & Voltage)

- 标称频率: 900 MHz
- 最高频率: 1.25 GHz (工艺角依赖)
- 核心电压: ~0.8-0.9V (14nm 典型)
- TDP: ~300W

### 性能/功耗比

| 工作负载 | 性能 | 功耗效率 |
|---------|------|---------|
| INT8 矩阵乘 | 750-1000 TOPS | ~3 TOPS/W |
| FP16 矩阵乘 | 188-205 TFLOPS | ~0.7 TFLOPS/W |
| ResNet-50 | 20,400 imgs/s @ batch-1 | — |

---

## 五、与传统架构的对比 (Comparison with Traditional Architectures)

### vs GPU (NVIDIA H100)

| 特性 | Groq TSP | NVIDIA H100 |
|------|---------|-------------|
| 制程 | 14nm | 4nm |
| 片上存储 | 230 MB SRAM | ~50 MB cache + 80 GB HBM |
| 带宽 | 80 TB/s (片上) | ~3 TB/s (HBM) |
| 延迟控制 | 确定性 (cycle 级) | 统计性 |
| 调度 | 编译器静态 | 硬件动态 (+ 编译器) |
| 控制逻辑占比 | <3% | ~15-20% |
| 编程模型 | 流式 (Stream) | SIMT (线程) |
| 利用率 | 可预测/高 | 动态/变化 |

### vs TPU (Google TPUv4)

| 特性 | Groq TSP | Google TPUv4 |
|------|---------|--------------|
| Systolic | 320×320 × 4 planes | 128×128 |
| 数据流 | Weight-stationary | Systolic |
| SRAM | 230 MB (全局) | ~32 MB (HBM2) |
| 互联 | Dragonfly | 3D Torus |
| 确定性 | 完全 | 有限 |

---

## 六、关键设计决策分析 (Key Design Decisions)

### Why SRAM instead of DRAM/HBM?

1. **确定性延迟**: DRAM 具有可变延迟 (refresh, row activate/precharge)
2. **延迟低**: SRAM ~1-2ns vs DRAM ~50-100ns
3. **带宽高**: 80 TB/s vs HBM3 ~3 TB/s
4. **功耗效率**: SRAM 每 bit 访问功耗远低于 DRAM + PHY
5. **代价**: 容量小 (220MB vs 80GB), 密度低, 成本高

### Why Functional Slicing?

1. **控制逻辑共享**: ICU <3% vs 传统每个核心 15-25%
2. **指令广播**: 同功能 tiles 执行相同指令 → 解码一次
3. **确定性数据流**: 无交叉核心竞争
4. **扩展性**: 增加 tile 数即可纵向扩展

### Why Static Scheduling?

1. **无运行时开销**: 无分支预测/重排序
2. **可预测延迟**: 关键推理场景
3. **高利用率**: 编译器可全局优化
4. **简化硬件**: 减少硅面积和功耗

---

## 参考文献 (References)

1. USPTO 12277444 — "Software-defined Tensor Streaming Multiprocessor"
2. US20240037064A1 — "Instruction Format and ISA for TSP"  
3. US20230024670A1 — "Deterministic Memory for TSP"
4. D. Abts, Stanford EE380 Seminar — "Dataflow for Convergence of AI and HPC"
5. Groq Blog — "Inside the LPU: Deconstructing Groq's Speed"
6. Zellic Research — "How Is Groq So Fast?"
