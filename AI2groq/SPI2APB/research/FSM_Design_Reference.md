# SPI Slave + AXI4-Lite Master FSM Design Reference

> Research compilation for SPI2AXI bridge IP design.
> Sources include ESP32 hardware FSM documentation, airhdl spi-to-axi-bridge, efabless sky130 spi_slave, and AXI4-Lite protocol reference implementations.

---

## 1. SPI Slave Receiver FSM

### 1.1 State Definitions

The SPI slave receiver FSM decodes an incoming serial bitstream into commands, addresses, and data. Based on the ESP32 hardware SPI FSM and industrial SPI bridge designs, the canonical state set is:

| State   | Encoding (Binary) | Encoding (One-Hot) | Description |
|---------|------------------:|--------------------:|-------------|
| IDLE    | `3'b000`          | `8'b0000_0001`     | Waiting for chip select (CS_n) assertion |
| PREP    | `3'b001`          | `8'b0000_0010`     | Preparation cycle (optional, used for mode switching) |
| OPCODE  | `3'b010`          | `8'b0000_0100`     | Receiving the 8-bit command/opcode byte |
| ADDRESS | `3'b011`          | `8'b0000_1000`     | Receiving the 32-bit address (4 bytes) |
| DUMMY   | `3'b100`          | `8'b0001_0000`     | Dummy/wait cycles (for read operations or AXI latency) |
| DATA    | `3'b101`          | `8'b0010_0000`     | Transmitting (read) or receiving (write) 32-bit data |
| DONE    | `3'b110`          | `8'b0100_0000`     | Transaction complete, status byte output |

### 1.2 State Transition Table

```
Legend:
  CS_n   = Chip select (active low)
  SCK    = SPI clock (sampling edge determined by CPHA)
  bit_cnt = Internal bit counter (0..7 per byte)
  byte_cnt = Internal byte counter
  opcode = Decoded command (e.g., 8'h00 = write, 8'h01 = read)
  data_dir = Transaction direction (read = MOSI->MISO turnaround)
  status_rdy = AXI response received

Current State  | Condition                          | Next State | Actions
---------------|------------------------------------|------------|------------------------------------------
IDLE           | CS_n == 1'b0                       | PREP       | Reset bit_cnt, byte_cnt; enable SCK sampling
               | CS_n == 1'b1                       | IDLE       | Hold (deasserted)

PREP           | Always (1 cycle)                   | OPCODE     | Prepare shift register

OPCODE         | bit_cnt == 3'd7 && SCK_has_sampled | ADDRESS    | Latch opcode byte; decode r/w direction
               | CS_n == 1'b1 (any time)            | IDLE       | Abort; deassert

ADDRESS        | byte_cnt == 3 && bit_cnt == 7       | DUMMY      | Latch full 32-bit address; start AXI txn
               | bit_cnt == 7 (not last byte)        | ADDRESS    | Advance byte_cnt; continue shifting
               | CS_n == 1'b1 (any time)             | IDLE       | Abort

DUMMY          | opcode == READ && dummy_cnt == done | DATA       | Wait cycles for AXI read completion
               | opcode == WRITE                     | DATA       | Write may skip or have minimal dummy
               | CS_n == 1'b1                        | IDLE       | Abort

DATA           | opcode == WRITE && bit_cnt == 7 &&   | DONE       | Capture final write data byte
               |   byte_cnt == 3                      |            |
               | opcode == READ && bit_cnt == 7 &&   | DONE       | Final read data byte transmitted
               |   byte_cnt == 3                      |            |
               | bit_cnt == 7 (not last)              | DATA       | Advance byte_cnt
               | CS_n == 1'b1                        | IDLE       | Abort

DONE           | status_rdy == 1'b1                   | IDLE       | Output status byte; deassert all
               | (CS_n deassertion also returns)      |            |
```

### 1.3 State Output Table

