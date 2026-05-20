# SPI2AXI Bridge Module - Planning Report

> 生成日期: 2026-05-20
> 规划阶段: 1.planning
> 文档类型: 内部 Block (单一功能模块: SPI Slave to AXI Master Bridge)

---

## 1. 源文档分析

### 1.1 文档概况

| 项目 | 内容 |
|------|------|
| 源文件 | `SPI2AXI SPEC.pdf` |
| 页数 | 7 页 |
| 文件大小 | 1,663,496 bytes |
| 提取图片 | 10 张 |
| 语言 | 中文 |

### 1.2 内容结构

| 页码 | 主要内容 | 关键图示 |
|------|---------|---------|
| Page 1 | 概述、IP主要特性(SPI接口/AXI Lite/跨时钟域)、接口定义 | 接口框图 |
| Page 2 | SPI接口信号表、AXI主设备接口、写操作序列 | - |
| Page 3 | 读操作序列、可配置参数表(AXI_ADDR_WIDTH/AXI_DATA_WIDTH/AXI_ID_WIDTH/DUMMY_CYCLES)、应用场景、地址范围图 | 地址范围图 |
| Page 4 | 操作说明(8-bit操作码→32位地址→Dummy cycle→数据)、FSM状态机 | FSM状态图, FSM面积/带宽数据 |
| Page 5 | SPI命令操作码表、SPI侧寄存器设定 | 操作码表格, 寄存器表格 |
| Page 6 | QSPI写时序图、QSPI读时序图、Wrap操作支持说明 | QSPI时序图(写/读) |
| Page 7 | Wrap示例(Wrap=2, 地址序列'h100→'h104→'h100→'h104→...) | - |

### 1.3 关键信息提取

#### 1.3.1 SPI 接口信号

| 信号名称 | 方向 | 描述 |
|---------|------|------|
| spi_sclk | 输入 | SPI 串行时钟, 50MHz |
| spi_cs | 输入 | SPI 片选信号（低有效） |
| spi_sdi[3:0] | 输入 | SPI 数据输入线 |
| spi_sdo[3:0] | 输出 | SPI 数据输出线 |

#### 1.3.2 AXI4-Lite 主设备接口

五个独立通道: AW(写地址), AR(读地址), W(写数据), R(读数据), B(写响应)

#### 1.3.3 可配置参数

| 参数 | 默认值 | 描述 |
|------|--------|------|
| AXI_ADDR_WIDTH | 32 | AXI 地址总线宽度 |
| AXI_DATA_WIDTH | 32 | AXI 数据总线宽度 |
| AXI_ID_WIDTH | 3 | AXI ID 信号宽度 |
| DUMMY_CYCLES | 32 | SPI 读操作虚拟周期数(实际 = 配置值 + 1) |

#### 1.3.4 操作流程

**写操作序列:**
1. （可选）配置 SPI 参数（1线或者4线模式）
2. SPI 主机发送写命令和地址
3. 控制器解析命令并同步到 AXI 时钟域
4. AXI 桥接发起写地址事务
5. 通过 FIFO 传输写数据
6. 等待 AXI 写响应完成

**读操作序列:**
1. （可选）配置 SPI 参数（1线或者4线模式）
2. SPI 主机发送读命令和地址
3. 控制器同步读请求到 AXI 时钟域
4. AXI 桥接发起读地址事务
5. 从 AXI 总线读取数据到 TX FIFO
6. 通过 SPI 接口返回读取的数据

#### 1.3.5 Wrap 操作

| 参数 | 说明 |
|------|------|
| Wrap = 0 | 无环绕功能 |
| Wrap = N | 环绕窗口为 N 个字(4×N 字节)，起始地址4字节对齐，每次+4，到第N个字后回绕 |

