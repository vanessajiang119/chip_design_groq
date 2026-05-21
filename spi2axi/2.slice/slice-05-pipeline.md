<!-- Source: source_raw.md 第2-3页, source_spec.md 第6章 -->
<!-- Chapter: 流水线 (Pipeline) -->

# 流水线 (Pipeline)

## 概述

SPI2AXI Bridge 作为 SPI 到 AXI 的桥接模块，处理流程为串行执行模式（非流水线），每次处理一个 SPI 事务，将其转换为对应的 AXI 事务。由于 AXI4-Lite 仅支持 single transfer，整体流程以事务为基本单元顺序执行。

## 写操作流水线

写操作序列步骤：

1. **(可选) 配置 SPI 参数** — 配置 1-wire 或 4-wire 工作模式
2. **SPI 主机发送写命令和地址** — 通过 SPI 发送操作码 + 32-bit 地址
3. **控制器解析命令并同步到 AXI 时钟域** — 通过 CDC FIFO 跨时钟域传输
4. **AXI 桥接发起写地址事务** — AXI AW 通道发送写地址
5. **通过 FIFO 传输写数据** — AXI W 通道发送写数据
6. **等待 AXI 写响应完成** — AXI B 通道接收写响应

### 写操作阶段示意图

```
SPI Domain:  [Opcode] → [Address] → [WData] ──┐
                                                ↓
CDC FIFO:                            ┌─── cmd_fifo ───┐
                                     └─── wdata_fifo ─┘
                                                ↓
AXI Domain:              [AW Addr] → [W Data] → [B Resp]
```

## 读操作流水线

读操作序列步骤：

1. **(可选) 配置 SPI 参数** — 配置 1-wire 或 4-wire 工作模式
2. **SPI 主机发送读命令和地址** — 通过 SPI 发送操作码 + 32-bit 地址
3. **控制器同步读请求到 AXI 时钟域** — 通过 CDC FIFO 跨时钟域传输
4. **AXI 桥接发起读地址事务** — AXI AR 通道发送读地址
5. **从 AXI 总线读取数据到 TX FIFO** — AXI R 通道接收读数据
6. **通过 SPI 接口返回读取的数据** — 将数据通过 SPI 发送回主机

### 读操作阶段示意图

```
SPI Domain:  [Opcode] → [Address] → [Dummy Cycles] ──┐
                                                       ↓
CDC FIFO:                              ┌─── cmd_fifo ───┐
                                       └─── rdata_fifo ─┘
                                                       ↓
AXI Domain:              [AR Addr] → [R Data] → (to rdata_fifo)
```

## 流水线深度

- 整体流水线深度为 **1**（每个事务串行执行）
- CDC FIFO 提供必要的缓冲，但不增加流水线深度
- 多个连续 SPI 事务之间可衔接，下一事务的地址可在当前事务完成前开始接收
