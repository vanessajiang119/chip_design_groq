# VXM — 向量执行模块详细设计分析
# VXM — Vector Execution Module Detailed Design Analysis

> 创建时间: 2026-05-19T1630
> 分析层级: Layer 2 (微架构深度展开)

---

## 1. 概述 (Overview)

VXM (Vector Execution Module) 是 Groq TSP 的向量处理引擎。每个 Super Lane 包含一个 VXM (16 个 ALU)，全芯片共 320 个 SIMD 通道 × 16 ALU/通道 = 5,120 个向量 ALU。VXM 负责所有元素级 (element-wise) 向量运算、激活函数、类型转换和归约操作。

### 架构定位

```
Super Lane 内部排列:
┌──────┬─────┬──────────┬────────────────────┬──────────┬─────┬──────┐
│ MXM  │ SXM │  MEM_L   │       VXM          │  MEM_R   │ SXM │ MXM  │
│(矩阵)│(开关)│ (存储左)  │ (向量 — 中心位置)    │ (存储右)  │(开关)│(矩阵)│
└──────┴─────┴──────────┴────────────────────┴──────────┴─────┴──────┘

VXM 位于每个 Super Lane 的中心 — 两侧对称镜像分布 MEM + SXM + MXM
形成两个准独立的"计算半球 (hemisphere)"
```

---

## 2. 微架构设计 (Microarchitecture)

### VXM 内部结构

```
VXM (每个 Super Lane, 16 lanes × 32 bytes):
┌─────────────────────────────────────────────────────────────┐
│  Lane 0    Lane 1    Lane 2    ...    Lane 14   Lane 15     │
│ ┌──────┐  ┌──────┐  ┌──────┐         ┌──────┐  ┌──────┐    │
│ │ ALU0 │  │ ALU1 │  │ ALU2 │         │ ALU14│  │ ALU15│    │
│ │┌────┐│  │┌────┐│  │┌────┐│         │┌────┐│  │┌────┐│    │
│ ││ FP ││  ││ FP ││  ││ FP ││         ││ FP ││  ││ FP ││    │
│ ││ INT ││  ││ INT ││  ││ INT ││         ││ INT ││  ││ INT ││    │
│ ││ SIMD││  ││ SIMD││  ││ SIMD││         ││ SIMD││  ││ SIMD││    │
│ │└────┘│  │└────┘│  │└────┘│         │└────┘│  │└────┘│    │
│ │┌────┐│  │┌────┐│  │┌────┐│         │┌────┐│  │┌────┐│    │
│ ││MAC ││  ││MAC ││  ││MAC ││         ││MAC ││  ││MAC ││    │ ← 标量 MAC
│ │└────┘│  │└────┘│  │└────┘│         │└────┘│  │└────┘│    │
│ └──────┘  └──────┘  └──────┘         └──────┘  └──────┘    │
│ ┌──────┐  ┌──────┐  ┌──────┐         ┌──────┐  ┌──────┐    │
│ │RF(流)│  │RF(流)│  │RF(流)│         │RF(流)│  │RF(流)│    │ ← 流式 RF
│ └──────┘  └──────┘  └──────┘         └──────┘  └──────┘    │
└─────────────────────────────────────────────────────────────┘
```

### ALU 内部组成 (ALU Internals)

每个 ALU 包含:

| 子单元 | 功能 | 位宽 |
|--------|------|------|
| FP32 Adder | 浮点加法/减法 | 32-bit |
| FP32 Multiplier | 浮点乘法 | 32-bit |
| INT32 ALU | 整数算术/逻辑 | 32-bit |
| FP16/BF16 Unit | 半精度运算 | 16-bit |
| INT8 SIMD | 8-bit SIMD 运算 | 32-bit (4×INT8) |
| Type Converter | 精度转换 | 可变 |
| Comparator | 比较/选择 | 32-bit |

### 全芯片向量能力汇总

| 参数 | 数值 |
|------|------|
| Super Lane 数 | 20 |
| 每 SL ALU 数 | 16 |
| 全芯片 ALU 数 | 320 |
| 全芯片运算单元数 | 5,120 (含每个 ALU 内的多个子单元) |
| 向量宽度 | 320 elements/cycle |
| 数据路径宽度 | 32 bytes/lane |
| 流水线深度 | 20 级 |
| 每 cycle 最大操作 | 320 × 16 = 5,120 ops/cycle |
| 每 cycle 最大 INT8 操作 | 5,120 × 4 = 20,480 ops/cycle |

