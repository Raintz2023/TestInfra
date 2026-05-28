module Chip(
    input  wire       CLK,
    input  wire       RST_N,
    input  wire       START_IN,
    input  wire       START_OUT,
    input  wire       R,
    input  wire       W,
    input  wire [7:0] ADDR,
    input  wire       DQ_IN,
    input  wire [7:0] MR_IN,
    input  wire       MRW,   
    input  wire       MRR,
    input  wire       DRIV,

    output wire       DQ_IE,
    output wire       DOUT_TX,
    output wire [7:0] MR_OUT,
    output wire       DQ_OE,
    output wire       DQ_OUT_VALID
);
    /* verilator lint_off UNUSEDSIGNAL */
    
    wire [7:0] rx_dq_data;
    wire       rx_busy;
    wire       rx_done;
    wire       rx_start_bit;
    wire       rx_stop_bit;

    wire [7:0] dram_dq_data;

    wire       tx_busy;
    wire       tx_done;
    /* verilator lint_on UNUSEDSIGNAL */
    
    Receiver u_receiver (
        .CLK   (CLK),
        .RST_N (RST_N),
        .DOUT  (rx_dq_data),
        .BUSY  (rx_busy),
        .DONE  (rx_done),
        .PRE   (rx_start_bit),
        .POST  (rx_stop_bit),
        .START (START_IN),
        .DIN   (DQ_IN)
    );

    Dram u_dram (
        .R           (R),
        .W           (W),
        .ADDR        (ADDR),
        .DQ_IN       (rx_dq_data),
        .MR_IN       (MR_IN),
        .MRW         (MRW),
        .MRR         (MRR),
        .DRIV        (DRIV),
        .CLK         (CLK),
        .RST_N       (RST_N),
        .DQ_IE       (DQ_IE),
        .DQ_OUT      (dram_dq_data),
        .MR_OUT      (MR_OUT),
        .DQ_OE       (DQ_OE),
        .DQ_OUT_VALID(DQ_OUT_VALID)
    );

    Sender u_sender (
        .CLK   (CLK),
        .RST_N (RST_N),
        .DOUT  (DOUT_TX),
        .BUSY  (tx_busy),
        .DONE  (tx_done),
        .START (START_OUT),
        .DIN   (dram_dq_data)
    );

endmodule
