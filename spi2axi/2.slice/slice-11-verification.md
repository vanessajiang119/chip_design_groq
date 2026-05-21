<!-- Source: source_raw.md 第1-7页, source_spec.md 第2-8章 -->
<!-- Chapter: 验证方案 (Verification) -->

# 验证方案 (Verification)

## 概述

**待补充** — 本章为验证方案框架，需要根据具体验证计划细化。以下仅为建议的验证策略框架。

## 验证层次

SPI2AXI Bridge 的验证可在以下层次进行：

| 验证层次 | 范围 | 方法 |
|---|---|---|
| **模块级 (Module Level)** | 单个子模块验证 | 定向测试 + UVM 或 Verilog testbench |
| **集成级 (Integration Level)** | SPI2AXI 顶层模块 | 系统级测试序列 |
| **SoC 级 (SoC Level)** | SPI2AXI + 系统总线 | 端到端 FPGA 原型验证 |

## 验证功能点

### 1. SPI 接口功能
- 标准 SPI（1-wire）模式下的命令接收和数据收发
- QSPI（4-wire）模式下的命令接收和数据收发
- SPI 时钟频率范围测试（最大 50 MHz）
- 片选信号的有效/无效时序

### 2. AXI 接口功能
- AXI4-Lite 写事务（AW → W → B 协议握手）
- AXI4-Lite 读事务（AR → R 协议握手）
- AXI 地址/数据宽度配置测试

### 3. 跨时钟域 (CDC)
- 异步时钟域数据传输正确性
- FIFO 空/满标志功能
- CDC 同步可靠性和数据完整性

### 4. 命令解析
- 操作码编码解码正确性
- 地址接收和解析（32-bit）
- 寄存器访问 vs 内存访问路径区分

### 5. 读写操作序列
- 写操作全流程（SPI → CDC → AXI）
- 读操作全流程（SPI → CDC → AXI → CDC → SPI）
- 连续读写操作的正确性

### 6. Wrap 地址环绕
- Wrap = 0 行为
- Wrap 窗口大小 N 的有效性
- 地址自增和回绕正确性
- 地址 4 字节对齐限制

### 7. 虚拟周期 (Dummy Cycles)
- DUMMY_CYCLES 配置值和实际等待周期数
- 可编程范围测试

## 测试场景建议

| 测试编号 | 场景 | 描述 |
|---|---|---|
| T01 | SPI 写寄存器 | 标准 SPI 模式写寄存器 |
| T02 | SPI 读寄存器 | 标准 SPI 模式读寄存器 |
| T03 | SPI 写内存 | 标准 SPI 模式写内存（32-bit 地址） |
| T04 | SPI 读内存 | 标准 SPI 模式读内存（含 dummy cycles） |
| T05 | QSPI 写内存 | 四线 SPI 模式写内存 |
| T06 | QSPI 读内存 | 四线 SPI 模式读内存 |
| T07 | Wrap 地址回绕 | Wrap = 3 时连续写的地址序列 |
| T08 | CDC FIFO 满 | SPI 连续写，AXI 时钟较慢时 FIFO 满行为 |
| T09 | 并发读写 | AXI 处理中 SPI 收到新命令 |
| T10 | 复位行为 | 各模块在复位时的行为和状态 |

## 覆盖率目标

**待补充** — 建议覆盖率目标：
- 代码覆盖率 (Code Coverage): ≥ 90%
- 功能覆盖率 (Functional Coverage): ≥ 95%
- 状态机覆盖率 (FSM Coverage): 100%