```
State    | MOSI_out | shift_en | byte_latch | addr_latch | data_latch | status_out | AXI_start
---------|----------|----------|------------|------------|------------|------------|----------
IDLE     | Hi-Z     | 0        | 0          | 0          | 0          | 0          | 0
PREP     | Hi-Z     | 0        | 0          | 0          | 0          | 0          | 0
OPCODE   | Hi-Z     | 1        | 1          | 0          | 0          | 0          | 0
ADDRESS  | Hi-Z     | 1        | 0          | 1 (last)   | 0          | 0          | 0 (start AXI after ADDR done)
DUMMY    | Hi-Z     | 0/1      | 0          | 0          | 0          | 0          | 1 (if read, trigger AXI read)
DATA(R)  | shift_out| 1        | 0          | 0          | 0          | 0          | 0
DATA(W)  | Hi-Z     | 1        | 0          | 0          | 1 (last)   | 0          | 0 (AXI write triggered earlier)
DONE     | status   | 0        | 0          | 0          | 0          | 1          | 0
```

### 1.4 Opcode Definition (from airhdl spi-to-axi-bridge)

| Bit [7] | Description        |
|---------|--------------------|
| `0`     | **Write** transaction (SPI master sends addr + data)     |
| `1`     | **Read** transaction (SPI master sends addr, receives data) |

Extended opcode field for multi-function bridges:

| Opcode[7:0] | Command         | Description                     |
|-------------|-----------------|---------------------------------|
| `0x00`      | WRITE           | 32-bit write at 32-bit address  |
| `0x01`      | READ            | 32-bit read at 32-bit address   |
| `0x02`      | WRITE_16        | 16-bit write (optional)         |
| `0x03`      | READ_16         | 16-bit read (optional)          |
| `0x04..0x7F`| Reserved        | Future use                      |
| `0x80..0xFF`| Vendor-specific | Custom commands                 |

### 1.5 Transaction Byte Sequence (airhdl protocol)

**Write Transaction** (opcode = 0x00) — 11 bytes total:

```
Byte#  MOSI_out       MISO_in        Notes
-----  -------------- -------------- ---------------------------------
  0    0x00 (opcode)  don't care     Write command
  1    addr[31:24]    don't care     Address byte 3 (MSB)
  2    addr[23:16]    don't care     Address byte 2
  3    addr[15:8]     don't care     Address byte 1
  4    addr[7:0]      don't care     Address byte 0 (LSB)
  5    wdata[31:24]   don't care     Data byte 3 (MSB)
  6    wdata[23:16]   don't care     Data byte 2
  7    wdata[15:8]    don't care     Data byte 1
  8    wdata[7:0]     don't care     Data byte 0 (LSB)
  9    don't care     don't care     Dummy (AXI write completion window)
 10    don't care     status[7:0]    Status byte (bits[2]=timeout, bits[1:0]=BRESP)
```

**Read Transaction** (opcode = 0x01) — 11 bytes total:

```
Byte#  MOSI_out       MISO_in        Notes
-----  -------------- -------------- ---------------------------------
  0    0x01 (opcode)  don't care     Read command
  1    addr[31:24]    don't care     Address byte 3 (MSB)
  2    addr[23:16]    don't care     Address byte 2
  3    addr[15:8]     don't care     Address byte 1
  4    addr[7:0]      don't care     Address byte 0 (LSB)
  5    don't care     don't care     Dummy (AXI read latency window)
  6    don't care     rdata[31:24]   Read data byte 3 (MSB)
  7    don't care     rdata[23:16]   Read data byte 2
  8    don't care     rdata[15:8]    Read data byte 1
  9    don't care     rdata[7:0]     Read data byte 0 (LSB)
 10    don't care     status[7:0]    Status byte (bits[2]=timeout, bits[1:0]=RRESP)
```

**Status Byte Encoding:**

