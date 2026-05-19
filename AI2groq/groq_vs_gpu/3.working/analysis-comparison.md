# Working Analysis — Groq vs GPU 架构对比结论

> 分析时间: 2026-05-18
> 当前迭代: Round 3 / 3

## 研究发现总结

经过3轮搜索，已覆盖：
1. **架构对比** — Groq TSP 功能切片 vs NVIDIA SM/Tensor Core 微架构
2. **存储与编程模型** — SRAM 流式 vs HBM+Cache 层次，GroqFlow vs CUDA/Triton
3. **性能与生态** — MLPerf 数据、LLM 推理吞吐、开发者生态、TCO

## 关键发现

### 1. 架构哲学的根本差异
- **Groq**：确定性执行，消除所有"反应式硬件"（无缓存/无分支预测/无序外执行），编译器完全控制调度
- **GPU**：SIMT + 大量并发线程隐藏延迟，硬件 warp 调度器动态决策，用复杂度换取灵活性

### 2. 存储层次的互补取舍
- **Groq**：220 MB SRAM 片上，80 TB/s 带宽，延迟固定，适合小 batch 低延迟推理
- **GPU**：80-192 GB HBM 片外，3-8 TB/s 带宽，延迟可变，适合大模型大 batch

### 3. 推理场景 Groq 优势明显
- Llama 3.3 70B 推理速度 Groq 305 t/s 排名第一
- 能量效率 ~10x 优于 H100（1-3 J/token vs 10-30 J/token）
- TTFT 低至 0.005s

### 4. 生态与应用场景决定选择
- Groq 适用于延迟敏感、小 batch、固定计算图的推理场景
- NVIDIA GPU 适用于训练、大 batch、动态计算图、通用计算
- NVIDIA $20B 收购 Groq 技术验证了 LPU 架构的价值

## 决策

✅ **研究目标已达成**。进入 Phase 4: Final Result 阶段。

## 交付物确认

- [x] 1.planning/ — 搜索计划与配置
- [x] 2.research/ — 三轮搜索结构（架构/存储编程/性能生态）
- [x] 3.working/ — 综合分析与结论
- [ ] 4.result/ — 最终 HTML 报告 + 架构对比图
