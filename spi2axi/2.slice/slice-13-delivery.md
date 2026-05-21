<!-- Source: source_raw.md 第1-7页, source_spec.md 第1章 -->
<!-- Chapter: 交付物 (Delivery) -->

# 交付物 (Delivery)

## 概述

**待补充** — 本章列出了 SPI2AXI Bridge IP 的完整交付物清单，根据项目进展逐步完善。

## RTL 交付物

| 序号 | 交付物 | 描述 | 状态 |
|---|---|---|---|
| 1 | `spi2axi_top.v` | 顶层模块（模块实例化和互联） | 待完成 |
| 2 | `spi_slave_if.v` | SPI 从设备接口模块 | 待完成 |
| 3 | `cdc_fifo.v` | 双时钟域 FIFO 模块 | 待完成 |
| 4 | `axi_master_if.v` | AXI4-Lite 主接口模块 | 待完成 |
| 5 | `wrap_addr_gen.v` | Wrap 地址生成器 | 待完成 |
| 6 | `csr_regfile.v` | 配置寄存器文件 | 待完成 |
| 7 | `fsm_ctrl.v` | 主状态机控制器 | 待完成 |

## 验证交付物

| 序号 | 交付物 | 描述 | 状态 |
|---|---|---|---|
| 1 | `spi2axi_tb.v` | 模块级测试平台 | 待完成 |
| 2 | `spi2axi_test_seq.v` | 测试序列定义 | 待完成 |
| 3 | `spi2axi_coverage.v` | 覆盖率收集 | 待完成 |
| 4 | 验证报告 | 功能覆盖率和代码覆盖率报告 | 待完成 |

## 约束与脚本

| 序号 | 交付物 | 描述 | 状态 |
|---|---|---|---|
| 1 | `spi2axi.sdc` | Synopsys Design Constraints | 待完成 |
| 2 | `spi2axi.tcl` | 综合脚本 | 待完成 |
| 3 | `spi2axi_dft.tcl` | DFT 扫描链插入脚本 | 待完成 |
| 4 | `spi2axi_sta.tcl` | STA 时序分析脚本 | 待完成 |

## 文档交付物

| 序号 | 交付物 | 描述 | 状态 |
|---|---|---|---|
| 1 | `SPI2AXI_Arch_HLD.md` | 架构设计文档（HLD） | 待完成 |
| 2 | `SPI2AXI_Micro_LLD.md` | 微架构设计文档（LLD） | 待完成 |
| 3 | `SPI2AXI_Design_Spec.md` | 设计规格说明书 | 待完成 |
| 4 | `SPI2AXI_User_Guide.md` | 用户使用指南（含寄存器描述） | 待完成 |

## 交付物树形结构

```
spi2axi/
├── rtl/
│   ├── spi2axi_top.v
│   ├── spi_slave_if.v
│   ├── cdc_fifo.v
│   ├── axi_master_if.v
│   ├── wrap_addr_gen.v
│   ├── csr_regfile.v
│   └── fsm_ctrl.v
├── tb/
│   ├── spi2axi_tb.v
│   └── spi2axi_test_seq.v
├── scripts/
│   ├── spi2axi.sdc
│   ├── spi2axi.tcl
│   ├── spi2axi_dft.tcl
│   └── spi2axi_sta.tcl
└── doc/
    ├── SPI2AXI_Arch_HLD.md
    ├── SPI2AXI_Micro_LLD.md
    ├── SPI2AXI_Design_Spec.md
    └── SPI2AXI_User_Guide.md
```