| Bit | Field    | Description                     |
|-----|----------|---------------------------------|
| 7   | reserved |                                 |
| 6   | reserved |                                 |
| 5   | reserved |                                 |
| 4   | reserved |                                 |
| 3   | reserved |                                 |
| 2   | timeout  | `1` = AXI transaction timed out |
| 1:0 | RESP     | AXI BRESP or RRESP code         |

AXI Response Codes:

| RESP[1:0] | Mnemonic | Description     |
|-----------|----------|-----------------|
| `2'b00`   | OKAY     | Normal access   |
| `2'b01`   | EXOKAY   | Exclusive access|
| `2'b10`   | SLVERR   | Slave error     |
| `2'b11`   | DECERR   | Decode error    |

### 1.6 ESP32 Hardware FSM Register Reference

The ESP32 SPI controller provides a hardware FSM with status observable via the `FSM.ST` register field:

| Value | State      | Description                   |
|-------|------------|-------------------------------|
| 0     | `IDLE`     | Idle, waiting for transaction |
| 1     | `PREP`     | Preparation phase             |
| 2     | `CMD`      | Command/opcode phase          |
| 3     | `ADDR`     | Address phase                 |
| 4     | `DIN`      | Data input (RX) phase         |
| 5     | `DOUT`     | Data output (TX) phase        |
| 6     | `DUMMY`    | Dummy/wait cycle phase        |
| 7     | `DONE`     | Transaction complete          |

The hardware FSM advances based on these control fields:

| Register Field            | Controls                               |
|---------------------------|----------------------------------------|
| `CTRL1.CMD_LEN`          | Command length (bits)  -> enables CMD  |
| `CTRL1.ADDR_LEN`         | Address length (bits) -> enables ADDR  |
| `CTRL2.DUMMY_CYCLE_LEN`  | Dummy cycle count    -> enables DUMMY  |
| `MISO_DLEN` / `MOSI_DLEN`| Data length (bits)   -> controls DATA  |
| `CMD.USR`                | User command start   -> IDLE->PREP     |

---

## 2. AXI4-Lite Master FSM

### 2.1 State Definitions

An AXI4-Lite master initiates and manages transactions on the AXI bus on behalf of the SPI interface. The FSM uses the five AXI channels (AW, W, B, AR, R) with VALID/READY handshake.

| State         | Encoding (One-Hot) | Description |
|---------------|-------------------:|-------------|
| IDLE          | `7'b000_0001`      | Waiting for transaction request from SPI domain |
| WRITE_ADDR    | `7'b000_0010`      | Driving AW channel: AWVALID + AWADDR |
| WRITE_DATA    | `7'b000_0100`      | Driving W channel: WVALID + WDATA + WSTRB |
| WRITE_RESP    | `7'b000_1000`      | Waiting for B channel: BVALID, capturing BRESP |
| READ_ADDR     | `7'b001_0000`      | Driving AR channel: ARVALID + ARADDR |
| READ_DATA     | `7'b010_0000`      | Waiting for R channel: RVALID, capturing RDATA + RRESP |
| COMPLETE      | `7'b100_0000`      | Transaction done, asserting done/status to SPI domain |

### 2.2 State Transition Table

The AXI4-Lite protocol allows independent VALID/READY handshakes on each channel. The FSM must sequence these while respecting protocol rules.

