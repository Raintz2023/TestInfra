module Socket #(
    parameter PIN_IN_NUM  = 29,
    parameter PIN_OUT_NUM = 19,
    parameter DEPTH    = 32,
    parameter OFFSET_W = $clog2(DEPTH)
)(
    input wire CLK,
    input wire RST_N,

    input  wire [PIN_IN_NUM-1:0] DRIV,
    input  wire [PIN_IN_NUM-1:0] DRIV_IN,
    input  wire [PIN_IN_NUM*OFFSET_W-1:0] DRIV_OFFSET,

    output wire [PIN_IN_NUM-1:0] DRIV_ALERT,
    output wire [PIN_IN_NUM*OFFSET_W-1:0] DRIV_CNTS,

    input  wire [PIN_OUT_NUM-1:0] SAMP,
    input  wire [PIN_OUT_NUM*OFFSET_W-1:0] SAMP_OFFSET,

    output wire [PIN_OUT_NUM-1:0] SAMP_OUT,
    output wire [PIN_OUT_NUM-1:0] SAMP_ALERT,
    output wire [PIN_OUT_NUM*OFFSET_W-1:0] SAMP_CNTS
);
    wire [PIN_IN_NUM-1:0] in_wire;
    wire [PIN_OUT_NUM-1:0] out_wire;

    PinIn #(
        .PIN_NUM(PIN_IN_NUM),
        .DEPTH(DEPTH)
    ) pin_in (
        .CLK        (CLK),
        .RST_N      (RST_N),

        .DRIV       (DRIV),
        .DRIV_IN    (DRIV_IN),
        .DRIV_OFFSET(DRIV_OFFSET),

        .DRIV_OUT   (in_wire),
        .DRIV_ALERT (DRIV_ALERT),
        .DRIV_CNTS  (DRIV_CNTS)
    );

    DUT dut (
        .CLK (CLK),
        .RST_N(RST_N),

        .IN  (in_wire),
        .OUT (out_wire)
    );

    PinOut #(
        .PIN_NUM(PIN_OUT_NUM),
        .DEPTH(DEPTH)
    ) pin_out (
        .CLK        (CLK),
        .RST_N      (RST_N),

        .SAMP       (SAMP),
        .SAMP_IN    (out_wire),
        .SAMP_OFFSET(SAMP_OFFSET),

        .SAMP_OUT   (SAMP_OUT),
        .SAMP_ALERT (SAMP_ALERT),
        .SAMP_CNTS  (SAMP_CNTS)
    );

endmodule
