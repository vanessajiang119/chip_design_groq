<!-- Source: source_raw.md 第1-2页, source_spec.md 第3.3节 -->
<!-- Chapter: 时钟与复位 (Clock & Reset) -->

# 时钟与复位 (Clock & Reset)

## 时钟域划分

SPI2AXI Bridge 包含两个独立的时钟域：

| 时钟域 | 时钟信号 | 时钟频率 | 描述 |
|---|---|---|---|
| **SPI 时钟域** | `spi_sclk` | 50 MHz (max) | SPI 串行时钟，由 SPI 主机提供 |
| **AXI 时钟域** | `axi_aclk` | 待定 (取决于 SoC 配置) | AXI 系统时钟，由 SoC 提供 |

## 跨时钟域处理 (CDC)

### 设计策略
- SPI 时钟域与 AXI 时钟域完全分离，时钟频率可不同
- 使用 **dual-clock FIFOs（双时钟 FIFO）** 实现跨时钟域数据传输
- 写时钟域 = SPI 时钟域，读时钟域 = AXI 时钟域（反之亦然，取决于数据流向）

### CDC FIFO 配置
| FIFO 名称 | 写时钟 | 读时钟 | 数据流向 |
|---|---|---|---|
| cmd_fifo | spi_sclk | axi_aclk | SPI → AXI |
| wdata_fifo | spi_sclk | axi_aclk | SPI → AXI |
| rdata_fifo | axi_aclk | spi_sclk | AXI → SPI |

### CDC 同步机制
- 使用 dual-clock FIFO 内置的同步器（通常为两级或三级同步链）
- 空/满标志的同步使用格雷码 (Gray Code) 指针
- 防止亚稳态传播，保证跨时钟域数据传输的可靠性

## 复位策略

| 复位信号 | 时钟域 | 极性 | 描述 |
|---|---|---|---|
| `spi_rst_n` | SPI 时钟域 | 低有效 | SPI 域异步复位 |
| `axi_areset_n` | AXI 时钟域 | 低有效 | AXI 域异步复位 |

- 建议使用 **异步复位，同步释放** 的复位同步器
- 两个时钟域应分别拥有独立的复位信号
- SPI 域复位：复位 SPI 接口逻辑、SPI 侧寄存器
- AXI 域复位：复位 AXI 主接口逻辑、AXI 侧寄存器
- CDC FIFO 通常需要两个时钟域都复位才能正确初始化