```
Current State  | Condition                          | Next State    | AXI Signals Driven
---------------|------------------------------------|---------------|-----------------------------------
IDLE           | spi_txn_pending == 1 && write_txn  | WRITE_ADDR    | AWVALID=1, AWADDR=addr
               | spi_txn_pending == 1 && read_txn   | READ_ADDR     | ARVALID=1, ARADDR=addr
               | no_pending                         | IDLE          | All VALID=0

WRITE_ADDR     | AWREADY == 1 && WREADY == 1        | WRITE_RESP    | Deassert AWVALID; AWADDR sampled
               | AWREADY == 1 && WREADY == 0        | WRITE_DATA    | Deassert AWVALID; keep WVALID*
               | AWREADY == 0                       | WRITE_ADDR    | Hold AWVALID; wait

WRITE_DATA     | WREADY == 1                        | WRITE_RESP    | Deassert WVALID; assert BREADY
               | WREADY == 0                        | WRITE_DATA    | Hold WVALID, WDATA, WSTRB

WRITE_RESP     | BVALID == 1 && BREADY == 1         | COMPLETE      | Capture BRESP; deassert BREADY
               | BVALID == 0                        | WRITE_RESP    | Hold BREADY; wait

READ_ADDR      | ARREADY == 1                       | READ_DATA     | Deassert ARVALID; assert RREADY
               | ARREADY == 0                       | READ_ADDR     | Hold ARVALID, ARADDR

READ_DATA      | RVALID == 1 && RREADY == 1         | COMPLETE      | Capture RDATA + RRESP; deassert RREADY
               | RVALID == 0                        | READ_DATA     | Hold RREADY; wait

COMPLETE       | (always, 1 cycle)                  | IDLE          | Assert done pulse to SPI domain
```

\* AXI4-Lite allows AWVALID + WVALID to be asserted simultaneously. If the slave accepts AW but not W in the same cycle, the FSM moves to WRITE_DATA to finish the W handshake.

### 2.3 Combined Address+Data Optimization

For AXI4-Lite, the AW and W channels have no burst relationship. A common optimization combines address and data phases:

```
Optimized state merge:

IDLE --[write_txn]--> WRITE_ADDR_DATA --[AWREADY & WREADY]--> WRITE_RESP
                        |                    |--[AWREADY & !WREADY]--> WRITE_DATA --[WREADY]--> WRITE_RESP

This saves one state for write transactions, reducing total states from 7 to 6.
```

### 2.4 State Output Table (Full)

```
State    | AWVALID | WVALID | ARVALID | BREADY | RREADY | AWADDR | WDATA/WSTRB | ARADDR | done
---------|---------|--------|---------|--------|--------|--------|-------------|--------|-----
IDLE     | 0       | 0      | 0       | 0      | 0      | X      | X           | X      | 0
WRITE_ADDR| 1      | 0/1*   | 0       | 0      | 0      | addr   | X (or data) | X      | 0
WRITE_DATA| 0      | 1      | 0       | 0      | 0      | X      | data        | X      | 0
WRITE_RESP| 0      | 0      | 0       | 1      | 0      | X      | X           | X      | 0
READ_ADDR | 0      | 0      | 1       | 0      | 0      | X      | X           | addr   | 0
READ_DATA | 0      | 0      | 0       | 0      | 1      | X      | X           | X      | 0
COMPLETE  | 0      | 0      | 0       | 0      | 0      | X      | X           | X      | 1

* WVALID may be asserted simultaneously with AWVALID for the combined optimization.
```

### 2.5 Handshake Timing Diagram (Reference)

```
WRITE transaction (address + data combined):

CLK          __   __   __   __   __   __
          __|  |__|  |__|  |__|  |__|  |__
              _____                   _____
AWADDR    XXX_| A  |_________________|     Address phase
              _____
AWVALID    ___|     |___________________
                        _____
AWREADY    ____________|     |___________
              _________________
WDATA     XXX|    write_data    |XXXXXXX   Data phase (combined)
              _________________
WVALID    ___|                 |___________
                           _____
WREADY    __________________|     |________
                                    _____
BVALID    ________________________________|     |_  Response phase
              _____
BREADY    ___|     |___________________________
                                    _____
done      _______________________________|     |_
```

### 2.6 Verilog Template (One-Hot, 3-block FSM)

