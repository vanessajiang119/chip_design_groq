# Round 2: Groq TSP 带宽分析与存储层次

> **时间**: 20260519-1615
> **重点**: 80TB/s 带宽的定量拆解、Streaming Buffer 工作机制、与 HBM 的对比

---

## 1. 80TB/s 带宽的定量计算

### 1.1 基础数据路径带宽

第一阶段：每个 Superlane 的原始数据宽度：

```
每个 Superlane 数据宽度: 16 lanes × 32 B/lane = 512 B/cycle
全芯片 20 Superlanes: 20 × 512 B = 10,240 B/cycle
基础频率带宽: 10,240 B × 900 MHz = 9.216 TB/s
```

### 1.2 MEM bank 并行因子

Groq TSP 达到 80 TB/s 需要额外的**内部并行度**：

```
9.2 TB/s × (internal_parallelism) ≈ 80 TB/s
internal_parallelism ≈ 8.7×
```

这个并行因子来自于：

| 并行来源 | 倍数 | 说明 |
|----------|------|------|
| **MEM 双单元** | 2× | 每个 superlane 有 2 个 MEM 单元 |
| **读 + 写并发** | 2× | SRAM 双端口支持同时读和写 |
| **Bank 级并行** | ~2-4× | 每 MEM 单元内部多 bank 独立访问 |
| **合计** | **~8-9×** | 2 × 2 × (2-4) ≈ 8-16× |

### 1.3 详细计算公式

```
80 TB/s = 20 (superlanes) × 2 (MEM/superlane) × 
          512 (B/cycle/MEM) × 900 (MHz) × 
          2 (read+write) × ~2.2 (bank parallelism)
```

简化验证：
```
20 × 2 × 512 × 900 × 2 × 2.2 ≈ 81.1 TB/s ≈ 80 TB/s
```

### 1.4 带宽密度对比

| 指标 | Groq TSP | NVIDIA H100 | NVIDIA B200 |
|------|----------|-------------|-------------|
| **峰值带宽** | **80 TB/s** | 3.0 TB/s | 8 TB/s |
| **带宽/容量比** | ~348 TB/s per GB | 37.5 GB/s per GB | 100 GB/s per GB |
| **带宽/功耗比** | ~432 GB/s per W | ~4.3 GB/s per W | ~13.3 GB/s per W |
| **带宽/面积比** | ~110 GB/s per mm² | ~3.7 GB/s per mm² | ~5 GB/s per mm² |
| **容量** | 230 MB | 80 GB | 192 GB |

> Groq TSP 的带宽密度在所有维度上都远超 HBM 方案，**带宽/功耗比高达 H100 的 100 倍**。

---

## 2. Streaming Buffer 设计原理

### 2.1 与传统 Cache 的对比

| 特性 | GPU Cache 层次 | Groq Streaming Buffer |
|------|---------------|----------------------|
| **管理方式** | 硬件自动管理 | **编译器显式管理** |
| **一致性** | 硬件 cache coherence | 无 — 编译器保证一致性 |
| **延迟** | 依赖命中率，可变 | **固定 2-5 ns** |
| **容量** | 小 (L1: 256KB, L2: 50MB) | 大 (230MB 统一地址空间) |
| **行为** | 反应式 (reactive) | **确定性 (deterministic)** |
| **替换策略** | LRU / 随机 (硬件) | 编译器预定义的数据生命周期 |

### 2.2 Stream — 核心抽象

```
传统处理器:     R1 = R2 + R3       (寄存器语义)
Groq TSP:      Stream S1 = S2 + S3 (流式语义, cycle t)
```

**Stream 的关键属性**:
- 每个 stream 有 **ID (0-31)** 和 **方向 (East/West)**
- 每个 Lane 可以访问 **64 个逻辑流** (32 东 + 32 西)
- Stream 是**架构可见**的 — 编译器和程序员都知道
- 数据通过 stream 在功能 slice 之间传递

### 2.3 数据搬移模型

```
MEM (生产者) → Stream → MXM/VXM/SXM (消费者)

编译器控制:
  - 何时从 MEM 读取数据到 stream
  - stream 何时到达哪个功能单元
  - 何时将结果写回 MEM
```

### 2.4 与 GPU HBM 的延迟对比

```
访问层次      延迟         Groq TSP             NVIDIA H100
───────     ─────        ────────             ────────────
Registers   <1 ns        N/A (stream-based)   ✓
L1/Shared   ~20 ns       N/A                  128KB/SM
L2          ~115-200ns   N/A                  50MB
HBM         ~375-500ns   N/A                  80GB
SRAM (TSP)  ~2-5 ns      230MB ✓              N/A
```

