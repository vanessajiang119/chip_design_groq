---
source: SPI2AXI SPEC.pdf
page: 4
chapter: fsm
tags: [fsm, state-machine, cmd-decoder]
---

# 状态机设计 (FSM Design)

## 操作流程帧格式

要从内存/寄存器中读取和写入数据，需要采用以下方案。首先，主设备必须发送一个8位的操作码（opcode）。如果要访问内存，则接下来必须跟随一个32位的地址（最高有效位在前）。寄存器的地址由操作码进行编码。

在从内存读取数据的情况下，接下来必须插入32（可编程）个cycle以等待读数据返回。最后，实际数据将在最后的32位中传输（MSB first）。

该从属控制器基于下图所示的有限状态机:

![SPI2AXI 状态转移图 - 操作码格式](images/page4_img0.png)
<!-- Page 4: SPI command frame format - opcode, address, dummy cycles, data fields -->

![SPI2AXI FSM 状态图](images/page4_img1.png)
<!-- Page 4: FSM state diagram showing IDLE → OPCODE → ADDR → DUMMY → DATA → RESPONSE state transitions -->

## 状态转移

FSM的基本状态包括:
- **IDLE**: 空闲状态，等待SPI片选
- **OPCODE**: 接收8-bit操作码，解码命令类型
- **ADDR**: 接收32-bit地址（MSB first），内存访问时需要
- **DUMMY**: 插入可编程数量的虚拟周期，等待读数据返回
- **DATA**: 数据传输阶段，32-bit数据（MSB first）
- **RESPONSE**: 写响应处理或读数据返回
