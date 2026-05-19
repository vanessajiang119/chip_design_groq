# Round 3: Performance Benchmarks & Ecosystem Comparison — Groq LPU vs NVIDIA/AMD GPUs

> 搜索时间: 2026-05-18

## 1. Groq LPU Published Benchmarks

### MLPerf Status
Groq has **not submitted official results** to the MLPerf Inference benchmark suite. Focus has been on LLM-specific benchmarks.

### LLM Inference Benchmarks (Tokens/sec)

| Model | Peak TPS | Source |
|---|---|---|
| Mixtral 8x7B SMoE | **480 tok/s** | Groq official / LLMPerf |
| Llama 2 7B | **750 tok/s** | Groq official |
| Llama 2 70B | **300 tok/s** | Groq official |
| Llama 3 8B (8k context) | **877 tok/s** | Artificial Analysis |
| Llama 3 70B (4k/8k context) | **284 tok/s** | Artificial Analysis |
| Llama 3.1 8B | **~870+ tok/s** | LLM Benchmarks |
| Llama 3.3 70B | **250-400 tok/s** | Artificial Analysis |

### Artificial Analysis: Llama 3.3 70B Provider Ranking

| Rank | Provider | Tokens/sec |
|---|---|---|
| #1 | **Groq** | **305.3 t/s** |
| #2 | SambaNova | 281.1 t/s |
| #3 | CompactifAI | 138.5 t/s |
| #4 | Fireworks | 125.4 t/s |
| #5 | Amazon Bedrock | 117.7 t/s |

### Time-to-First-Token (TTFT)
- Llama 2 70B: **0.22s**
- Llama 3 70B: **0.3s**
- Later optimizations achieved TTFT as low as **0.005s** for Llama 3.3 70B

### Energy Efficiency Claims

| Accelerator | Energy per Token | TDP |
|---|---|---|
| **Groq LPU** (single card) | **1-3 Joules** | 40W typical / 185W system-level |
| NVIDIA H100 | **10-30 Joules** | 700W |
| Efficiency Ratio | **~10x better per token** | |

### Groq LPU Hardware Specifications

| Specification | Value |
|---|---|
| Architecture | Tensor-Streaming Processor (TSP) |
| INT8 Performance | 750 TOPS |
| FP16 Performance | 188 TeraFLOPS |
| Local SRAM | 230 MB (per chip) |
| Memory Bandwidth | 80 TB/s |
| Vector ALUs | 5,120 |
| Matrix Multiply | 320x320 fused dot product |

### Large Model Scalability
For Llama 2 70B (INT8, ~70GB), Groq requires ~305-572 LPUs at ~106 kW total power. An 8x H100 server (10 kW) achieves similar throughput. Hardware cost for Groq is ~40x more expensive due to per-chip SRAM limitation.

---

## 2. GPU Comparable Benchmarks

### MLPerf Inference 4.1 — Llama 2 70B

**Single GPU — Offline:**

| GPU | Memory | Offline (tokens/s) | Server (tokens/s) |
|---|---|---|---|
| **NVIDIA B200** | 180 GB HBM3e | **11,264** | **10,755** |
| **NVIDIA H200** | 141 GB HBM3e | ~4,488 | — |
| **NVIDIA H100** SXM3 | 80 GB HBM3 | ~3,040 | ~2,576 |
| **AMD MI300X** | 192 GB HBM3 | **3,062** | **2,520** |

**8-GPU Systems — Llama 2 70B:**

| Configuration | Offline (tokens/s) | Server (tokens/s) |
|---|---|---|
| NVIDIA H100 (8x, 80GB) | 24,323 | 20,605 |
| AMD MI300X (8x) | 23,514 | 21,028 |
| NVIDIA H200 (8x, 141GB) | **32,124** | **29,739** |

### Architecture Comparison Table

| Spec | AMD MI300X | NVIDIA H100 | NVIDIA H200 | NVIDIA B200 |
|---|---|---|---|---|
| HBM Capacity | 192 GB | 80 GB | 141 GB | 180 GB |
| HBM Bandwidth | 5.3 TB/s | 3.35 TB/s | 4.8 TB/s | 8.0 TB/s |
| FP8 TFLOPS | 2,610 | 1,979 | 1,979 | 4,500 |
| TDP | 750W | 700W | ~700W | 1,000W |

---

## 3. Software Ecosystem Comparison

### GroqCloud Developer Ecosystem