---

## 3. 流水线设计 (Pipeline Design)

### 20 级向量流水线

基于功能分片和数据流模型，推测 VXM 的流水线阶段:

```
Stage 0-1:  指令接收 (Inst Receive)
            从垂直指令流接收来自 ICU 的 VXM 操作码
            Stream ID 解析

Stage 2-3:  操作数加载 (Operand Load)  
            从东西方向数据流接收源操作数
            如果数据未到达 → 等待 (编译器保证精确到达)

Stage 4-5:  流合并 (Stream Combine)
            多流输入合并 (如有)
            数据类型统一

Stage 6-12: 算术执行 (Arithmetic Execute)
            FP/INT 运算核心执行
            不同运算延迟不同:
              - INT ADD: 1 cycle
              - INT MUL: 2-3 cycles
              - FP ADD: 3-4 cycles
              - FP MUL: 4-5 cycles
              - FP DIV: 7-12 cycles

Stage 13-15: 类型转换/格式化 (Type Convert/Format)
             结果精度转换
             TruePoint 累加输出格式化

Stage 16-17: 归约操作 (Reduce Operation)
             跨 lane 的 SUM/MAX/MIN
             用于 attention 等操作

Stage 18-19: 结果输出 (Result Output)
             将结果写回数据流
             指定输出 Stream ID 和方向
```

### 流水线交错 (Pipeline Interleaving)

由于 20 个 Super Lane 垂直堆叠:
```
Cycle 0:  ICU 发射 VXM 指令
Cycle 1:  SL 0(VXM) 开始执行
          同时 ICU 发射下一条 VXM 指令
Cycle 2:  SL 0(VXM) Stage 1, SL 1(VXM) Stage 0
          ICU 继续发射
...
Cycle 20: SL 19 开始执行
          SL 0 完成执行
```

---

## 4. 数据类型与精度 (Data Types & Precision)

### 支持的数据类型

| 类型 | 位宽 | VXM 操作 | 性能 (ops/cycle) |
|------|------|---------|-----------------|
| INT8 | 8-bit | ADD/MUL/CMP | 20,480 |
| INT16 | 16-bit | ADD/MUL/CMP | 10,240 |
| INT32 | 32-bit | ADD/MUL/CMP | 5,120 |
| FP8 | 8-bit | ADD/MUL | 20,480 |
| FP16 | 16-bit | ADD/MUL | 10,240 |
| BF16 | 16-bit | ADD/MUL | 10,240 |
| FP32 | 32-bit | ADD/MUL | 5,120 |

### TruePoint Numerics 详解

Groq 的专有精度管理技术:

```
传统方式:
  FP16 输入 → FP16 乘法 → FP16 累加 → FP16 输出
            ↘ 精度损失 ↗

TruePoint 方式:
  INT8/FP16 输入 → 全精度乘法 → 100-bit 累加器 → 按需量化输出
                                     ↓
                             精度无损累加
```

**关键特性**:
1. 矩阵运算使用 100-bit 中间累加器
2. 权重/激活值可用低精度 (INT8/FP16) 存储
3. 输出根据下游层的误差敏感度选择性量化
4. 保证无精度损失的累加 — 无论输入位宽

**实现推测**:
- 100-bit 累加器 = 多个 FP32 或大位宽定点累加器组成
- 支持 accumulate-and-quantize 指令
- 编译器控制量化点：在 MXM 输出处或在 VXM 后处理中

---

## 5. 向量指令集 (Vector Instruction Set)

### 算术指令

| 指令 | 操作 | 周期 |
|------|------|------|
| VADD | 向量加法 | 1-2 |
| VSUB | 向量减法 | 1-2 |
| VMUL | 向量乘法 | 2-3 |
| VFMUL | 向量浮点乘法 | 3-4 |
| VFDIV | 向量浮点除法 | 7-12 |
| VSQRT | 向量平方根 | 10-15 |
| VMLA | 向量乘加 (multiply-add) | 3-4 |
| VNEG | 向量取负 | 1 |

### 激活函数

| 指令 | 操作 | 实现方式 |
|------|------|---------|
| RELU | ReLU(x) = max(0,x) | 简单比较 |
| GELU | Gaussian Error Linear Unit | 分段近似 |
| TANH | 双曲正切 | 分段近似 |
| SIGMOID | S 型函数 | 分段近似 |
| EXP | 指数 | 迭代/查找表 |
| LOG | 对数 | 迭代/查找表 |
| SOFTMAX | Softmax (跨 lane) | 归约 + 指数 + 归一化 |

