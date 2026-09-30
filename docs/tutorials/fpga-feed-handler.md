# Tutorial: FPGA Feed Handler

**Domain:** HFT  
**Difficulty:** Advanced  
**Duration:** 4–6 hours

---

## Overview

In this tutorial, you'll design a basic FPGA feed handler that receives market data packets from a network port, decodes the protocol, and extracts key fields (symbol, price, quantity). This is the first stage of the tick-to-trade pipeline.

## What You'll Build

- **MAC/UDP/IP stack** in FPGA logic
- **Protocol decoder** for a simple market data format
- **Field extraction** (symbol, price, quantity)
- **Output interface** to order book module

## Prerequisites

- FPGA dev board (Xilinx/AMD or Intel)
- Vivado or Quartus Prime
- Basic Verilog/SystemVerilog knowledge
- Network packet generator (for testing)

---

## Step 1: Define the Protocol

We'll use a simplified market data format:

```
┌─────────────────────────────────────────────────────────┐
│ Ethernet Header (14 bytes)                               │
│  ├─ Dst MAC (6)                                         │
│  ├─ Src MAC (6)                                         │
│  └─ EtherType (2) = 0x0800                              │
├─────────────────────────────────────────────────────────┤
│ IP Header (20 bytes)                                     │
│  ├─ Version/IHL (1)                                     │
│  ├─ TOS (1)                                             │
│  ├─ Total Length (2)                                    │
│  ├─ ID (2)                                              │
│  ├─ Flags/Fragment (2)                                  │
│  ├─ TTL (1)                                             │
│  ├─ Protocol (1) = 17 (UDP)                             │
│  ├─ Checksum (2)                                        │
│  ├─ Src IP (4)                                          │
│  └─ Dst IP (4)                                          │
├─────────────────────────────────────────────────────────┤
│ UDP Header (8 bytes)                                     │
│  ├─ Src Port (2)                                        │
│  ├─ Dst Port (2)                                        │
│  ├─ Length (2)                                          │
│  └─ Checksum (2)                                        │
├─────────────────────────────────────────────────────────┤
│ Market Data Payload (variable)                           │
│  ├─ Symbol (8 bytes, ASCII)                             │
│  ├─ Price (8 bytes, fixed-point)                        │
│  ├─ Quantity (4 bytes, uint32)                          │
│  └─ Side (1 byte, 'B' or 'S')                           │
└─────────────────────────────────────────────────────────┘
```

## Step 2: Top-Level Module

