---
source: SPI2AXI SPEC.pdf
page: 1, 3
chapter: overview
tags: [overview, features, application]
---

# 模块概述 (Module Overview)

## 功能描述

SPI2AXI IP是一个将SPI从设备接口转换为AXI主设备接口的桥接模块，允许通过SPI总线访问AXI总线上的存储器和外设。因为SPI是一个通用数字接口，SPI2AXI可以在桌面PC上使用，方便pattern的调试和实验室的bringup和debug。

## IP主要特性

- **SPI接口**：支持标准SPI和四线SPI(QSPI)两种工作模式
- **SPI Slave 模式**：作为主动外设（active peripheral），无需 SoC 内部 CPU 干预即可完成SOC功能配置，状态观测等功能
- **AXI Lite 接口**：将 SPI 侧接收到的命令/数据转换成 AXI 事务
- **AXI 总线访问**：通过 AXI Lite 接口访问 SoC 的内存和外设
- **跨时钟域处理**：SPI时钟域与AXI时钟域分离
- **双时钟 FIFO**：内置 dual-clock FIFOs，实现从 SPI 时钟域到 SoC AXI 时钟域之间的可靠跨时钟域传输（CDC）

## 应用场景

- 系统调试和配置接口
- 低引脚数系统总线扩展
- 嵌入式系统固件更新
- 芯片测试和验证接口

这是一个SPI slave的实现版本。该SPI从机可被外部微控制器用于访问相关数据。SPI从机通过AXI总线来访问目标设备的配置空间和内存。SoC配备了双时钟FIFO缓存器，用于实现从SPI频率域到SoC（AXI）频率域的时钟域转换。

在S3中，SPI2AXI用于访问config配置空间。

![SPI2AXI 系统架构图](images/page1_img0.png)
<!-- Page 1: SPI2AXI system block diagram showing SPI slave to AXI master bridge architecture -->

![SPI2AXI 地址范围映射](images/page3_img0.png)
<!-- Page 3: SPI2AXI address range mapping for config space access in S3 subsystem -->
