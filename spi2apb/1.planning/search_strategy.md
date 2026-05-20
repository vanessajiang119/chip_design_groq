# 搜索策略文档 — SPI2APB Bridge IP

> 生成日期: 2026-05-20
> 目标: 为 QSPI-to-APB bridge IP 设计提供技术参考

---

## 研究方向总览

| 方向 | 研究重点 | 优先级 | 关联模块 |
|------|---------|--------|---------|
| QSPI 协议 | 命令格式、时序约束、200MHz 接口要求 | P0 | qspi_slave, cmd_decoder |
| APB 2.0 协议 | PSLVERR/PREADY 握手、40bit 地址/128bit 数据 | P0 | apb_master |
| SPI2APB bridge 架构 | 参考设计、CDC 方案、地址映射策略 | P0 | 所有模块 |

---

## Round 1: 架构设计与业界方案

### 关键词
- 中文: "QSPI 从机设计", "APB 2.0 协议规范", "SPI to APB bridge 设计", "Quad SPI 时序"
- English: "QSPI slave design Verilog", "APB 2.0 protocol specification", "SPI to APB bridge architecture", "Quad SPI timing 200MHz"

### 搜索源优先级
1. web_search — 通用网络搜索获取协议规范和设计参考
2. vendor_docs — ARM APB 2.0 规范、SPI 控制器厂商文档

### 推荐搜索方向
- QSPI 协议标准: READ (0x03), FAST_READ (0x0B), Quad Output (0x6B), Quad IO (0xEB) 命令格式
- APB 2.0 规范: 状态机 (IDLE/SETUP/ACCESS), PREADY 握手, PSLVERR 响应
- SPI2APB bridge 业界参考实现: OpenCores/开源项目

---

## Round 2: 关键模块微架构细节

### 关键词
- 中文: "异步 FIFO 跨时钟域桥接", "QSPI 命令解码器 FSM", "APB master 状态机设计", "CDC 同步器"
- English: "async FIFO CDC design", "SPI command decoder FSM", "APB master state machine", "dual clock FIFO"

### 搜索源优先级
1. web_search — 微架构设计参考
2. github — 开源 Verilog/SystemVerilog 设计实例

### 推荐搜索方向
- 异步 FIFO: 双端口 RAM + 格雷码指针同步, 深度选择策略
- 命令解码器 FSM: SPI 命令解析状态机设计
- APB master: 标准 APB 2.0 master 状态机实现

---

## Round 3: 验证与实现参考

### 关键词
- 中文: "SPI 验证 UVM", "APB 验证 sequence", "QSPI 断言检查", "覆盖率驱动验证"
- English: "SPI UVM verification", "APB protocol checker", "QSPI assertion", "functional coverage SPI"

### 搜索源优先级
1. web_search — 验证方法学
2. github — 验证测试平台代码

### 推荐搜索方向
- UVM testbench for SPI/APB
- SystemVerilog assertion for SPI protocol
- 功能覆盖点: SPI 命令覆盖率, APB 传输覆盖率
