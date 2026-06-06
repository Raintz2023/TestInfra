module Socket #(
    parameter PIN_IN_NUM  = 24,
    parameter PIN_OUT_NUM = 4,
    parameter DEPTH    = 32,
    parameter OFFSET_W = $clog2(DEPTH),
    parameter DELAY_W  = 32
)(
    input wire ATE_CLK,
    input wire ATE_RST_N,
    /* verilator lint_off UNUSEDSIGNAL */
    input wire ALERT,
    input wire [31:0] TOP_DATA,
    /* verilator lint_on UNUSEDSIGNAL */

    input  wire [PIN_IN_NUM-1:0] DRIV,
    input  wire [PIN_IN_NUM-1:0] DRIV_IN,
    input  wire [PIN_IN_NUM*DELAY_W-1:0] DRIV_DELAY,
    input  wire [PIN_IN_NUM*DELAY_W-1:0] DRIV_DURATION,

    output wire [PIN_IN_NUM-1:0] DRIV_ALERT,
    output wire [PIN_IN_NUM*OFFSET_W-1:0] DRIV_CNTS,

    input  wire [PIN_OUT_NUM-1:0] SAMP,
    input  wire [PIN_OUT_NUM*DELAY_W-1:0] SAMP_DELAY,

    output wire [PIN_OUT_NUM-1:0] SAMP_OUT,
    output wire [PIN_OUT_NUM-1:0] SAMP_ALERT,
    output wire [PIN_OUT_NUM*OFFSET_W-1:0] SAMP_CNTS
);
    wire [PIN_IN_NUM-1:0] in_wire;
    wire [PIN_OUT_NUM-1:0] out_wire;

    PinIn #(
        .PIN_NUM(PIN_IN_NUM),
        .DEPTH(DEPTH),
        .DELAY_W(DELAY_W)
    ) pin_in (
        .CLK        (ATE_CLK),
        .RST_N      (ATE_RST_N),

        .DRIV       (DRIV),
        .DRIV_IN    (DRIV_IN),
        .DRIV_DELAY (DRIV_DELAY),
        .DRIV_DURATION(DRIV_DURATION),

        .DRIV_OUT   (in_wire),
        .DRIV_ALERT (DRIV_ALERT),
        .DRIV_CNTS  (DRIV_CNTS)
    );

    DUT dut (
        .IN  (in_wire),
        .OUT (out_wire)
    );

    PinOut #(
        .PIN_NUM(PIN_OUT_NUM),
        .DEPTH(DEPTH),
        .DELAY_W(DELAY_W)
    ) pin_out (
        .CLK        (ATE_CLK),
        .RST_N      (ATE_RST_N),

        .SAMP       (SAMP),
        .SAMP_IN    (out_wire),
        .SAMP_DELAY (SAMP_DELAY),

        .SAMP_OUT   (SAMP_OUT),
        .SAMP_ALERT (SAMP_ALERT),
        .SAMP_CNTS  (SAMP_CNTS)
    );

endmodule
