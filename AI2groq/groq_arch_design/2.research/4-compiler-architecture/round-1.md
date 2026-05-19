# Round 1: GroqFlow 工具链与 MLIR 前端深度分析
## GroqFlow Toolchain & MLIR Frontend — Deep Analysis

**Created:** 20260519-1000  
**Author:** Groq Compiler Architecture Expert  
**Status:** Complete

---

## 1. GroqFlow — 用户入口的自动化编译流

### 1.1 定位与角色 / Role & Positioning

GroqFlow 是 Groq 编译器的**用户级 Python 接口**，提供从主流 ML 框架到 GroqChip LPU 的端到端自动化编译流程。其核心设计理念是 **"write once, compile for Groq"**。

```python
from groqflow import groqit
gmodel = groqit(model, inputs)  # 编译并返回 GroqModel
gmodel(**inputs)                # 在 LPU 上执行推理
```

### 1.2 支持的框架 / Supported Frameworks

| 框架 | 输入类型 | 说明 |
|------|----------|------|
| PyTorch | `torch.nn.Module` | 最常用入口，JIT trace 捕获图 |
| Keras/TF | `tf.keras.Model` | TensorFlow 模型支持 |
| TorchScript | `torch.jit.ScriptModule` | 静态图输入 |
| ONNX | `.onnx` 文件路径 | 标准中间表示 |
| scikit-learn | RandomForest, SVM, MLP etc. | 经 Hummingbird 转换 |
| xgboost | XGBClassifier, XGBRegressor | 经 Hummingbird 转换 |

### 1.3 默认构建流水线 / Default Build Pipeline

GroqFlow 按序执行以下 6 个 stage，每个 stage 均可被用户自定义跳过或替换：

```
Stage 1: Convert to ONNX          # 模型 → ONNX 中间表示
    ↓
Stage 2: Optimize ONNX file       # ONNX 图优化 (常量折叠、算子融合等)
    ↓
Stage 3: Check op support         # 算子合规性检查 (是否 TSP 支持)
    ↓
Stage 4: Convert to FP16          # 参数精度转换 (FP32 → FP16)
    ↓
Stage 5: Compile Model            # Groq Compiler 编译 (MLIR frontend)
    ↓
Stage 6: Assemble Model           # Groq Assembler 汇编 (Haskell backend)
```

**关键设计决策**: GroqFlow 选择 ONNX 作为**框架无关的中间表示**，而非直接使用 PyTorch/TF 的内部 IR。这使得：
- 框架适配工作简化为 "任意框架 → ONNX"
- 可利用 ONNX 生态的优化工具
- 与 Groq IR 的边界清晰

### 1.4 API 关键参数 / Key `groqit()` Arguments

| 参数 | 作用 | 商业意义 |
|------|------|----------|
| `num_chips` | 指定使用多少颗 TSP | 多芯片自动并行 |
| `topology` | `DRAGONFLY`/`ROTATIONAL` | 多芯片互联拓扑选择 |
| `rebuild` | 缓存策略 (`if_needed`/`always`/`never`) | 避免重复编译 |
| `quantization_samples` | int8 量化校准数据 | 低精度推理 |
| `compiler_flags` | 传递给 Groq Compiler 的自定义 flag | 高级用户调优 |

### 1.5 包结构 / Package Structure

```
groqflow/
├── __init__.py          # 导出 groqit()
├── common/
│   └── build.py         # Build 配置：拓扑常量、默认参数
├── stages/
│   ├── onnx_convert     # Stage 1: 转换到 ONNX
│   ├── onnx_optimize    # Stage 2: 图优化
│   ├── op_check          # Stage 3: op 检查
│   ├── fp16_convert      # Stage 4: FP16 转换
│   ├── compile           # Stage 5: 编译
│   └── assemble          # Stage 6: 汇编
├── models/
│   ├── GroqModel         # 基类：run(), run_abunch(), estimate_performance()
│   ├── PytorchModelWrapper  # 返回 torch.Tensor
│   └── KerasModelWrapper    # 返回 tf.Tensor
└── cache/                # 构建缓存管理
```

### 1.6 构建缓存 / Build Cache

GroqFlow 提供 `~/.cache/groqflow/` 的构建缓存机制，按 `build_name` 索引。支持：
- `rebuild="never"`: 缓存在时直接加载
- `rebuild="if_needed"`: 模型变更时自动重编译
- `rebuild="always"`: 强制全量编译

