# Round 1: Groq TSP vs NVIDIA GPU Architecture Comparison

> 搜索时间: 2026-05-18
> 范围: 微架构、执行模型、数据流、关键架构差异

## 1. Groq TSP Microarchitecture

### 1.1 Design Philosophy
The Groq Tensor Streaming Processor (TSP) is built around **deterministic execution** — eliminating all "reactive hardware" (no caches, no branch predictors, no out-of-order execution, no dynamic arbitration, no cache coherence). The **compiler** statically schedules every instruction, data movement, and timing cycle at compile time. This is **"software-defined hardware."**

### 1.2 Functional Slices (Columnar Organization)

| Slice | Full Name | Count/Lane | Function |
|-------|-----------|:----------:|----------|
| **ICU** | Instruction Control Unit | Shared | Fetches, decodes, dispatches instructions vertically to all slices. <3% chip area. |
| **MEM** | Memory Slice | x2 | On-chip SRAM scratchpad, 88 independent banks, **220 MB** total, **80 TB/s** bandwidth |
| **VXM** | Vector Execution Module | x1 | Vector arithmetic: add, multiply, compare, activation (GELU, ReLU) |
| **MXM** | Matrix Execution Module | x2 | Matrix multiply & convolution (GEMM) — **409,600 MAC units** total |
| **SXM** | Switch Execution Module | x2 | Data movement: shift, rotate, permute, broadcast. Also Chip-to-Chip (C2C) I/O. |

### 1.3 Data Flow: 2D Orthogonal Architecture
- **Instructions flow vertically (Y-axis, North-to-South)** from ICU through all slice columns
- **Data flows horizontally (X-axis, East-to-West)** as streams across functional slices
- **Computation occurs at intersection** — instruction and data arriving at same unit in same cycle
- 20 Super Lanes × 16 lanes = **320 parallel lanes**; data bus width per Super Lane: **512 bytes**

### 1.4 Deterministic Execution Model
**What is eliminated:**
- No caches (all SRAM with fixed latency)
- No dynamic arbitration (compile-time routing)
- No out-of-order execution
- No branch prediction (compute both branches, select via mask)
- No speculative execution
- No cache coherence protocols
- No DRAM (SRAM only)

**Compiler controls 144 independent instruction queues**, each capable of issuing 1+ instructions/cycle.

### 1.5 Why No Cache Coherence?
No caches exist → nothing to keep coherent. All data in 220 MB global shared SRAM with fixed access latencies. Compiler statically allocates addresses and schedules all memory accesses.

---

## 2. NVIDIA GPU SM Architecture

### 2.1 Streaming Multiprocessor (SM) Structure
Each SM contains: CUDA Cores, Tensor Cores, Warp Schedulers, Register File (64K-256K 32-bit regs), Shared Memory / L1 Cache, Load/Store Units, SFUs.

### 2.2 SIMT Model (Single Instruction, Multiple Threads)
- **Thread**: Smallest unit, each has own PC (post-Volta), register state, stack
- **Warp**: Group of **32 threads** executing same instruction — fundamental scheduling unit
- **Thread Block**: Group of warps sharing data via shared memory
- **Grid**: Collection of thread blocks = entire kernel launch

### 2.3 CUDA Cores vs Tensor Cores

| Aspect | CUDA Cores | Tensor Cores |
|--------|-----------|--------------|
| Purpose | General scalar compute | Matrix multiply-accumulate |
| Since | G80 (2006) | Volta (2017) |
| Operation | One scalar thread/core | Matrix tiles (4x4, 8x8, 16x16) |
| H100 count | 16,896 | 528 |
| FLOPs contribution | ~66 TFLOPS | ~2,000 TFLOPS (FP8) |

### 2.4 Memory Hierarchy

| Level | GPU | Latency | TSP Equivalent |
|-------|-----|---------|----------------|
| L1/Shared | 128-256 KB/SM | ~20-30 cyc | N/A |
| L2 Cache | 40-96 MB | ~200-400 cyc | N/A |
| HBM | 80-192 GB, 2-8 TB/s | ~400-800 cyc | N/A |
| On-chip SRAM | N/A | N/A | 220 MB, 80 TB/s |

### 2.5 Warp Divergence
- Single PC per warp (pre-Volta): divergent branches serialize execution paths
- Independent thread scheduling (Volta+): each thread has own PC, tracks sub-warp divergence

---

## 3. Key Architectural Differences

### 3.1 Matrix Compute: MXM vs Tensor Core

| Aspect | Groq MXM | NVIDIA Tensor Core |
|--------|----------|-------------------|
| Organization | 320-wide SIMD, weights pre-loaded | 4x4 to 16x16 MAC tile arrays in each SM |
| Data movement | Streaming, no register file | Classic systolic, results to registers |
| Scheduling | Compiler, exact cycle | Hardware warp scheduler dispatches MMA |
| Batch=1 | Excellent (streaming keeps all MACs fed) | Poor (tensor cores underutilized) |

### 3.2 Dataflow vs Cache-Based Memory

| Aspect | Groq TSP | NVIDIA GPU |
|--------|----------|------------|
| Primary memory | 220 MB on-chip SRAM | 80-192 GB off-chip HBM3 |
| Bandwidth | ~80 TB/s (on-chip) | ~3-8 TB/s (HBM) |
| Latency | Fixed, few cycles | Variable, hundreds of cycles |
| Management | Compiler static allocation | HW caches + SW shared memory |
| Energy/access | Lower | Higher |

### 3.3 Deterministic vs Dynamic Scheduling

| Aspect | Groq TSP | NVIDIA GPU |
|--------|----------|------------|
| Scheduling | Compile-time, cycle-accurate | Runtime, by HW warp schedulers |
| Worst-case execution | Known before execution | Data-dependent variance |
| Latency jitter | <1 microsecond | Orders of magnitude possible |
| Compiler complexity | Extremely high | Lower |
| HW complexity | Low | High |
| Batch=1 efficiency | Excellent | Poor |
| Large batch throughput | Limited by SRAM | Excellent |

### 3.4 Summary: When Each Wins

| Workload Type | Better Choice |
|--------------|:-------------:|
| Single-batch inference (latency-critical) | **Groq TSP** |
| Low-latency LLM serving (real-time) | **Groq TSP** |
| Large-batch training | **NVIDIA GPU** |
| Large model inference (70B+) | **NVIDIA GPU** |
| Dynamic workloads (MoE, speculation) | **NVIDIA GPU** |
| Energy per token (inference) | **Groq TSP** (~10x better) |

Sources: Zellic Research, ISCA 2020/2022, NVIDIA CUDA Programming Guide, NVIDIA Hopper/Blackwell Architecture, EET China, 36Kr, Zhihu.