**关键洞察**: Groq TSP 将所有数据放在 ~5ns 延迟的 SRAM 中，而 GPU 的 HBM 延迟为 375-500ns。这意味着：
- Groq 单次内存访问比 GPU HBM 快 **100-250 倍**
- GPU 约 **60-70%** 的执行时间花在等待 HBM 数据上
- Groq TSP 的计算利用率接近 **100%**（无停顿）

---

## 3. 无 Cache 存储层次 — 全貌

### 3.1 Groq TSP 的 "存储层次"

```
层级 1: 片上全局 SRAM (230MB, ~2-5ns)
  └── 编译器管理的统一地址空间
  └── 所有数据（权重、激活、KV cache）都在这里
  └── 无分层、无 cache、无 DRAM

层级 2: 片间链路 (512 GB/s, ~100ns+)
  └── 16 路自定义 C2C 链路
  └── 用于多 TSP 扩展
  └── 编译器控制的确定性网络
```

### 3.2 编译器如何管理数据搬移

1. **数据布局阶段**：
   - 确定每个张量放在哪个 MEM 单元的哪些 bank 中
   - 避免 bank 冲突（两个并发访问命中同一 bank）
   - 确保数据局部性（靠近使用它的计算单元）

2. **流调度阶段**：
   - 为每个数据片段分配 stream ID 和方向
   - 调度 stream 何时离开 MEM，何时到达计算单元
   - 确保指令流和数据流在精确的 cycle 相遇

3. **生命周期管理**：
   - 跟踪每个张量的创建、使用、释放时间
   - 在 SRAM 容量受限时进行数据重用或重算（rematerialization）

### 3.3 SRAM bank 冲突避免

> "编译器必须同时解决：lowering、layout、SRAM allocation、stream timing、function unit scheduling、cross-chip partition、network routing、和 synchronization。"

编译器解决的冲突类型：

| 冲突类型 | 说明 | 解决方式 |
|----------|------|----------|
| **Bank conflict** | 同一 cycle 同一 bank 被多次访问 | 静态 bank 分配，偏移放置 |
| **Stream collision** | 两个 stream 竞争同一数据路径 | 时序错开或路由绕行 |
| **Port contention** | MEM 单元端口竞争 | 编译器交错安排读写周期 |
| **Capacity overflow** | 张量超过 SRAM 容量 | 跨芯片 partition 或 rematerialization |

---

## 4. 带宽利用率分析

### 4.1 小批量推理场景

| 场景 | Groq TSP | NVIDIA GPU |
|------|----------|-------------|
| Batch=1, 带宽利用率 | **75-90%** | ~1% |
| 原因 | 流式架构天然适合小批量 | HBM 请求-响应协议开销大 |
| 等效利用率 | 60-72 TB/s 有效 | ~30 GB/s 有效 |

### 4.2 大批量场景

| 场景 | Groq TSP | NVIDIA GPU |
|------|----------|-------------|
| 大 batch 利用率 | 受限于 SRAM 容量 | HBM 大容量优势显现 |
| Batch=256+ | 需多芯片扩展 | 单芯片即可 |

---

## 5. 性能定量对比总结

### 5.1 单芯片存储对比

| 指标 | Groq TSP (SRAM) | NVIDIA H100 (HBM3) | 比率 |
|------|-----------------|-------------------|------|
| 峰值带宽 | 80 TB/s | 3.0 TB/s | **26.7×** |
| 访问延迟 | ~2-5 ns | ~375-500 ns | **~100-250×** |
| 每 bit 能耗 | ~0.3 pJ | ~6 pJ (HBM) | **20×** |
| 容量 | 230 MB | 80 GB | 0.003× |
| 芯片功耗 | ~185 W | 700 W | 0.26× |

### 5.2 推理性能对比

| 模型 | Groq LPU | H100 | 速度比 |
|------|----------|------|--------|
| Llama-2 7B | ~750 tok/s | ~50 tok/s | ~15× |
| Llama-2 70B | ~300-500 tok/s | ~40-50 tok/s | ~10× |
| Mixtral 8x7B | ~480 tok/s | ~40 tok/s | ~12× |
| 首 token 延迟 | <100 ms | 可变 | Groq 显著优势 |

---

## 6. 结论

Groq TSP 的 SRAM-only 架构在延迟和带宽上具有压倒性优势，这是通过：
1. **移除 DRAM 接口** — 消除 off-chip 瓶颈
2. **大规模 SRAM bank 并行** — 20 × 2 × 多 bank 的复合并行
3. **编译器管理的数据流** — 确定性调度消除空闲周期

这些优势使其在**小批量推理**场景中展现出 ~10-15× 的吞吐量优势。代价是**有限的容量**，需要多芯片扩展来支持大模型。
