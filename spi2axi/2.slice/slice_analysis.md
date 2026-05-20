# SPI2AXI SPEC — Slice 分析

按章节提取源文档内容，标注图片/表格/代码块及缺失信息。

---

## Chapter 1: 产品概述与特性

### 1.1 概述
SPI2AXI IP 是一个将 SPI 从设备接口转换为 AXI 主设备接口的桥接模块，允许通过 SPI 总线访问 AXI 总线上的存储器和外设。SPI 是通用数字接口，可在桌面 PC 上使用，方便 pattern 调试和实验室 bringup/debug。

### 1.2 主要特性
| 特性 | 描述 |
|------|------|
| SPI 接口 | 支持标准 SPI 和四线 SPI (QSPI) 两种工作模式；SPI Slave 作为主动外设，无需 SoC CPU 干预 |
| AXI Lite 接口 | 将 SPI 命令/数据转换为 AXI 事务；通过 AXI Lite 访问 SoC 内存和外设 |
| 跨时钟域处理 | SPI 与 AXI 时钟域分离；内置 dual-clock FIFOs 实现可靠 CDC |

**状态**: ✅ 完整

---

## Chapter 2: 接口定义

### 2.1 SPI 接口信号
| 信号名称 | 方向 | 宽度 | 描述 |
|----------|------|------|------|
| spi_sclk | 输入 | 1 | SPI 串行时钟，50MHz |
| spi_cs | 输入 | 1 | SPI 片选信号（低有效） |
| spi_sdi | 输入 | 4 | SPI 数据输入线 [3:0] |
| spi_sdo | 输出 | 4 | SPI 数据输出线 [3:0] |

### 2.2 AXI4 Lite 主设备接口
5 个通道：
- 写地址通道（AW）
- 读地址通道（AR）
- 写数据通道（W）
- 读数据通道（R）
- 写响应通道（B）

**状态**: ✅ 完整（AXI 标准信号需按协议展开）

---

## Chapter 3: 可配置参数

| 参数 | 默认值 | 描述 |
|------|--------|------|
| AXI_ADDR_WIDTH | 32 | AXI 地址总线宽度 |
| AXI_DATA_WIDTH | 32 | AXI 数据总线宽度 |
| AXI_ID_WIDTH | 3 | AXI ID 信号宽度 |
| DUMMY_CYCLES | 32 | SPI 读操作虚拟周期数，实际 Dummy_cycle = 配置值 + 1 |

**状态**: ✅ 完整

---

## Chapter 4: 操作协议

### 4.1 写操作序列
1. （可选）配置 SPI 参数（1线或4线模式）
2. SPI 主机发送写命令和地址
3. 控制器解析命令并同步到 AXI 时钟域
4. AXI 桥接发起写地址事务
5. 通过 FIFO 传输写数据
6. 等待 AXI 写响应完成

### 4.2 读操作序列
1. （可选）配置 SPI 参数（1线或4线模式）
2. SPI 主机发送读命令和地址
3. 控制器同步读请求到 AXI 时钟域
4. AXI 桥接发起读地址事务
5. 从 AXI 总线读取数据到 TX FIFO
6. 通过 SPI 接口返回读取的数据

### 4.3 SPI 命令协议
- 主设备发送 8-bit 操作码 (opcode)
- 内存访问：后跟 32-bit 地址（MSB first）
- 寄存器访问：地址由操作码编码
- 读操作：插入 32（可编程）个 dummy cycle 等待数据返回
- 数据在最后 32-bit 传输（MSB first）

### 4.4 SPI 命令操作码
> **图片内容** — PDF 第 5 页包含操作码编码表（图片格式），需手动补充：
> - 各操作码值对应的读/写命令
> - 内存访问 vs 寄存器访问区分
> - **待补充**: 操作码编码表详细内容

### 4.5 SPI 侧寄存器设定
> **图片内容** — PDF 第 5 页包含寄存器映射表（图片格式）
> - **待补充**: 寄存器地址、名称、位域定义

**状态**: ⚠️ 部分完整（操作码表和寄存器表为图片，需补充）

---

## Chapter 5: FSM 状态机

PDF 第 4 页提到"该从属控制器基于有限状态机"，包含 FSM 图示。
- **待补充**: FSM 状态定义、状态转移条件

**状态**: ⚠️ 待补充

---

## Chapter 6: 时序图

### 6.1 QSPI 写时序
> **图片内容** — PDF 第 6 页包含 QSPI 写时序图

### 6.2 QSPI 读时序
> **图片内容** — PDF 第 6 页包含 QSPI 读时序图

**状态**: ⚠️ 图片格式，需文字化描述或保留引用

---

## Chapter 7: Wrap 地址环绕功能

### 7.1 功能描述
- AXI4-Lite 仅支持 single transfer，AxLEN = 0，AxSIZE = 2（32-bit 字）
- SPI2AXI 引入可配置地址 Wrap 功能
- **Wrap = 0**: 无环绕
- **Wrap = N (N > 0)**: 环绕窗口 = N 个 word = 4×N 字节
  - 起始地址 4 字节对齐
  - 每次传输地址 +4
  - 访问完 N 个 word 后回绕到起始地址

### 7.2 示例 (Wrap=2, 起始地址 'h100)
```
Burst 0: Write to 'h100 (word 1)
Burst 1: Write to 'h104 (word 2)
Burst 2: Write to 'h100 (wrap, word 1)
Burst 3: Write to 'h104 (word 2)
Burst 4: Write to 'h100 (wrap, word 1)
```

**状态**: ✅ 完整

---

## Chapter 8: 应用场景
- 系统调试和配置接口
- 低引脚数系统总线扩展
- 嵌入式系统固件更新
- 芯片测试和验证接口

**状态**: ✅ 完整

---

## Chapter 9: CDC 跨时钟域设计

PDF 中提到：
- SPI 时钟域与 AXI 时钟域分离
- 内置 dual-clock FIFOs 实现可靠 CDC

**状态**: ⚠️ 需补充详细 CDC 设计方案

---

## Chapter 10: 系统架构

SPI slave 实现版本，SoC 配备双时钟 FIFO，SPI 时钟域 → SoC (AXI) 时钟域转换。
在 S3 中用于访问 config 配置空间。

**状态**: ⚠️ 需补充架构框图