```systemverilog
// AXI4-Lite Master FSM — One-Hot Encoding
localparam [6:0]
    IDLE        = 7'b000_0001,
    WRITE_ADDR  = 7'b000_0010,
    WRITE_DATA  = 7'b000_0100,
    WRITE_RESP  = 7'b000_1000,
    READ_ADDR   = 7'b001_0000,
    READ_DATA   = 7'b010_0000,
    COMPLETE    = 7'b100_0000;

reg [6:0] state, next_state;

// Block 1: State register
always @(posedge ACLK or negedge ARESETn) begin
    if (!ARESETn) state <= IDLE;
    else          state <= next_state;
end

// Block 2: Next-state logic (combinational)
always @(*) begin
    next_state = state;
    case (1'b1)
        IDLE: begin
            if (spi_txn_pending)
                next_state = spi_write_txn ? WRITE_ADDR : READ_ADDR;
        end
        WRITE_ADDR: begin
            if (AWREADY)
                next_state = WREADY ? WRITE_RESP : WRITE_DATA;
        end
        WRITE_DATA: begin
            if (WREADY) next_state = WRITE_RESP;
        end
        WRITE_RESP: begin
            if (BVALID) next_state = COMPLETE;
        end
        READ_ADDR: begin
            if (ARREADY) next_state = READ_DATA;
        end
        READ_DATA: begin
            if (RVALID) next_state = COMPLETE;
        end
        COMPLETE: begin
            next_state = IDLE;
        end
        default: next_state = IDLE;
    endcase
end

// Block 3: Output logic (combinational)
always @(*) begin
    // Defaults
    {AWVALID, WVALID, ARVALID, BREADY, RREADY} = 5'b0;
    done = 1'b0;
    case (1'b1)
        IDLE: begin
            // All defaults
        end
        WRITE_ADDR: begin
            AWVALID = 1'b1;
            WVALID  = 1'b1;  // combined address+data
        end
        WRITE_DATA: begin
            WVALID = 1'b1;
        end
        WRITE_RESP: begin
            BREADY = 1'b1;
        end
        READ_ADDR: begin
            ARVALID = 1'b1;
            RREADY  = 1'b1;
        end
        READ_DATA: begin
            RREADY = 1'b1;
        end
        COMPLETE: begin
            done = 1'b1;
        end
    endcase
end
```

### 2.7 AXI Protocol Rules for Master FSM

| Rule | Description |
|------|-------------|
| VALID stickiness | Once asserted, VALID must remain asserted until the handshake (READY assertion) |
| No dependency | Master must assert VALID without waiting for READY (avoid deadlock) |
| WDATA stability | WDATA must remain stable while WVALID is asserted |
| AW/W ordering | AXI4-Lite allows AW and W in any order; both must complete before B |
| BREADY timing | BREADY may be asserted before or after BVALID |
| RREADY timing | RREADY may be asserted before or after RVALID |
| Reset | All VALID signals must be deasserted within 1 cycle of reset |

---

## 3. Cross-Clock Domain Synchronization

### 3.1 Clock Domain Architecture

The SPI2AXI bridge operates across two independent clock domains:

```
SPI Clock Domain (spi_clk)                    AXI Clock Domain (axi_clk / ACLK)
==========================                    ==================================
- Frequency: variable (SPI master drives)     - Frequency: fixed (e.g., 50-200 MHz)
- Typically 1-50 MHz                          - Typically 50-200 MHz
- Synchronous to SCK from SPI master          - Synchronous to system ACLK
- Used by: SPI Slave FSM, SPI shift regs     - Used by: AXI Master FSM, AXI channels
```

### 3.2 CDC Boundary Signals

Signals crossing the SPI-to-AXI clock domain boundary:

