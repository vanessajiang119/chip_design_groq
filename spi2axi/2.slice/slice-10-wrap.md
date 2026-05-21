---
source: SPI2AXI SPEC.pdf
page: 6-7
chapter: wrap
tags: [wrap, address-wrapping, burst]
---

# 地址环绕 (Address Wrap)

## Wrap 功能概述

SPI2AXI 模块支持 AXI4-Lite 协议。由于 AXI4-Lite 仅支持单次传输（single transfer），每个 burst 长度固定为 1，即 AxLEN = 0，且通常配置为 AxSIZE = 2（表示每次传输 1 个 32-bit 字，即 4 字节）。

SPI2AXI 引入了可配置的地址 Wrap 功能：

- **Wrap = 0**: 无环绕功能，地址持续递增
- **Wrap = N (N > 0)**: 启用地址环绕模式，环绕窗口大小为 N 个字（word），即 4×N 字节
  - 起始地址必须按 4 字节对齐（因 AxSIZE=2）
  - 地址从起始地址开始，每次传输后地址 +4（下一个 word）
  - 当访问完第 N 个 word 后，自动回绕到起始地址

## Wrap 示例

若 Wrap = 2，起始地址为 'h100（4-byte 对齐），则连续写操作的地址序列为：

| Burst | 地址 | 说明 |
|-------|------|------|
| Burst 0 | 'h100 | 第 1 个 word |
| Burst 1 | 'h104 | 第 2 个 word |
| Burst 2 | 'h100 | 回绕，重新从第 1 个 word 开始 |
| Burst 3 | 'h104 | 第 2 个 word |
| Burst 4 | 'h100 | 回绕，重新从第 1 个 word 开始 |

## QSPI 时序

![QSPI 写时序图](images/page6_img0.png)
<!-- Page 6: QSPI write timing diagram - 4-line mode, command/address/data phases -->

![QSPI 读时序图](images/page6_img1.png)
<!-- Page 6: QSPI read timing diagram - 4-line mode, with dummy cycles -->

![QSPI 时序图](images/page6_img2.png)
<!-- Page 6: QSPI timing details - signal relationships and timing parameters -->
