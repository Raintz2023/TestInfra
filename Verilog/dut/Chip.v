module Chip(
    input  wire       CLK,
    input  wire       RST_N,
    input  wire       R,
    input  wire       W,
    input  wire [7:0] ADDR,
    input  wire       DQ_RX_BIT,
    input  wire       DQS_RX_BIT,
    input  wire [7:0] MR_IN,
    input  wire       MRW,   
    input  wire       MRR,

    output wire       DQ_IE,
    output wire       DQ_TX_BIT,
    output wire       DQS_TX_BIT,
    output wire       DQ_OE,
    output wire       DQ_OUT_VALID
);
    Dram u_dram (
        .R           (R),
        .W           (W),
        .ADDR        (ADDR),
        .DQ_RX_BIT   (DQ_RX_BIT),
        .DQS_RX_BIT  (DQS_RX_BIT),
        .MR_IN       (MR_IN),
        .MRW         (MRW),
        .MRR         (MRR),
        .CLK         (CLK),
        .RST_N       (RST_N),
        .DQ_IE       (DQ_IE),
        .DQ_TX_BIT   (DQ_TX_BIT),
        .DQS_TX_BIT  (DQS_TX_BIT),
        .DQ_OE       (DQ_OE),
        .DQ_OUT_VALID(DQ_OUT_VALID)
    );

endmodule
