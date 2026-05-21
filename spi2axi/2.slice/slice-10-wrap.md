<!-- Source: source_raw.md 第6-7页, source_spec.md 第3.4节, 第8.1节 -->
<!-- Chapter: Wrap 操作支持 (Wrap Support) -->

# Wrap 操作支持 (Wrap Support)

## 概述

SPI2AXI 模块支持 AXI4-Lite 协议。由于 AXI4-Lite 仅支持单次传输（single transfer），每个 burst 长度固定为 1，即 AxLEN = 0，且通常配置为 AxSIZE = 2（表示每次传输 1 个 32-bit 字，即 4 字节），因此无法利用 AXI 的 burst 特性进行连续地址访问。

SPI2AXI 引入了 **可配置的地址 Wrap 功能**，在 AXI4-Lite 的约束下模拟连续的地址环绕访问。

## Wrap 功能配置

| 配置值 | 行为 |
|---|---|
| **Wrap = 0** | 无环绕功能，每次访问地址为 SPI 主机指定的地址 |
| **Wrap = N (N > 0)** | 启用地址环绕模式，环绕窗口大小为 N 个字（word），即 4×N 字节 |

## Wrap 地址计算规则

- **起始地址**：必须按 4 字节对齐（因 AxSIZE = 2）
- **地址递增**：从起始地址开始，每次传输后地址 +4（下一个 word）
- **回绕条件**：当访问完第 N 个 word 后，自动回绕到起始地址
- **循环**：回绕后继续地址递增，形成循环访问模式

### 地址序列示例

若 Wrap = 2，起始地址为 'h100（4-byte 对齐），则连续写操作的地址序列为：

| Burst | 地址 | 说明 |
|---|---|---|
| Burst 0 | 'h100 | 第 1 个 word |
| Burst 1 | 'h104 | 第 2 个 word |
| Burst 2 | 'h100 | 回绕，重新从第 1 个 word 开始 |
| Burst 3 | 'h104 | 第 2 个 word |
| Burst 4 | 'h100 | 回绕，重新从第 1 个 word 开始 |

## Wrap 时序图

![QSPI 写时序](images/page6_img0.png)
<!-- 第6页图片：QSPI 写操作时序图，展示 QSPI 模式下 4-bit 数据线同时传输写命令、地址、数据的时序 -->

![QSPI 读时序](images/page6_img1.png)
<!-- 第6页图片：QSPI 读操作时序图，展示 QSPI 模式下 4-bit 数据线同时传输读命令、地址、虚拟周期和返回读数据的时序 -->

![Wrap 操作支持示意图](images/page6_img2.png)
<!-- 第6页另一张图片：Wrap 操作支持示意图，展示地址环绕模式的地址序列和循环行为 -->