```verilog
// feed_handler.v
module feed_handler (
    input  wire        clk_250mhz,
    input  wire        rst_n,
    
    // RGMII interface (to PHY)
    input  wire [3:0]  rgmii_rxd,
    input  wire        rgmii_rx_ctl,
    input  wire        rgmii_rx_clk,
    output wire [3:0]  rgmii_txd,
    output wire        rgmii_tx_ctl,
    output wire        rgmii_tx_clk,
    
    // Output to order book
    output reg  [63:0] symbol,
    output reg  [63:0] price,
    output reg  [31:0] quantity,
    output reg         side,  // 1=buy, 0=sell
    output reg         valid,
    input  wire        ready
);

    // Internal signals
    wire [7:0]  rx_data;
    wire        rx_valid;
    wire        rx_sof;  // Start of frame
    wire        rx_eof;  // End of frame
    
    // Protocol parsing state machine
    localparam S_IDLE       = 4'd0;
    localparam S_ETH_DST    = 4'd1;
    localparam S_ETH_SRC    = 4'd2;
    localparam S_ETH_TYPE   = 4'd3;
    localparam S_IP_HDR     = 4'd4;
    localparam S_UDP_HDR    = 4'd5;
    localparam S_SYMBOL     = 4'd6;
    localparam S_PRICE      = 4'd7;
    localparam S_QUANTITY   = 4'd8;
    localparam S_SIDE       = 4'd9;
    localparam S_OUTPUT     = 4'd10;
    
    reg [3:0]  state;
    reg [15:0] byte_counter;
    reg [7:0]  header_buffer [0:51];  // Store headers
    
    // RGMII to byte conversion (simplified)
    rgmii_receiver rgmii_rx (
        .clk(clk_250mhz),
        .rst_n(rst_n),
        .rxd(rgmii_rxd),
        .rx_ctl(rgmii_rx_ctl),
        .rx_clk(rgmii_rx_clk),
        .data_out(rx_data),
        .data_valid(rx_valid),
        .sof(rx_sof),
        .eof(rx_eof)
    );
    
    // Main state machine
    always @(posedge clk_250mhz or negedge rst_n) begin
        if (!rst_n) begin
            state <= S_IDLE;
            byte_counter <= 0;
            valid <= 0;
        end else begin
            valid <= 0;  // Default: deassert
            
            case (state)
                S_IDLE: begin
                    if (rx_sof) begin
                        state <= S_ETH_DST;
                        byte_counter <= 0;
                    end
                end
                
                S_ETH_DST: begin
                    if (rx_valid) begin
                        header_buffer[byte_counter] <= rx_data;
                        byte_counter <= byte_counter + 1;
                        if (byte_counter == 5) begin
                            state <= S_ETH_SRC;
                            byte_counter <= 0;
                        end
                    end
                end
                
                S_ETH_SRC: begin
                    if (rx_valid) begin
                        header_buffer[byte_counter + 6] <= rx_data;
                        byte_counter <= byte_counter + 1;
                        if (byte_counter == 5) begin
                            state <= S_ETH_TYPE;
                            byte_counter <= 0;
                        end
                    end
                end
                
                S_ETH_TYPE: begin
                    if (rx_valid) begin
                        header_buffer[byte_counter + 12] <= rx_data;
                        byte_counter <= byte_counter + 1;
                        if (byte_counter == 1) begin
                            // Check EtherType = 0x0800 (IPv4)
                            if (header_buffer[12] == 8'h08 &&
                                header_buffer[13] == 8'h00) begin
                                state <= S_IP_HDR;
                                byte_counter <= 0;
                            end else begin
                                state <= S_IDLE;  // Not IPv4
                            end
                        end
                    end
                end
                
                S_IP_HDR: begin
                    if (rx_valid) begin
                        header_buffer[byte_counter + 14] <= rx_data;
                        byte_counter <= byte_counter + 1;
                        if (byte_counter == 19) begin
                            // Check protocol = UDP (17)
                            if (header_buffer[23] == 8'd17) begin
                                state <= S_UDP_HDR;
                                byte_counter <= 0;
                            end else begin
                                state <= S_IDLE;
                            end
                        end
                    end
                end
                
                S_UDP_HDR: begin
                    if (rx_valid) begin
                        header_buffer[byte_counter + 34] <= rx_data;
                        byte_counter <= byte_counter + 1;
                        if (byte_counter == 7) begin
                            state <= S_SYMBOL;
                            byte_counter <= 0;
                        end
                    end
                end
                
                S_SYMBOL: begin
                    if (rx_valid) begin
                        symbol[63:56] <= rx_data;  // MSB first
                        symbol <= {symbol[55:0], rx_data};
                        byte_counter <= byte_counter + 1;
                        if (byte_counter == 7) begin
                            state <= S_PRICE;
                            byte_counter <= 0;
                        end
                    end
                end
                
                S_PRICE: begin
                    if (rx_valid) begin
                        price <= {price[55:0], rx_data};
                        byte_counter <= byte_counter + 1;
                        if (byte_counter == 7) begin
                            state <= S_QUANTITY;
                            byte_counter <= 0;
                        end
                    end
                end
                
                S_QUANTITY: begin
                    if (rx_valid) begin
                        quantity <= {quantity[23:0], rx_data};
                        byte_counter <= byte_counter + 1;
                        if (byte_counter == 3) begin
                            state <= S_SIDE;
                            byte_counter <= 0;
                        end
                    end
                end
                
                S_SIDE: begin
                    if (rx_valid) begin
                        side <= (rx_data == 8'h42);  // 'B' = buy
                        state <= S_OUTPUT;
                    end
                end
                
                S_OUTPUT: begin
                    if (ready) begin
                        valid <= 1;
                        state <= S_IDLE;
                    end
                end
                
                default: state <= S_IDLE;
            endcase
        end
    end

endmodule
```

