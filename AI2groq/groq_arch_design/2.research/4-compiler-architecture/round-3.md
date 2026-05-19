# Round 3: 内存布局优化、GroqFlow 源码分析与架构对比
## Memory Layout, GroqFlow Source Analysis & Architecture Comparison

**Created:** 20260519-1020  
**Author:** Groq Compiler Architecture Expert  
**Status:** Complete

---

## 1. 编译器驱动的内存布局 / Compiler-Driven Memory Layout

### 1.1 TSP 内存层次

```
Register-level: Streaming Registers (SR)
    ↓ 64 streams/lane (32E + 32W), 32 bytes/stream
    ↓ 编译器管理所有 stream 的生命周期
Memory-level: 全局共享 SRAM, 220 MB
    ↓ 无缓存层次，无 TLB
    ↓ 编译器决定所有数据的物理地址
Tiling-level: 重量/激活 Tile, 每个 320×320
    ↓ 矩阵乘法专用的 systolic array buffer
    ↓ 所有 4 个 weight tile 可在 40 周期内加载
```

### 1.2 编译器内存管理的关键挑战

#### 挑战 1: Stream 寄存器分配

每个通道只有 64 个流 (stream) 寄存器，而 ML 计算图中中间张量可能超过 64 个。编译器必须：

```
流分配算法 (推测):
  1. 构建张量 liveness 区间
  2. 图着色分配 stream 寄存器
  3. 超出 64 时插入 spill/reload 到 SRAM
  4. 优化 spill 位置以最小化延迟

与 CPU register allocation 的对比:
  CPU:      寄存器数量 ~16-32, 编译器用图着色
  Groq TSP: stream 寄存器 64/通道, 同样用图着色
             但 spill 到 SRAM 的开销已知且确定
```

#### 挑战 2: SRAM Bank 冲突避免

TSP 的 SRAM 被组织为多 bank 结构。由于无硬件 bank 冲突解决机制，编译器必须静态避免冲突：

```
Bank Conflict 场景:
  同一周期内, 两个 stream 访问同 bank 的不同地址 ⇒ 延迟增加
  
编译器对策:
  1. 分析访问模式 (stride, pattern)
  2. 调整数据排列 (padding, transposing)
  3. 交错调度访问 (时间上错开冲突访问)
```

#### 挑战 3: 张量平铺 (Tensor Tiling)

对于大矩阵乘法（如 transformer 的 QKV），矩阵必须分块存入 SRAM：

```
Tiling 策略:
  1. 确定 tile 大小: 适配 MXM 的 systolic array (320×320)
  2. 确定 tile 顺序: 行主序 vs 列主序
  3. 计算 tile 间依赖: 部分和传递
  4. 调度 tile 加载: 双缓冲隐藏加载延迟
  
编译器生成 "tiling loop nest" 的静态展开版本:
  for (int i = 0; i < M; i += Ti)
    for (int j = 0; j < N; j += Tj)
      for (int k = 0; k < K; k += Tk)
        // 全部展开为静态指令序列
```

### 1.3 FP16 与 INT8 量化支持

GroqFlow 在 Stage 4 执行 FP16 转换，同时可选 int8 量化：

```
FP16 转换:
  - GroqFlow 自动将 FP32 权重转为 FP16
  - 精度通常在 1% 以内
  
INT8 量化:
  - 需要校准数据 (quantization_samples)
  - 后训练量化 (PTQ), 不需要 QAT
  - 编译器处理 scale/zero-point 的 stream 传输
```

---

## 2. GroqFlow 源码结构分析

### 2.1 仓库概况

| 属性 | 值 |
|------|-----|
| 仓库 | https://github.com/groq/groqflow |
| 语言 | 100% Python |
| 许可证 | MIT |
| Stars | ~109 |
| 状态 | 2025 年 7 月 31 日归档 (只读) |

### 2.2 关键源码模块分析

#### `groqflow/__init__.py` — 入口

```python
# 核心导出
from groqflow.groqflow import groqit
from groqflow.groqflow import list_builds, delete_build, GroqModel
```

#### `groqflow/common/build.py` — Build 配置

这个模块定义了 GroqFlow 的核心数据类型：

```python
# 拓扑常量
DRAGONFLY = "DRAGONFLY"       # 蜻蜓拓扑：适用于跨多芯片的 all-to-all 通信
ROTATIONAL = "ROTATIONAL"      # 旋转拓扑：适用于流水线并行

# BuildConfig 类
# - num_chips: int (默认自动检测)
# - topology: str (DRAGONFLY/ROTATIONAL)
# - rebuild: str (if_needed/always/never)
# - compiler_flags: list[str]
# - assembler_flags: list[str]
```

#### `groqflow/stages/` — Stage 实现

每个 stage 继承自基础 `Stage` 类，提供 `run()` 接口：

```
Stage 基类:
  - run()       : 执行 stage
  - check()     : 检查是否可跳过 (缓存命中)
  - get_cache() : 返回缓存路径
```

具体 stage：
- `onnx_convert` 使用 torch.onnx.export 将模型转为 ONNX
- `onnx_optimize` 使用 onnxruntime 工具优化图
- `op_check` 调用 Groq 内部 API 做算子合规检查
- `compile` 调用 `groq-compiler` 二进制（闭源 MLIR 前端）
- `assemble` 调用 `groq-assembler` 二进制（闭源 Haskell 后端）