```
SPI Domain -> AXI Domain                      Direction
--------------------------------------------- ---------
spi_txn_valid  (pulse: "new transaction")     SPI -> AXI
spi_addr[31:0] (multi-bit data)               SPI -> AXI
spi_wdata[31:0] (multi-bit data)              SPI -> AXI
spi_opcode     (1-bit: read/write)            SPI -> AXI
spi_wstrb[3:0] (byte enables)                 SPI -> AXI
axi_txn_done   (pulse: "transaction complete") AXI -> SPI
axi_rdata[31:0] (multi-bit read data)         AXI -> SPI
axi_resp[1:0]  (response code)                AXI -> SPI
axi_timeout    (timeout flag)                 AXI -> SPI
```

### 3.3 Recommended Synchronization Techniques

#### 3.3.1 2-Flop Synchronizer (Level Signals)

For single-bit level signals that remain stable for >2 destination clock cycles.

```systemverilog
// 2-flop synchronizer for axi_txn_done (AXI -> SPI)
// SYNTHESIS attribute: ASYNC_REG = "TRUE"
reg axi_txn_done_sync1, axi_txn_done_sync2;

always @(posedge spi_clk or negedge spi_rst_n) begin
    if (!spi_rst_n) begin
        axi_txn_done_sync1 <= 1'b0;
        axi_txn_done_sync2 <= 1'b0;
    end else begin
        axi_txn_done_sync1 <= axi_txn_done_raw;
        axi_txn_done_sync2 <= axi_txn_done_sync1;
    end
end
// synchronized output: axi_txn_done_sync2
```

**Applicable to:**
- `axi_txn_done` (level signal, held until acknowledged by SPI domain)
- `spi_txn_pending` (held active while transaction is in progress)

#### 3.3.2 Pulse Synchronizer (Toggle + Edge Detect)

For single-cycle pulses crossing from fast to slow (or slow to fast) clock domains.

```systemverilog
// Pulse synchronizer for spi_txn_valid (SPI -> AXI)
// Toggle on source, edge-detect on destination

// Source domain (SPI) — toggle on pulse
reg txn_toggle;
always @(posedge spi_clk or negedge spi_rst_n) begin
    if (!spi_rst_n)        txn_toggle <= 1'b0;
    else if (spi_txn_start) txn_toggle <= ~txn_toggle;
end

// Destination domain (AXI) — synchronize toggle, detect edge
reg toggle_sync1, toggle_sync2, toggle_sync3;
reg axi_txn_start;

always @(posedge ACLK or negedge ARESETn) begin
    if (!ARESETn) begin
        toggle_sync1 <= 1'b0;
        toggle_sync2 <= 1'b0;
        toggle_sync3 <= 1'b0;
    end else begin
        toggle_sync1 <= txn_toggle;
        toggle_sync2 <= toggle_sync1;
        toggle_sync3 <= toggle_sync2;
    end
end

// Edge detection: rising edge = pulse on destination
assign axi_txn_start = toggle_sync2 ^ toggle_sync3;
```

**Applicable to:**
- `spi_txn_valid` (SPI -> AXI, single-cycle pulse)
- `axi_txn_done_pulse` (AXI -> SPI)

#### 3.3.3 Handshake Protocol (Data Convergence)

For multi-bit data where the source domain changes data, then waits for acknowledge. This turns a multi-bit CDC problem into a single-bit CDC problem.

```systemverilog
// Handshake-based multi-bit CDC for address/data

// Source domain (SPI)
reg [31:0] spi_addr_reg;
reg        spi_req;
wire       axi_ack_sync;  // synchronized acknowledge

always @(posedge spi_clk or negedge spi_rst_n) begin
    if (!spi_rst_n) begin
        spi_addr_reg <= 32'b0;
        spi_req      <= 1'b0;
    end else if (spi_new_addr && !spi_req) begin
        spi_addr_reg <= spi_addr_in;
        spi_req      <= 1'b1;  // assert request
    end else if (axi_ack_sync) begin
        spi_req      <= 1'b0;  // clear on acknowledge
    end
end

// Destination domain (AXI)
reg        axi_req_sync1, axi_req_sync2;
reg        axi_ack;
reg [31:0] axi_addr_reg;

// Synchronize request
always @(posedge ACLK or negedge ARESETn) begin
    if (!ARESETn) begin
        axi_req_sync1 <= 1'b0;
        axi_req_sync2 <= 1'b0;
    end else begin
        axi_req_sync1 <= spi_req;
        axi_req_sync2 <= axi_req_sync1;
    end
end

// Capture data when request detected
wire axi_req_edge = axi_req_sync2 && !axi_req_sync1_prev;
always @(posedge ACLK) begin
    if (axi_req_edge) begin
        axi_addr_reg <= spi_addr_reg;  // data stable, safe to capture
        axi_ack <= 1'b1;
    end else if (/* txn accepted */) begin
        axi_ack <= 1'b0;
    end
end
```

