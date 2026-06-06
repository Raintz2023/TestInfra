module Chip(
    input  wire       CLK,
    input  wire       RST_N,
    input  wire       DQ_RX_START,
    input  wire       R,
    input  wire       W,
    input  wire [7:0] ADDR,
    input  wire       DQ_RX_BIT,
    input  wire [7:0] MR_IN,
    input  wire       MRW,   
    input  wire       MRR,

    output wire       DQ_IE,
    output wire       DQ_TX_BIT,
    output wire       DQ_OE,
    output wire       DQ_OUT_VALID
);
    /* verilator lint_off UNUSEDSIGNAL */
    
    wire [7:0] dq_rx_data;
    wire       rx_busy;
    wire       dq_rx_valid;
    wire       rx_start_bit;
    wire       rx_stop_bit;

    wire [7:0] dq_tx_data;

    wire       tx_busy;
    wire       dq_tx_valid;
    /* verilator lint_on UNUSEDSIGNAL */
    
    Receiver u_receiver (
        .CLK      (CLK),
        .RST_N    (RST_N),
        .DATA     (dq_rx_data),
        .BUSY     (rx_busy),
        .VALID    (dq_rx_valid),
        .START_BIT(rx_start_bit),
        .STOP_BIT (rx_stop_bit),
        .START    (DQ_RX_START),
        .BIT_IN   (DQ_RX_BIT)
    );

    Dram u_dram (
        .R           (R),
        .W           (W),
        .ADDR        (ADDR),
        .DQ_RX_DATA  (dq_rx_data),
        .DQ_RX_VALID (dq_rx_valid),
        .MR_IN       (MR_IN),
        .MRW         (MRW),
        .MRR         (MRR),
        .CLK         (CLK),
        .RST_N       (RST_N),
        .DQ_IE       (DQ_IE),
        .DQ_TX_DATA  (dq_tx_data),
        .DQ_OE       (DQ_OE),
        .DQ_OUT_VALID(DQ_OUT_VALID)
    );

    Sender u_sender (
        .CLK    (CLK),
        .RST_N  (RST_N),
        .BIT_OUT(DQ_TX_BIT),
        .BUSY   (tx_busy),
        .VALID  (dq_tx_valid),
        .START  (DQ_OE),
        .DATA   (dq_tx_data)
    );

endmodule