#### `groqflow/models/` — 模型封装

`GroqModel` 封装了编译后的程序：

```python
class GroqModel:
    def run(self, *inputs):           # 单次推理
    def run_abunch(self, *inputs):    # 批量推理 (自动 batching)
    def estimate_performance(self):   # 预估性能 (延迟、吞吐量)
    def groqview(self):               # 可视化编译结果
    def netron(self):                 # Netron 模型图查看
```

### 2.3 对闭源层的分析

GroqFlow 开源的部分止步于 **调用闭源二进制**。`compile` 和 `assemble` 两个 stage 只是 shell out 到 GroqWare Suite 中的工具：

```
groqit() 
  → groqflow/stages/compile.py::run()
    → subprocess.run(["groq-compiler", ...])   # 闭源
  → groqflow/stages/assemble.py::run()
    → subprocess.run(["groq-assembler", ...])  # 闭源
```

这意味着：
- MLIR 前端使用的 Groq Dialect 定义不在开源仓库中
- Haskell 后端的调度器完全闭源
- 汇编器输出的 IOP 二进制格式也闭源

---

## 3. 架构对比 / Architecture Comparison

### 3.1 Groq vs GPU (NVIDIA CUDA) 编译器对比

| 维度 | Groq TSP | NVIDIA GPU (CUDA) |
|------|----------|-------------------|
| **调度时机** | 全部静态 (编译时) | 动态调度 (硬件 warp scheduler) |
| **编译器类型** | 全静态调度编译器 | JIT 编译 + 动态发射 |
| **内存模型** | 无缓存，编译器分配 SRAM | 复杂缓存层次 + 程序员控制 shared mem |
| **并行模型** | 144 队列 × 确定性 | SM × warp × 动态线程调度 |
| **确定性** | 相同输入 = 相同周期数 | 不确定 (硬件调度波动) |
| **延迟可预测性** | 精确到 cycle | 统计性 |
| **编程语言** | Python (GroqFlow) → MLIR → Haskell | CUDA C++ → PTX → SASS |
| **编译器难度** | 调度器极其复杂 (NP-hard) | 常规优化 + JIT |
| **调试/Profiling** | GroqView (可视化 trace) | Nsight, nvprof |

### 3.2 Groq vs Cerebras vs SambaNova

| 维度 | Groq | Cerebras | SambaNova |
|------|------|----------|-----------|
| **编译器方法** | 全静态调度 | 图编译器 + 数据并行 | 可重构数据流 |
| **硬件范式** | 功能切片 (functional slices) | 晶圆级大规模 2D 阵列 | 可重构数据流单元 (RDU) |
| **确定性** | 是，完全确定 | 部分 | 是 (数据流图) |
| **调度复杂性** | 144 队列需 ILP 求解 | 图分区 + 映射到 PE | 数据流编译器 |
| **框架支持** | PyTorch, TF, ONNX | PyTorch, TF | PyTorch, TF, ONNX |
| **生态成熟度** | 较新，闭源工具链 | 较成熟 | 较成熟 |

### 3.3 Groq vs FPGA

Groq TSP 可被视作一种 **粗粒度可重构架构**：

| 维度 | Groq TSP | FPGA |
|------|----------|------|
| **粒度** | 功能列 (MXM, VXM 等) | LUT + DSP + BRAM |
| **编程模型** | ML 框架 → MLIR → Haskell | Verilog/VHDL → HLS |
| **重构时机** | 静态 (固定硬件) | 可重配置比特流 |
| **抽象层次** | 高 (ML 算子级) | 低 (RTL 级) |
| **确定性** | 完全确定 | 取决于设计 |
| **编译器复杂度** | 极其复杂的调度器 | 逻辑综合 + 布局布线 |

---

## 4. 关键洞察与未来方向

### 4.1 Groq 编译器架构的成败关键

**成功因素:**
1. 确定性哲学从硬件到编译器的一致性 — 简化了所有层的设计
2. 功能切片的设计天然匹配 ML 计算图 (典型 ML 模型 = 矩阵乘法 + 向量操作 + 激活)
3. Haskell 的类型安全性在调度这种高复杂度问题上具有优势

**风险因素:**
1. 静态调度对不规则计算（控制流密集的任务）效率低下
2. 编译时间随模型大小超线性增长（ILP 求解的复杂度）
3. 工具链闭源导致社区生态发展受限
4. 人才招聘困难（同时精通 Haskell、编译器、硬件的工程师极其稀缺）

### 4.2 技术演进方向

1. **MLIR 更深度整合**: 随着 MLIR 社区的 CIRCT、TOSA、StableHLO 等项目的成熟，Groq 可以在 MLIR 层做更多优化
2. **动态编译探索**: 对于某些动态 shape 的场景，可能引入轻量级 JIT 编译
3. **精度自适应**: 编译器自动选择 FP16/BF16/int8 的混合精度策略
4. **自动化图分区**: 跨多芯片的编译器自动并行更加智能化

---

**完成研究阶段。下一个阶段: Phase 3 — Layer 2 深度展开分析**