**Latency:** 3 destination clock cycles per handshake (request sync + 1).

**Applicable to:**
- `spi_addr[31:0]` (SPI -> AXI, changes infrequently)
- `spi_wdata[31:0]` (SPI -> AXI)
- `spi_wstrb[3:0]` (SPI -> AXI)

#### 3.3.4 Asynchronous FIFO (High-Throughput CDC)

For transferring multiple data items (e.g., burst writes) or when the SPI domain runs independently.

```
                    +--------------------------+
  SPI Domain -->   |  Dual-Clock Async FIFO   |  --> AXI Domain
  (write side)     |  Depth: 8-16 entries     |     (read side)
                   |  Data width: 32+ bits    |
                   +--------------------------+

  Write control:         Read control:
  - wr_clk = spi_clk    - rd_clk = ACLK
  - wr_en               - rd_en
  - full (backpressure)  - empty (stall)
  - Gray code pointers  - Gray code pointers
```

**Key properties:**
- Gray code pointers cross the clock boundary (only 1 bit changes per increment)
- Each pointer is 2-flop synchronized into the other domain
- Full/empty generation uses synchronized pointers

**Applications in SPI2AXI:**

| FIFO | Source | Sink | Width | Depth | Purpose |
|------|--------|------|-------|-------|---------|
| Command FIFO | SPI domain | AXI domain | 32+4+1 = 37b | 4 | Address + wstrb + r/w |
| Write Data FIFO | SPI domain | AXI domain | 32 | 4 | Write data words |
| Read Data FIFO | AXI domain | SPI domain | 32+2 = 34b | 4 | Read data + response |

#### 3.3.5 Synchronization Selection Guide

| Signal Type | Width | Rate | Recommended Technique | Latency |
|-------------|-------|------|----------------------|---------|
| Control (r/w direction) | 1 | Per txn | Pulse synchronizer | 3 dst cycles |
| Address | 32 | Per txn | Handshake | 3 dst cycles + ack |
| Write data | 32 | Per txn | Handshake or Async FIFO | Depends |
| Read data | 32 | Per txn | Async FIFO (read response) | Depends |
| Status/response | 2 | Per txn | 2-flop (held stable) | 2 dst cycles |
| txn_done | 1 | Per txn | Pulse synchronizer | 3 dst cycles |

### 3.4 CDC Timing Closure Considerations

| Topic | Guidance |
|-------|----------|
| SDC false paths | Set `set_false_path -from [get_clocks spi_clk] -to [get_clocks axi_clk]` on data paths; DO NOT set false path on synchronizer FFs |
| ASYNC_REG | Mark all synchronizer FFs with `ASYNC_REG = "TRUE"` to prevent replication and keep FFs adjacent |
| MTBF calculation | For 2-flop: MTBF increases exponentially with 2nd FF; typical > 10^9 years at 100 MHz |
| FIFO depth | Minimum depth = ceil( (rd_latency + wr_latency) / min(txn_time) ) for full throughput |
| Reset sequence | Both clock domains must reset synchronizers; use asynchronous reset, synchronous deassertion |

### 3.5 End-to-End Data Flow

