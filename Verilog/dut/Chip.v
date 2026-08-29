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
    input  wire [31:0] VDDQ_UV,

    output wire       DQ_IE,
    output wire       DQ_TX_BIT,
    output wire       DQS_TX_BIT,
    output wire       DQ_OE,
    output wire       DQ_OUT_VALID
);
    localparam VOLTAGE_W = 32;
    localparam PIN_IN_NUM = 24;
    localparam PIN_OUT_NUM = 5;
    wire [PIN_IN_NUM*VOLTAGE_W-1:0] ate_pin_in_uv;
    wire [PIN_IN_NUM*VOLTAGE_W-1:0] pin_in_uv_unused;
    wire [PIN_OUT_NUM*VOLTAGE_W-1:0] pin_out_uv_unused;

    assign ate_pin_in_uv = {PIN_IN_NUM{VDDQ_UV}};

    ChipAnalogWrapper #(
        .VOLTAGE_W(VOLTAGE_W)
    ) u_chip (
        .CLK(CLK),
        .RST_N(RST_N),
        .R(R),
        .W(W),
        .ADDR(ADDR),
        .DQ_RX_BIT(DQ_RX_BIT),
        .DQS_RX_BIT(DQS_RX_BIT),
        .MR_IN(MR_IN),
        .MRW(MRW),
        .MRR(MRR),
        .DQ_IE(DQ_IE),
        .DQ_TX_BIT(DQ_TX_BIT),
        .DQS_TX_BIT(DQS_TX_BIT),
        .DQ_OE(DQ_OE),
        .DQ_OUT_VALID(DQ_OUT_VALID),
        .VDDQ_UV(VDDQ_UV),
        .ANALOG_ENABLE(1'b0),
        .ATE_CLK(CLK),
        .ATE_PIN_IN_UV(ate_pin_in_uv),
        .DUT_INPUT_ENABLE({PIN_IN_NUM{1'b0}}),
        .DUT_INPUT_RISE_STEP_UV({PIN_IN_NUM{32'd100000}}),
        .DUT_INPUT_FALL_STEP_UV({PIN_IN_NUM{32'd100000}}),
        .DUT_RX_DQS_SKEW(4'd0),
        .DUT_RX_DQ_SKEW(4'd1),
        .DUT_TX_DQS_SKEW(4'd2),
        .DUT_TX_DQ_SKEW(4'd0),
        .DUT_OUTPUT_ENABLE({PIN_OUT_NUM{1'b0}}),
        .DUT_LOW_UV({PIN_OUT_NUM{32'd0}}),
        .DUT_HIGH_UV({PIN_OUT_NUM{32'd1200000}}),
        .DUT_RISE_STEP_UV({PIN_OUT_NUM{32'd100000}}),
        .DUT_FALL_STEP_UV({PIN_OUT_NUM{32'd100000}}),
        .PIN_IN_UV(pin_in_uv_unused),
        .PIN_OUT_UV(pin_out_uv_unused)
    );

endmodule