### 归约指令

| 指令 | 操作 | 跨 lane 实现 |
|------|------|-------------|
| REDUCE_SUM | 求和归约 | Tree reduction 跨 16 lanes |
| REDUCE_MAX | 最大值归约 | Tree reduction |
| REDUCE_MIN | 最小值归约 | Tree reduction |
| REDUCE_MEAN | 均值归约 | SUM + DIV |

### 类型转换

| 指令 | 转换 |
|------|------|
| CVT_I8_F16 | INT8 → FP16 |
| CVT_F16_F32 | FP16 → FP32 |
| CVT_F32_I8 | FP32 → INT8 (量化) |
| CVT_BF16_F32 | BF16 → FP32 |
| PACK_I8 | 打包 4×INT8 到 32-bit |
| UNPACK_I8 | 解包 32-bit 到 4×INT8 |

---

## 6. 数据通路设计 (Data Path Design)

### 输入选择 (Input Select)

每个 ALU 可以从以下来源选择操作数:
- **Stream East**: 来自东侧 MEM/SXM 的数据流
- **Stream West**: 来自西侧 MEM/SXM 的数据流
- **MXM Result**: 来自 MXM 的链式结果
- **广播 (Broadcast)**: 来自 SXM 的广播值
- **立即数 (Immediate)**: 指令中的立即字段

### 链式数据流 (Chaining)

```
MXM(矩阵结果) ──► VXM(激活函数) ──► MEM(存储结果)
                      ↑
                 流操作数 (来自 MEM)

无需寄存器文件中间存储:
  MXM → VXM 链: 矩阵乘结果直接流向 VXM 进行激活函数处理
  VXM → MEM 链: 向量结果直接流向 MEM 存储
  VXM → VXM 链: 向量结果直接流向另一个 VXM 操作
```

### 寄存器文件 (Register File)

TSP 不使用传统向量寄存器文件，而是使用**流式寄存器文件 (Stream RF)**:

| 特性 | 传统 VRFs | TSP 流式 RF |
|------|----------|------------|
| 结构 | 多端口 SRAM | 流寄存器 (每个 lane) |
| 容量 | 32-256 registers | 64 streams/lane |
| 寻址 | 寄存器编号 | Stream ID (0-31 × 2方向) |
| 生命周期 | 函数/基本块 | 单次数据流传输 |
| 编译器控制 | 寄存器分配 | 流调度 |

---

## 7. 面积与功耗 (Area & Power)

### VXM 面积分解 (推测)

| 子模块 | 占比 (SL 级) | 全芯片面积 |
|--------|------------|----------|
| ALU 阵列 (16 ALU × 20 SL) | ~50% | ~36 mm² |
| 流式 RF (64 streams × 16 lanes) | ~20% | ~14 mm² |
| 数据路径布线 | ~15% | ~11 mm² |
| 输入选择/路由 | ~10% | ~7 mm² |
| 控制逻辑 | ~5% | ~4 mm² |
| **VXM 总计** | **100%** | **~72 mm²** |

### 每 cycle 功耗 (推测)

| 操作类型 | 每 ALU 功耗 | 全芯片功耗 |
|---------|-----------|-----------|
| INT8 ADD | ~0.5 mW | ~1.6 W |
| FP16 MUL | ~2 mW | ~6.4 W |
| FP32 FMA | ~5 mW | ~16 W |
| 激活函数 | ~3 mW | ~9.6 W |

---

## 8. 与传统向量单元对比 (Comparison)

| 特性 | TSP VXM | NVIDIA Tensor Core | ARM SVE |
|------|---------|-------------------|---------|
| SIMD 宽度 | 320 (全芯片) | 32 (warp) | 128-2048 bits |
| ALU 数 | 5,120 | 64-256 | 可变 |
| 寄存器文件 | 流式 (64 streams) | 256 KB (regfile) | 32 registers |
| 数据类型 | INT8/FP16/FP32/BF16 | FP16/FP32/TF32 | INT/FP 全 |
| 流水线 | 20 级 + tile 管道 | 动态调度 | 顺序/乱序 |
| 控制方式 | 编译器静态 | SIMT scheduler | 硬件控制 |
| 面积效率 | 高 (无调度器) | 中 | 低 |
