---
source: SPI2AXI SPEC.pdf
page: 2-3
chapter: pipeline
tags: [pipeline, write-sequence, read-sequence, operation-flow]
---

# 流水线设计 (Pipeline Design)

## 写操作序列

1. （可选）配置 SPI 参数（1线或者4线模式）
2. SPI主机发送写命令和地址
3. 控制器解析命令并同步到AXI时钟域
4. AXI桥接发起写地址事务
5. 通过FIFO传输写数据
6. 等待AXI写响应完成

## 读操作序列

1. （可选）配置 SPI 参数（1线或者4线模式）
2. SPI主机发送读命令和地址
3. 控制器同步读请求到AXI时钟域
4. AXI桥接发起读地址事务
5. 从AXI总线读取数据到TX FIFO
6. 通过SPI接口返回读取的数据

## 操作流水线阶段

SPI命令→AXI事务的转换流水线包含以下阶段:

| 阶段 | 时钟域 | 描述 |
|------|--------|------|
| SPI 命令接收 | SPI (50MHz) | 接收操作码+地址+数据，SPI串并转换 |
| 命令解码 | SPI (50MHz) | 解析命令类型，生成控制信号 |
| CDC 同步 | 跨时钟域 | 通过异步FIFO同步到AXI时钟域 |
| AXI 总线事务 | AXI | 发起AXI4-Lite读写事务 |
| 数据返回 | AXI → SPI | 读数据经FIFO返回SPI侧输出 |
