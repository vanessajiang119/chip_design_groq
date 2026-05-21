---
source: SPI2AXI SPEC.pdf
page: 1, 6
chapter: sdc
tags: [sdc, timing-constraints, cdc-constraint]
---

# 时序约束 (SDC Constraints)

## 时钟定义

SPI2AXI IP包含两个异步时钟域，需要分别定义时钟约束：

### SPI 时钟约束
- SPI时钟由外部Master提供，频率最高50MHz
- 创建输入时钟约束：`create_clock -name spi_sclk -period 20.0 [get_ports spi_sclk]`

### AXI 时钟约束
- AXI时钟由SoC系统时钟提供
- 创建时钟约束：`create_clock -name axi_aclk -period 10.0 [get_ports axi_aclk]`（假设100MHz）

## 输入/输出延迟约束

SPI输入信号（spi_sdi, spi_cs）需要相对于spi_sclk设置输入延迟约束：
- `set_input_delay -clock spi_sclk -max 5.0 [get_ports spi_sdi*]`
- `set_input_delay -clock spi_sclk -min 1.0 [get_ports spi_sdi*]`

SPI输出信号（spi_sdo）需要设置输出延迟约束：
- `set_output_delay -clock spi_sclk -max 5.0 [get_ports spi_sdo*]`
- `set_output_delay -clock spi_sclk -min 1.0 [get_ports spi_sdo*]`

## 跨时钟域约束

SPI时钟域到AXI时钟域之间的所有路径应设置为false path或使用set_clock_groups约束：
- `set_clock_groups -asynchronous -group [get_clocks spi_sclk] -group [get_clocks axi_aclk]`

## 异步FIFO约束

dual-clock FIFO内部使用格雷码同步器，其跨时钟域路径不应被STA工具分析：
- `set_false_path -from [get_clocks spi_sclk] -to [get_clocks axi_aclk]`
- `set_false_path -from [get_clocks axi_aclk] -to [get_clocks spi_sclk]`