---

## 2. MLIR 前端 — 多级 IR 转换

### 2.1 MLIR 在 Groq 编译器中的角色

Groq 选择 MLIR 作为前端框架的核心原因：

1. **多级抽象**: 从高层图 IR 逐步 lower 到接近硬件的 IR
2. **Dialect 扩展性**: 自定义 Groq dialect 表达 TSP 专属语义
3. **Pass 管理**: MLIR 的 pass pipeline 框架可以直接复用
4. **跨框架兼容**: MLIR 的 ONNX/TOSA/HLO dialect 覆盖主流框架

### 2.2 IR 转换路径 / IR Lowering Pipeline

```
PyTorch Model / TF Model / ONNX
         │
         ▼
   [ONNX Dialect]     ← 高层图表示 (数学语义)
         │
         ▼
   [TOSA Dialect]     ← 目标无关的算子级 IR (可选，用于验证)
         │
         ▼
   [Groq Dialect]     ← TSP 自定义 dialect (硬件感知)
         │  (graph-level optimization passes)
         ▼
   [Groq Dialect (opt)]  ← 融合、布局变换、常量折叠
         │
         ▼
   [LLVM Dialect / C++ emission]
         │
         ▼
   Haskell Backend (static scheduling + codegen)
```

### 2.3 Groq Dialect 设计要点

根据 Groq Sr. Compiler Engineer 的招聘描述，Dialect 开发的工作包括：

- **算子覆盖**: 持续扩展 Groq IR Dialect 以覆盖新的 ML 算子（Transformer、Mamba 等新架构）
- **融合规则**: 定义算子融合的 pattern — MXM + VXM 融合、Activation 融合等
- **数据类型**: FP16/BF16/int8 等混合精度在 IR 层面的表示
- **布局变换**: NHWC/NCHW/自定义布局的转换规则

### 2.4 MLIR Pass Pipeline 推测

基于 TSP 硬件特性，可以推断 MLIR 前端的关键 Pass：

| Pass | 作用 | 硬件映射 |
|------|------|----------|
| `--canonicalize` | 规范化 (折叠、简化) | — |
| `--inline` | 内联子图 | — |
| `--grok-fuse-ops` | 算子融合 (Conv+BN+ReLU) | 减少存中间结果 |
| `--grok-layout-transform` | 内存布局优化 | 匹配 MEM slice 访问模式 |
| `--grok-constant-fold` | 常量折叠 | 减少运行时计算 |
| `--grok-partition` | 图分区 (跨芯片/跨 queue) | 144 队列的作业分配 |
| `--convert-to-haskell-ir` | 发射到 Haskell 后端 | 输入给调度器 |

### 2.5 多芯片编译 / Multi-TSP Compilation

MLIR 前端承担的跨芯片编译职责：

1. **图分区**: 将大模型按层/算子切分到多颗 TSP
2. **通信注入**: 插入 inter-chip 的 stream 通信指令
3. **拓扑感知**: 根据 `DRAGONFLY` 或 `ROTATIONAL` 拓扑调整通信模式
4. **负载均衡**: 静态计算各芯片的计算/通信比例

---

## 3. 关键洞察 / Key Insights

### 3.1 GroqFlow 的架构权衡

- **ONNX 作为中间格式的取舍**: 优点是框架无关，缺点是 ONNX 算子集正被不断增长的 ML 新算子追赶，Groq 必须持续更新 dialect
- **构建缓存的设计**: 反映了编译时间长的现实（全静态调度需要大量计算），缓存策略减少重复编译
- **API 简洁性的代价**: `groqit()` 的一行接口隐藏了极其复杂的编译链，调试时难以定位问题

### 3.2 MLIR 前端的战略意义

Groq 选择 MLIR 而非直接构建自定义前端，是**务实的技术决策**：
- MLIR 社区持续发展新 dialect（如 TOSA、StableHLO），Groq 可免费受益
- 从 MLIR 到 Haskell 后端的接口比从 ONNX 直接生成更可控
- 但这也意味着编译器的关键优化（调度、内存）全部在闭源的 Haskell 后端中

---

**Next**: [Round 2 — Haskell 后端与静态调度算法](./round-2.md)
