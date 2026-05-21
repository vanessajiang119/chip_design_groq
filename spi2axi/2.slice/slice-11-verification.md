---
source: SPI2AXI SPEC.pdf
page: N/A
chapter: verification
tags: [verification, test-plan]
status: 待补充
---

# 验证计划 (Verification Plan)

**状态**: 待补充 — 源文档未包含验证计划章节。需根据SPI2AXI IP功能特性补充验证点。

## 建议验证点

### 功能验证
- SPI标准模式(1线)读写操作
- QSPI模式(4线)读写操作
- 所有支持的操作码(READ/WRITE/REG_READ/REG_WRITE)
- AXI4-Lite 5通道握手协议
- 地址环绕功能(Wrap=0, Wrap=2, Wrap=N)
- 跨时钟域数据传输正确性
- 配置寄存器读写

### 时序验证
- SPI时钟最高频率(50MHz)下的建立/保持时间
- AXI接口时序满足AXI4-Lite规范
- 异步FIFO CDC路径的同步正确性

### 异常场景
- SPI传输中途片选异常拉高
- AXI Slave响应错误(PSLVERR/DECERR)
- 同时发起读写请求时FIFO满/空状态处理
