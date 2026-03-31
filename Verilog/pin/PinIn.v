module PinIn #(
    parameter PIN_NUM  = 64,
    parameter WIDTH    = 1,
    parameter DEPTH    = 16,
    parameter OFFSET_W = $clog2(DEPTH)
)(
    input wire CLK,
    input wire RST_N,

    input wire [PIN_NUM-1:0] DRIV,
    input wire [PIN_NUM*WIDTH-1:0] DRIV_IN,
    input wire [PIN_NUM*OFFSET_W-1:0] DRIV_OFFSET,

    output wire [PIN_NUM*WIDTH-1:0] DRIV_OUT,
    output wire [PIN_NUM-1:0] DRIV_ALERT,
    output wire [PIN_NUM*OFFSET_W-1:0] DRIV_CNTS
);

genvar i;
generate
for (i = 0; i < PIN_NUM; i = i + 1) begin : PIN

    wire driv_i;
    wire [WIDTH-1:0] driv_in_i;
    wire [OFFSET_W-1:0] offset_i;

    assign driv_i     = DRIV[i];
    assign driv_in_i  = DRIV_IN[i*WIDTH +: WIDTH];
    assign offset_i   = DRIV_OFFSET[i*OFFSET_W +: OFFSET_W];

    wire [WIDTH-1:0] driv_out_i;
    wire alert_i;
    wire [OFFSET_W-1:0] cnt_i;

    // 实例
    PinInDriver driver (
        .CLK(CLK),
        .RST_N(RST_N),
        .DRIV(driv_i),
        .DRIV_IN(driv_in_i),
        .DRIV_OFFSET(offset_i),
        .DRIV_OUT(driv_out_i),
        .DRIV_ALERT(alert_i)
    );

    PinInRegister reg_inst (
        .CLK(CLK),
        .RST_N(RST_N),
        .DRIV_ALERT(alert_i),
        .DRIV_CNTS(cnt_i)
    );

    // pack回去
    assign DRIV_OUT[i*WIDTH +: WIDTH] = driv_out_i;
    assign DRIV_ALERT[i]              = alert_i;
    assign DRIV_CNTS[i*OFFSET_W +: OFFSET_W] = cnt_i;

end
endgenerate

endmodule