示例(Wrap=2, 起始地址'h100):
```
Burst 0: Write to 'h100
Burst 1: Write to 'h104
Burst 2: Write to 'h100 (回绕)
Burst 3: Write to 'h104
Burst 4: Write to 'h100
```

---

## 2. 章节划分与输出需求

### 2.1 输出文档章节 (基于 14-Chapter LLD 模板)

| # | 章节 | 内容要点 | 来源 |
|---|------|---------|------|
| 1 | 模块概述 (Module Overview) | 功能描述、应用场景(SOC调试/固件更新/芯片测试)、关键特性 | Page 1, Page 3 |
| 2 | 接口定义 (Interface Definition) | SPI/QSPI 信号表及波形、AXI4-Lite 五通道信号表、时钟/复位、cycle-level 时序图 | Page 1-2, 图示(PDF) |
| 3 | 子模块划分 (Sub-Module Partition) | SPI Slave、命令解码器FSM、异步FIFO(dual-clock)、AXI Master、配置寄存器、Wrap控制器 | Page 1-3 |
| 4 | 状态机设计 (FSM Design) | 命令解码FSM: 状态编码+转移矩阵+输出解码, SPI操作码到AXI事务的映射 | Page 4, 图示(FSM) |
| 5 | 流水线设计 (Pipeline Design) | SPI命令接收→CDC同步→AXI事务发起→响应返回的流水线 | Page 2-3, 操作序列 |
| 6 | 数据通路 (Datapath) | SPI串行→并行转换、FIFO深度/宽度、AXI数据通道宽度(32-bit) | Page 4 |
| 7 | 配置寄存器 (CSR) | SPI侧寄存器: 操作码编码表(READ/WRITE/REG_READ/REG_WRITE)、Wrap配置寄存器、状态寄存器 | Page 5, 图示(寄存器表) |
| 8 | 时钟与复位 (Clock & Reset) | SPI时钟域(50MHz)与AXI时钟域独立、dual-clock FIFO CDC、异步复位同步释放 | Page 1 |
| 9 | 时序约束 (SDC) | create_clock(spi_sclk/axi_clk)、输入延迟(spi_sdi)、输出延迟(spi_sdo)、CDC false path | Page 1-2 |
| 10 | 地址环绕 (Wrap) | Wrap功能设计: 地址计数器、环绕边界检测、地址计算逻辑 | Page 6-7 |
| 11 | 验证计划 (Verification) | 功能验证(SPI读/写/QSPI/Wrap)、时序验证(CDC)、覆盖率 | 待补充 |
| 12 | DFT 设计 | 扫描链插入、测试模式、ATE 测试 | 待补充 |
| 13 | 交付物 | RTL代码、SDC、验证环境(testbench)、文档 | - |
| 14 | 修订历史 | 版本记录 | - |

### 2.2 需要补充的内容

以下内容在 PDF 中以图示形式存在，需要补充结构化的文字描述:

1. **Page 1 接口框图** - 模块级端口连接、时钟域划分
2. **Page 3 地址范围图** - SoC 配置空间地址映射
3. **Page 4 FSM 状态图** - 状态编码、转移条件、输出信号
4. **Page 4 FSM 面积/带宽图表** - 性能评估数据
5. **Page 5 SPI 操作码表** - 完整操作码编码、命令类型、数据格式
6. **Page 5 寄存器表** - 寄存器偏移地址、位域定义、读写属性
7. **Page 6 QSPI 写时序图** - 4线SPI写操作的 cycle-level 波形
8. **Page 6 QSPI 读时序图** - 4线SPI读操作的 cycle-level 波形(含Dummy周期)

---

## 3. 设计约束

### 3.1 技术参数

| 参数 | 值 |
|------|-----|
| SPI 时钟频率 | 50 MHz |
| AXI 协议 | AXI4-Lite |
| AXI 地址宽度 | 32-bit (可配) |
| AXI 数据宽度 | 32-bit (可配) |
| AXI ID 宽度 | 3-bit (可配) |
| AXI Burst 类型 | Fixed (AxLEN=0, single transfer) |
| Dummy Cycles | 32 (可配, 实际=配置值+1) |

### 3.2 应用场景

- 系统调试和配置接口
- 低引脚数系统总线扩展
- 嵌入式系统固件更新
- 芯片测试和验证接口

---

## 4. 输出文件清单

### 4.1 本次规划阶段输出

| 文件 | 路径 | 状态 |
|------|------|------|
| 源文档转换 | `1.planning/source_spec.md` | 已完成 |
| 图片提取 | `1.planning/images/` (10 张) | 已完成 |
| 规划配置 | `1.planning/planning.yml` | 已完成 |
| 规划报告 | `1.planning/planning_report.md` | 已完成 |

### 4.2 后续阶段预期输出

| 阶段 | 预期输出 |
|------|---------|
| 2.slice | 切片分析文档、图片分割分析 |
| 3.working | 模块架构HLD、微架构LLD、多版本迭代 |
| 4.result | 最终HLD/LLD文档(HTML), 规范文档 |
