<!-- Source: source_raw.md 第2页, source_spec.md 第4章 -->
<!-- Chapter: 接口定义 (Interface Definition) -->

# 接口定义 (Interface Definition)

## SPI 接口信号

| 信号名称 | 方向 (Direction) | 描述 (Description) |
|---|---|---|
| `spi_sclk` | Input | SPI 串行时钟，50 MHz |
| `spi_cs` | Input | SPI 片选信号，低有效 (Active Low) |
| `spi_sdi[3:0]` | Input | SPI 数据输入线（支持 1-wire 或 4-wire 模式） |
| `spi_sdo[3:0]` | Output | SPI 数据输出线（支持 1-wire 或 4-wire 模式） |

### SPI 接口说明
- `spi_sclk`：由 SPI 主机提供的串行时钟，最高频率 50 MHz
- `spi_cs`：片选信号，低电平有效，用于启动和结束 SPI 事务
- `spi_sdi[3:0]`：数据输入，标准 SPI 模式下仅使用 `spi_sdi[0]`（1-bit），QSPI 模式下使用全部 4-bit
- `spi_sdo[3:0]`：数据输出，标准 SPI 模式下仅使用 `spi_sdo[0]`（1-bit），QSPI 模式下使用全部 4-bit

## AXI 主设备接口

**AXI4-Lite** 主设备接口 (Master Interface)，包含 5 个独立通道：

| 通道 (Channel) | 方向 | 描述 (Description) |
|---|---|---|
| **写地址通道 (AW)** | Master→Slave | AWADDR, AWVALID, AWREADY, AWPROT |
| **写数据通道 (W)** | Master→Slave | WDATA, WSTRB, WVALID, WREADY |
| **写响应通道 (B)** | Slave→Master | BRESP, BVALID, BREADY |
| **读地址通道 (AR)** | Master→Slave | ARADDR, ARVALID, ARREADY, ARPROT |
| **读数据通道 (R)** | Slave→Master | RDATA, RRESP, RVALID, RREADY |

### AXI4-Lite 特性
- 仅支持 **single transfer**，burst 长度固定为 1（AxLEN = 0）
- AxSIZE 通常配置为 2（32-bit / 4-byte）
- 不支持 AXI4 的 burst、locked 事务、cached 或 protection unit 等高级特性
- 简化了地址通道握手协议
