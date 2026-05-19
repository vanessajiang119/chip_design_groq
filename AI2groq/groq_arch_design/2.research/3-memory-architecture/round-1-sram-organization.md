# Round 1: Groq TSP SRAM Tile 组织与架构概览

> **时间**: 20260519-1600
> **重点**: MEM slice 物理组织、SRAM 容量分布、功能切片架构

---

## 1. 功能切片架构 (Functional Sliced Microarchitecture)

Groq TSP 采用颠覆性的 **功能切片** 设计，而非传统多核架构。芯片被组织为垂直列（slice），每列只实现**单一功能**：

```
               North (指令流向上)
    ┌──────┬──────┬──────┬──────┬──────┐
    │      │      │      │      │      │  Tile 19
    ├──────┼──────┼──────┼──────┼──────┤
    │      │      │      │      │      │  ...
    ├──────┼──────┼──────┼──────┼──────┤
    │      │      │      │      │      │  Tile 1
    ├──────┼──────┼──────┼──────┼──────┤
    │      │      │      │      │      │  Tile 0
    ├──────┼──────┼──────┼──────┼──────┤
    │  MXM │ SXM  │ MEM  │ VXM  │ MEM  │  <- 每 superlane 水平布局
    └──────┴──────┴──────┴──────┴──────┘
                    ICU (指令控制单元)       <- 芯片底部
```

### 各功能切片

| 切片 | 全称 | 功能 | 数量/芯片 |
|------|------|------|-----------|
| **MEM** | Memory | SRAM 读写操作（不支持算术） | 每个 superlane 2 个 |
| **MXM** | Matrix Multiply | 矩阵乘加 (systolic array) | 每个 superlane 2 个 |
| **VXM** | Vector Execution | 向量算术 (加、乘等) | 每个 superlane 1 个 |
| **SXM** | Switch Execution | 移位、旋转、数据路由、片间网络交换 | 每个 superlane 2 个 |
| **ICU** | Instruction Control | 指令获取与分发（芯片底部水平条） | 1 个 |

---

## 2. MEM Slice 的物理组织

### 2.1 层次结构

```
TSP 芯片
 └── 20 个 Superlane (Tile 0-19)
      └── 每个 Superlane:
           ├── MEM 单元 (左): 5.5 MB SRAM
           ├── MEM 单元 (右): 5.5 MB SRAM
           ├── MXM 单元 × 2
           ├── VXM 单元 × 1
           └── SXM 单元 × 2
           └── 16 个 Lane (SIMD 通道)
```

### 2.2 SRAM 容量分解

| 层级 | 容量 | 计算方式 |
|------|------|----------|
| 每个 MEM 单元 | **5.5 MB** | 1 个 SRAM bank 组 |
| 每个 Superlane | **11 MB** | 2 × 5.5 MB (左+右 MEM) |
| 全芯片总计 | **220 MB** | 20 × 11 MB |
| 含小缓冲的标称值 | **~230 MB** | 含其他内部 buffer |

### 2.3 SIMD 通道组织

```
20 Superlanes × 16 Lanes = 320 SIMD 通道

每个 Lane 数据宽度: 32 bytes (256 bits)
每个 Superlane 总宽度: 16 × 32 B = 512 bytes/cycle
芯片总数据宽度: 20 × 512 B = 10,240 bytes/cycle
```

---

## 3. 架构详细规格 (Hot Chips 2020 / ISCA 2020)

| 参数 | 值 |
|------|-----|
| **工艺** | 14nm ASIC |
| **Die 面积** | 25 × 29 mm (725 mm²) |
| **时钟频率** | 900 MHz |
| **SRAM 容量** | 220 MB (标称 230 MB) |
| **片上 SRAM 带宽** | ~80 TB/s |
| **片外带宽** | 512 GB/s (16 路自定义 C2C 链路) |
| **SIMD 通道** | 320 (20 tiles × 16 lanes) |
| **独立指令队列** | 144 |
| **每通道逻辑流** | 64 (32 东向 + 32 西向) |
| **INT8 性能** | ~750-1000 TOPS |
| **FP16 性能** | 188 TFLOPS |
| **每 superlane MEM 数量** | 2 |
| **每 MEM 单元 SRAM** | 5.5 MB |

---

## 4. 关键设计理念 — 确定性计算

### 4.1 移除了哪些硬件？
- **无 cache** — 无 L1/L2/L3，无 cache coherence
- **无 DRAM 控制器** — 无 Refresh 逻辑，无页调度
- **无分支预测** — 无需 speculative execution
- **无乱序执行** — 无 reorder buffer
- **无仲裁器** — 所有访问在编译时静态调度

### 4.2 确定性带来的好处

| 方面 | Groq TSP | 传统 GPU |
|------|----------|----------|
| **内存延迟** | 固定 ~2-5 ns (SRAM) | 可变 375-500 ns (HBM) |
| **执行时间** | 编译时已知，与输入无关 | 运行时可变 |
| **尾部延迟** | 零方差 | 高方差 (cache miss, TLB miss) |
| **SLA 保证** | 可预测到 cycle 级 | 概率性保证 |
| **计算利用率** | ~100% | 推理时 ~30-40% |

### 4.3 编译器的作用

> "编译器跟踪芯片上每个 stream 的位置和使用时间 — 这被称为 '软件定义的硬件'。"

- 编译器在编译时调度**所有**指令和数据搬移
- 知道每条指令的确切延迟
- 跨 144 个指令队列调度数据流
- 控制 64 个逻辑流 / channel 的时序

---

## 5. SRAM 带宽初步分析

| 路径 | 宽度 | 频率 | 理论带宽 |
|------|------|------|----------|
| 每 superlane 数据路径 | 512 B | 900 MHz | 460 GB/s |
| 全芯片 20 superlanes 数据路径 | 10,240 B | 900 MHz | **9.2 TB/s** |
| MEM 内部 bank 并行 × 读+写 | 4-8× 并行因子 | — | **~80 TB/s** |

> 详细带宽计算见 Round 2。

---

## 6. 核心参考文献

1. Abts, D. et al., *"Think Fast: A Tensor Streaming Processor (TSP) for Accelerating Deep Learning Workloads"*, ISCA 2020.
2. Abts, D. et al., *"A Software-defined Tensor Streaming Multiprocessor for Large-scale Machine Learning"*, ISCA 2022 (Award Winner).
3. Groq Hot Chips 2020 Presentation.
4. "The Groq TSP Architecture" — Nextplatform analysis, Sep 2020.
