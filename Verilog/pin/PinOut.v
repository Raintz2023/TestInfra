module PinOut #(
    parameter PIN_NUM  = 64,
    parameter WIDTH    = 1,
    parameter DEPTH    = 32,
    parameter OFFSET_W = $clog2(DEPTH)
)(
    input wire CLK,
    input wire RST_N,

    input wire [PIN_NUM-1:0] SAMP,
    input wire [PIN_NUM*WIDTH-1:0] SAMP_IN,
    input wire [PIN_NUM*OFFSET_W-1:0] SAMP_OFFSET,

    output wire [PIN_NUM*WIDTH-1:0] SAMP_OUT,
    output wire [PIN_NUM-1:0] SAMP_ALERT,
    output wire [PIN_NUM*OFFSET_W-1:0] SAMP_CNTS
);

genvar i;
generate
for (i = 0; i < PIN_NUM; i = i + 1) begin : PIN

    wire samp_i;
    wire [WIDTH-1:0] samp_in_i;
    wire [OFFSET_W-1:0] offset_i;

    assign samp_i     = SAMP[i];
    assign samp_in_i  = SAMP_IN[i*WIDTH +: WIDTH];
    assign offset_i   = SAMP_OFFSET[i*OFFSET_W +: OFFSET_W];

    wire [WIDTH-1:0] samp_out_i;
    wire alert_i;
    wire [OFFSET_W-1:0] cnt_i;

    // 实例
    PinOutSampler sampler (
        .CLK(CLK),
        .RST_N(RST_N),
        .SAMP(samp_i),
        .SAMP_IN(samp_in_i),
        .SAMP_OFFSET(offset_i),
        .SAMP_OUT(samp_out_i),
        .SAMP_ALERT(alert_i)
    );

    PinOutRegister reg_inst (
        .CLK(CLK),
        .RST_N(RST_N),
        .SAMP_ALERT(alert_i),
        .SAMP_CNTS(cnt_i)
    );

    // pack回去
    assign SAMP_OUT[i*WIDTH +: WIDTH] = samp_out_i;
    assign SAMP_ALERT[i]              = alert_i;
    assign SAMP_CNTS[i*OFFSET_W +: OFFSET_W] = cnt_i;

end
endgenerate

endmodule