| Metric | Detail |
|---|---|
| Registered Developers | **2M+** (as of late 2025) |
| API Model | OpenAI-compatible |
| SDKs | Python, TypeScript/JS, Hugging Face, Spring AI |
| Free Tier | Yes, rate-limited |
| Supported Models | Llama 4, GPT-OSS, Qwen3, DeepSeek R1, Whisper |

### CUDA Ecosystem (NVIDIA)

| Metric | Detail |
|---|---|
| Developer Base | ~4M+ worldwide |
| Ecosystem Age | 15+ years |
| Core Libraries | CUDA C/C++, cuDNN, TensorRT, TensorRT-LLM, NCCL |
| Framework Support | PyTorch, TensorFlow, JAX — all first-class |
| Market Share | >90% of data center GPU market |

### ROCm Ecosystem (AMD)

| Metric | Detail |
|---|---|
| Developer Base | Growing but significantly smaller |
| Core Libraries | HIP, ROCm 7.0, MIOpen, RCCL |
| Framework Support | PyTorch 2.7/2.9, TF 2.19, JAX 0.6, vLLM |
| Performance Gap vs CUDA | 10-30% |
| Key Weakness | Setup measured in days vs hours |

### Ecosystem Maturity Verdict

| Factor | Winner |
|---|---|
| Performance | CUDA (10-30% faster) |
| Cost | ROCm (15-40% cheaper hardware) |
| Ease of Setup | CUDA (hours vs days) |
| Documentation | CUDA (vastly superior) |
| Open Source | ROCm (fully open) |
| Production Readiness | CUDA (proven at scale) |
| Community | CUDA (~4M devs) |

---

## 4. Deployment & Real-World Usage

### Groq Customers

| Customer | Use Case |
|---|---|
| **IBM** | watsonx Orchestrate, agentic AI |
| **Canva** | AI inference for design platform |
| **Thoughtworks** | Real-time speech-to-text (5x faster, 5x lower cost vs GPUs) |
| **Quantium** | Enterprise AI at scale |

### Groq Infrastructure
- **13 data centers** globally
- Hundreds of thousands of LPUs
- 20M+ tokens/sec across network
- **NVIDIA $20B deal (Dec 2025)**: Non-exclusive licensing, Jonathan Ross → NVIDIA SVP of Inference Architecture, ~90% of engineering team joined NVIDIA

### Market Adoption: NVIDIA vs AMD

| Metric | NVIDIA | AMD |
|---|---|---|
| AI accelerator revenue share | ~80-95% | Single-digit % |
| Data center GPU server share (Q4 2024) | >90% | <10% |
| Q3 2024 Data Center Revenue | $51.2B | $4.3B |

---

## 5. Cost Efficiency

### Groq API Pricing (per Million Tokens)

| Model | Input /M | Output /M | Speed |
|---|---|---|---|
| Llama 3.1 8B Instant | $0.05 | $0.08 | 840 TPS |
| Llama 4 Scout (17Bx16E) | $0.11 | $0.34 | 594 TPS |
| Llama 3.3 70B Versatile | $0.59 | $0.79 | 394 TPS |

### Per-Token Cost Comparison (70B-class model)

| Factor | Groq API | NVIDIA GPU Cloud |
|---|---|---|
| Price per 1M output tokens | **$0.79** | ~$0.50-$1.50 |
| Setup overhead | Zero (API key) | Days-weeks |
| Latency (TTFT) | ~10-40ms | ~100-500ms+ |
| Tokens/second (70B) | **394 TPS** | ~50-150 TPS |
| Idle cost | $0 (pay per token) | $1-7/hr |

---

## Summary: Strategic Positioning

| Dimension | Winner |
|---|---|
| **Raw inference speed** | Groq LPU (3-18x faster) |
| **MLPerf official** | NVIDIA (H200/B200 dominate) |
| **Energy efficiency** | Groq LPU (~10x better) |
| **Large model capacity** | NVIDIA/AMD (HBM capacity) |
| **Training capability** | NVIDIA (CUDA ecosystem) |
| **Developer ecosystem** | NVIDIA CUDA (15+ year head start) |
| **Cost per token (small-med)** | Groq (pay-per-token) |
| **Cost per token (mass scale)** | NVIDIA (optimized batching) |
| **Enterprise adoption** | NVIDIA (>90% market share) |

Sources: Groq official blog, Artificial Analysis, MLPerf Inference 4.1, SemiAnalysis, Tom's Hardware, NVIDIA/AMD official docs, The Register.
