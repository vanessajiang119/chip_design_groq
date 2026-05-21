<!-- Source: source_raw.md 第1-3页, source_spec.md 第1-2章 -->
<!-- Chapter: 模块概述 (Module Overview) -->

# 模块概述 (Module Overview)

## 模块名称
**SPI2AXI Bridge** — SPI Slave to AXI4-Lite Master 桥接模块

## 功能描述
SPI2AXI IP 是一个将 **SPI 从设备接口 (SPI Slave)** 转换为 **AXI 主设备接口 (AXI Master)** 的桥接模块，允许通过 SPI 总线访问 AXI 总线上的存储器和外设。

SPI是一个通用数字接口，SPI2AXI可以在桌面PC上使用，方便pattern的调试和实验 室的bringup和debug。

## IP 主要特性

### SPI 接口
- 支持 **标准 SPI (Standard SPI)** 和 **四线 SPI / QSPI (Quad SPI)** 两种工作模式
- **SPI Slave** 作为主动外设（active peripheral），无需 SoC 内部 CPU 干预即可完成 SOC 功能配置、状态观测等功能

### AXI Lite 接口
- 将 SPI 侧接收到的命令/数据转换成 AXI 事务
- 通过 AXI Lite 接口访问 SoC 的内存和外设

### 跨时钟域处理
- SPI 时钟域与 AXI 时钟域分离
- 内置 **dual-clock FIFOs（双时钟 FIFO）**，实现从 SPI 时钟域到 SoC AXI 时钟域之间的可靠跨时钟域传输（CDC）

### Wrap 地址环绕功能
- 支持可配置的地址 Wrap 功能（详见 slice-10-wrap.md）

## 系统架构

![SPI2AXI 系统架构图](images/page1_img0.png)
<!-- 第1页图片：SPI2AXI Bridge 系统级架构图，展示 SPI Slave 侧（左）经双时钟 FIFO 桥接到 AXI Master 侧（右）的连接关系 -->

## 应用场景
- 系统调试和配置接口 (System debug and configuration interface)
- 低引脚数系统总线扩展 (Low pin-count system bus expansion)
- 嵌入式系统固件更新 (Embedded system firmware update)
- 芯片测试和验证接口 (Chip test and verification interface)
- SoC config 配置空间访问

### SoC 中的应用
SPI2AXI 是一个 SPI slave 的实现版本。该 SPI 从机可被外部微控制器用于访问相关数据。SPI 从机通过 AXI 总线来访问目标设备的配置空间和内存。SoC 配备了双时钟 FIFO 缓存器，用于实现从 SPI 频率域到 SoC（AXI）频率域的时钟域转换。

在 S3 中，SPI2AXI 用于访问 config 配置空间。地址范围如下图标注：

![SoC 地址范围图](images/page3_img0.png)
<!-- 第3页图片：SPI2AXI 在 S3 SoC 系统中的地址空间映射图，展示 config 配置空间的地址范围 -->

## AXI4-Lite 协议说明
- 仅支持单次传输（single transfer），每个 burst 长度固定为 1，即 AxLEN = 0
- 通常配置为 AxSIZE = 2，表示每次传输 1 个 32-bit word（4 字节）