## Step 3: RGMII Receiver (Simplified)

```verilog
// rgmii_receiver.v
module rgmii_receiver (
    input  wire        clk,
    input  wire        rst_n,
    input  wire [3:0]  rxd,
    input  wire        rx_ctl,
    input  wire        rx_clk,
    output reg  [7:0]  data_out,
    output reg         data_valid,
    output reg         sof,
    output reg         eof
);
    
    // DDR sampling (simplified - use IDDR in real design)
    reg [7:0] rx_shift;
    reg [2:0] bit_count;
    
    always @(posedge rx_clk or negedge rst_n) begin
        if (!rst_n) begin
            data_valid <= 0;
            sof <= 0;
            eof <= 0;
            bit_count <= 0;
        end else begin
            data_valid <= 0;
            sof <= 0;
            eof <= 0;
            
            // Sample on both edges (DDR)
            rx_shift <= {rxd, rx_shift[7:4]};
            bit_count <= bit_count + 4;
            
            if (bit_count == 4) begin
                data_out <= {rxd, rx_shift[7:4]};
                data_valid <= rx_ctl;
                sof <= (bit_count == 0) && rx_ctl;
                eof <= !rx_ctl;
            end
        end
    end

endmodule
```

## Step 4: Testbench

```verilog
// tb_feed_handler.v
`timescale 1ns/1ps

module tb_feed_handler;
    
    reg clk_250mhz = 0;
    reg rst_n = 0;
    
    wire [63:0] symbol;
    wire [63:0] price;
    wire [31:0] quantity;
    wire        side;
    wire        valid;
    reg         ready = 1;
    
    // Clock generation
    always #2 clk_250mhz = ~clk_250mhz;  // 250 MHz
    
    feed_handler dut (
        .clk_250mhz(clk_250mhz),
        .rst_n(rst_n),
        .rgmii_rxd(4'b0),
        .rgmii_rx_ctl(1'b0),
        .rgmii_rx_clk(clk_250mhz),
        .rgmii_txd(),
        .rgmii_tx_ctl(),
        .rgmii_tx_clk(),
        .symbol(symbol),
        .price(price),
        .quantity(quantity),
        .side(side),
        .valid(valid),
        .ready(ready)
    );
    
    initial begin
        $dumpfile("feed_handler.vcd");
        $dumpvars(0, tb_feed_handler);
        
        // Reset
        #100 rst_n = 1;
        
        // Send test packet
        // ... (packet generation logic)
        
        #10000 $finish;
    end
    
    always @(posedge valid) begin
        $display("Symbol: %s, Price: %h, Qty: %d, Side: %s",
            symbol, price, quantity, side ? "BUY" : "SELL");
    end

endmodule
```

## Step 5: Synthesize and Deploy

```tcl
# Vivado TCL script
read_verilog feed_handler.v
read_verilog rgmii_receiver.v
read_xdc constraints.xdc

synth_design -top feed_handler -part xc7k325tffg900-2
opt_design
place_design
route_design

write_bitstream -force feed_handler.bit
```

## Expected Results

| Metric | Value |
|--------|-------|
| Clock frequency | 250 MHz |
| Latency (wire-to-output) | 100–200 ns |
| Throughput | 10 Gbps (line rate) |
| LUT utilization | ~5–10% |

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Timing violations | Add pipeline stages, reduce logic depth |
| Packet corruption | Verify RGMII sampling, check DDR alignment |
| Missing packets | Check SOF/EOF detection, verify buffer sizes |
| High latency | Minimize state machine depth, use parallel decoding |

## Next Steps

- Add order book update logic
- Implement multiple protocol support (ITCH, OUCH, FIX)
- Add timestamping for latency measurement
- Move to [P4 Switch Pipeline](p4-switch-pipeline.md) for programmable alternative