```
SPI Master               SPI2AXI Bridge Core                        AXI Slave
==========               ==================                        ==========

   |                     +-----------+     +---------+     +-----------+
   |  SCK/MOSI/CS_n ---->| SPI Slave |---->|   CDC   |---->| AXI4-Lite |----> AW/AR/W/B/R
   |                     |   FSM     |     |  Bridge |     | Master FSM|----> channels
   |  MISO <-------------| (IDLE->   |<----| (FIFOs +|<----| (IDLE->   |<---- to fabric
   |                     |  DONE)    |     |  sync)  |     |  COMPLETE)|
   |                     +-----------+     +---------+     +-----------+
   |                          |                                    |
   |                     spi_clk                              ACLK
   |                  (SPI domain)                        (AXI domain)
```

**Transaction flow (write):**
1. SPI master asserts CS_n, sends opcode + address + write data on MOSI
2. SPI Slave FSM: `IDLE -> PREP -> OPCODE -> ADDRESS -> DATA -> DONE`
3. On ADDRESS completion: captured address latched into CDC handshake register
4. On DATA completion: captured write data latched into CDC handshake register
5. Pulse synchronizer sends `spi_txn_valid` to AXI domain
6. AXI Master FSM: `IDLE -> WRITE_ADDR -> WRITE_DATA -> WRITE_RESP -> COMPLETE -> IDLE`
7. COMPLETE asserts `axi_txn_done`, synchronized back to SPI domain via pulse synchronizer
8. SPI Slave FSM outputs status byte on MISO (last byte of transaction)

**Transaction flow (read):**
1. SPI master asserts CS_n, sends opcode + address on MOSI
2. SPI Slave FSM: `IDLE -> PREP -> OPCODE -> ADDRESS -> DUMMY -> DATA -> DONE`
3. On ADDRESS completion: address sent to AXI domain via CDC handshake
4. Pulse synchronizer sends `spi_txn_valid` to AXI domain
5. AXI Master FSM: `IDLE -> READ_ADDR -> READ_DATA -> COMPLETE -> IDLE`
6. Read data + response written into Async FIFO (read response FIFO)
7. `axi_txn_done` pulse sent back to SPI domain via pulse synchronizer
8. FIFO data available for SPI domain: DUMMY cycles provide AXI latency window
9. DATA phase: shift read data out on MISO
10. Status byte output on last byte

---

## 4. Key Reference Sources

- **airhdl/spi-to-axi-bridge**: SPI-to-AXI4-Lite bridge with 11-byte transaction protocol, all 4 SPI modes, and OSVVM test suite. [GitHub](https://github.com/airhdl/spi-to-axi-bridge)
- **ESP32 SPI FSM register docs**: Hardware FSM with PREP/CMD/ADDR/DIN/DOUT/DUMMY/DONE states. [docs.rs/esp32s3](https://docs.rs/esp32s3/latest/x86_64-pc-windows-msvc/src/esp32s3/spi1/fsm.rs.html)
- **efabless sky130 spi_slave**: Open-source SPI slave with COMMAND/ADDRESS/DATA FSM on GoogleSource. [foss-eda-tools.googlesource.com](https://foss-eda-tools.googlesource.com/third_party/shuttle/sky130/mpw-001/slot-012/+/cd64af56b357004291503becc2788c4c9c17f68f/verilog/rtl/spi_slave.v)
- **weberxzq/axi_spi_slave**: SPI slave with dual-clock FIFO CDC for SoC AXI access, PULP ecosystem. [GitHub](https://github.com/weberxzq/axi_spi_slave)
- **AXI4-Lite protocol spec**: ARM AMBA 4 AXI4-Lite Protocol Specification (ARM IHI 0022E)
- **Verilog实战：状态机实现AXI4-Lite接口**: Chinese tutorial with complete slave FSM and design pitfalls. [z.shaonianxue.cn](https://z.shaonianxue.cn/41906.html)
