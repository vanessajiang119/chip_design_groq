<!-- Source: source_raw.md 第1-2页, source_spec.md 第3-4章 -->
<!-- Chapter: SDC约束 (SDC) -->

# SDC约束 (SDC)

## 概述

本章定义 SPI2AXI Bridge 的时序约束（Synopsys Design Constraints），用于综合和静态时序分析（STA）。内容为初步框架，需在 LLD 阶段根据具体时钟频率和设计参数细化。

## 时钟定义

```tcl
# SPI 时钟 - 由外部 SPI 主机提供
create_clock -name spi_sclk -period 20.0 [get_ports spi_sclk]

# AXI 时钟 - 由 SoC 提供 (假设 100MHz)
create_clock -name axi_aclk -period 10.0 [get_ports axi_aclk]
```

## 生成时钟

```tcl
# 如果内部有门控时钟或分频时钟，定义生成时钟
# (待补充 - 如果有内部时钟分频逻辑)
```

## 输入延迟约束

```tcl
# SPI 输入信号 (数据/片选) 相对于 spi_sclk 的输入延迟
set_input_delay -clock spi_sclk -max 5.0 [get_ports {spi_sdi[*] spi_cs}]
set_input_delay -clock spi_sclk -min 1.0 [get_ports {spi_sdi[*] spi_cs}]
```

## 输出延迟约束

```tcl
# SPI 输出信号相对于 spi_sclk 的输出延迟
set_output_delay -clock spi_sclk -max 5.0 [get_ports {spi_sdo[*]}]
set_output_delay -clock spi_sclk -min 1.0 [get_ports {spi_sdo[*]}]
```

## 跨时钟域约束

```tcl
# CDC FIFO 路径 - 设置为 false path，由 CDC 同步机制保证
set_false_path -from [get_clocks spi_sclk] -to [get_clocks axi_aclk]
set_false_path -from [get_clocks axi_aclk] -to [get_clocks spi_sclk]

# 异步复位信号的 false path
set_false_path -from [get_ports spi_rst_n] -to [get_clocks axi_aclk]
set_false_path -from [get_ports axi_areset_n] -to [get_clocks spi_sclk]
```

## 时钟分组

```tcl
# SPI 时钟域和 AXI 时钟域为异步关系
set_clock_groups -asynchronous -group [get_clocks spi_sclk] \
                                   -group [get_clocks axi_aclk]
```

## AXI 接口时序约束

```tcl
# AXI 接口时序约束假设 AXI 总线时序参数
# (待补充 - 需根据 SoC 集成环境的具体时序要求调整)
set_output_delay -clock axi_aclk -max 4.0 [all_outputs]
set_input_delay -clock axi_aclk -max 4.0 [all_inputs]
```

## 其他约束

```tcl
# 最大扇出/扇入约束
set_max_fanout 20 [current_design]
set_max_transition 0.5 [current_design]

# 线负载模式 (仅适用于较老工艺)
# set_wire_load_mode enclosed

# 面积约束 (可选)
# set_max_area 10000
```

**待补充** — 以上 SDC 约束为初始框架，需在 LLD/综合阶段根据以下因素细化：
- 实际 `axi_aclk` 频率（待 SoC 集成确定）
- SPI 接口 IO 时序（具体封装的 IO buffer 延迟）
- AXI 总线接口的时序预算
- 工艺库的 transition/slew 限制
