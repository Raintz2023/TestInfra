module ChipAnalogWrapper #(
    parameter VOLTAGE_W = 32,
    parameter RX_DQS_SKEW = 4'd0,
    parameter RX_DQ_SKEW = 4'd1,
    parameter TX_DQS_SKEW = 4'd2,
    parameter TX_DQ_SKEW = 4'd0,
    parameter DEFAULT_DUT_INPUT_RISE_STEP_UV = 30000,
    parameter DEFAULT_DUT_INPUT_FALL_STEP_UV = 30000,
    parameter DEFAULT_DUT_OUTPUT_LOW_UV = 300000,
    parameter DEFAULT_DUT_OUTPUT_HIGH_UV = 900000,
    parameter DEFAULT_DUT_OUTPUT_RISE_STEP_UV = 30000,
    parameter DEFAULT_DUT_OUTPUT_FALL_STEP_UV = 30000
)(
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
    output wire       DQ_OUT_VALID,

    input  wire [VOLTAGE_W-1:0] VDDQ_UV,
    input  wire                 ANALOG_ENABLE,
    input  wire                 ATE_CLK,
    input  wire [24*VOLTAGE_W-1:0] ATE_PIN_IN_UV,
    /* verilator lint_off UNUSEDSIGNAL */
    input  wire [23:0] DUT_INPUT_ENABLE,
    input  wire [24*VOLTAGE_W-1:0] DUT_INPUT_RISE_STEP_UV,
    input  wire [24*VOLTAGE_W-1:0] DUT_INPUT_FALL_STEP_UV,
    input  wire [3:0] DUT_RX_DQS_SKEW,
    input  wire [3:0] DUT_RX_DQ_SKEW,
    input  wire [3:0] DUT_TX_DQS_SKEW,
    input  wire [3:0] DUT_TX_DQ_SKEW,
    input  wire [4:0] DUT_OUTPUT_ENABLE,
    input  wire [5*VOLTAGE_W-1:0] DUT_LOW_UV,
    input  wire [5*VOLTAGE_W-1:0] DUT_HIGH_UV,
    input  wire [5*VOLTAGE_W-1:0] DUT_RISE_STEP_UV,
    input  wire [5*VOLTAGE_W-1:0] DUT_FALL_STEP_UV,
    /* verilator lint_on UNUSEDSIGNAL */
    output wire [24*VOLTAGE_W-1:0] PIN_IN_UV,
    output wire [5*VOLTAGE_W-1:0] PIN_OUT_UV
);
    localparam DQ_RX_PIN = 12;
    localparam DQS_RX_PIN = 13;
    localparam DQ_TX_PIN = 1;
    localparam DQS_TX_PIN = 2;

    wire [VOLTAGE_W-1:0] dq_rx_pin_uv;
    wire [VOLTAGE_W-1:0] dqs_rx_pin_uv;
    wire [VOLTAGE_W-1:0] dq_tx_pin_uv;
    wire [VOLTAGE_W-1:0] dqs_tx_pin_uv;
    wire [VOLTAGE_W-1:0] default_dut_input_rise_step_uv =
        DEFAULT_DUT_INPUT_RISE_STEP_UV[VOLTAGE_W-1:0];
    wire [VOLTAGE_W-1:0] default_dut_input_fall_step_uv =
        DEFAULT_DUT_INPUT_FALL_STEP_UV[VOLTAGE_W-1:0];
    wire [VOLTAGE_W-1:0] default_dut_output_low_uv =
        DEFAULT_DUT_OUTPUT_LOW_UV[VOLTAGE_W-1:0];
    wire [VOLTAGE_W-1:0] default_dut_output_high_uv =
        DEFAULT_DUT_OUTPUT_HIGH_UV[VOLTAGE_W-1:0];
    wire [VOLTAGE_W-1:0] default_dut_output_rise_step_uv =
        DEFAULT_DUT_OUTPUT_RISE_STEP_UV[VOLTAGE_W-1:0];
    wire [VOLTAGE_W-1:0] default_dut_output_fall_step_uv =
        DEFAULT_DUT_OUTPUT_FALL_STEP_UV[VOLTAGE_W-1:0];
    genvar pin_idx;

    generate
        for (pin_idx = 0; pin_idx < 24; pin_idx = pin_idx + 1) begin : PIN_IN_UV_GEN
            if (pin_idx == DQ_RX_PIN) begin : DQ_RX
                assign PIN_IN_UV[pin_idx*VOLTAGE_W +: VOLTAGE_W] = dq_rx_pin_uv;
            end else if (pin_idx == DQS_RX_PIN) begin : DQS_RX
                assign PIN_IN_UV[pin_idx*VOLTAGE_W +: VOLTAGE_W] = dqs_rx_pin_uv;
            end else begin : BYPASS
                assign PIN_IN_UV[pin_idx*VOLTAGE_W +: VOLTAGE_W] =
                    ATE_PIN_IN_UV[pin_idx*VOLTAGE_W +: VOLTAGE_W];
            end
        end

        for (pin_idx = 0; pin_idx < 5; pin_idx = pin_idx + 1) begin : PIN_OUT_UV_GEN
            if (pin_idx == DQ_TX_PIN) begin : DQ_TX
                assign PIN_OUT_UV[pin_idx*VOLTAGE_W +: VOLTAGE_W] = dq_tx_pin_uv;
            end else if (pin_idx == DQS_TX_PIN) begin : DQS_TX
                assign PIN_OUT_UV[pin_idx*VOLTAGE_W +: VOLTAGE_W] = dqs_tx_pin_uv;
            end else begin : ZERO
                assign PIN_OUT_UV[pin_idx*VOLTAGE_W +: VOLTAGE_W] = {VOLTAGE_W{1'b0}};
            end
        end
    endgenerate

    Dram #(
        .VOLTAGE_W(VOLTAGE_W),
        .RX_DQS_SKEW(RX_DQS_SKEW),
        .RX_DQ_SKEW(RX_DQ_SKEW),
        .TX_DQS_SKEW(TX_DQS_SKEW),
        .TX_DQ_SKEW(TX_DQ_SKEW)
    ) u_dram (
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
        .DQ_OUT_VALID(DQ_OUT_VALID),
        .VDDQ_UV      (VDDQ_UV),
        .ATE_CLK     (ATE_CLK),
        .ATE_DQ_RX_UV(ATE_PIN_IN_UV[DQ_RX_PIN*VOLTAGE_W +: VOLTAGE_W]),
        .ATE_DQS_RX_UV(ATE_PIN_IN_UV[DQS_RX_PIN*VOLTAGE_W +: VOLTAGE_W]),
        // The electrical input model belongs to the DUT and is always active.
        // DUT_INPUT_ENABLE only selects an explicit C++ parameter override.
        .DQ_RX_ANALOG_ENABLE(ANALOG_ENABLE),
        .DQS_RX_ANALOG_ENABLE(ANALOG_ENABLE),
        .DQ_RX_RISE_STEP_UV(DUT_INPUT_ENABLE[DQ_RX_PIN] ?
            DUT_INPUT_RISE_STEP_UV[DQ_RX_PIN*VOLTAGE_W +: VOLTAGE_W] :
            default_dut_input_rise_step_uv),
        .DQ_RX_FALL_STEP_UV(DUT_INPUT_ENABLE[DQ_RX_PIN] ?
            DUT_INPUT_FALL_STEP_UV[DQ_RX_PIN*VOLTAGE_W +: VOLTAGE_W] :
            default_dut_input_fall_step_uv),
        .DQS_RX_RISE_STEP_UV(DUT_INPUT_ENABLE[DQS_RX_PIN] ?
            DUT_INPUT_RISE_STEP_UV[DQS_RX_PIN*VOLTAGE_W +: VOLTAGE_W] :
            default_dut_input_rise_step_uv),
        .DQS_RX_FALL_STEP_UV(DUT_INPUT_ENABLE[DQS_RX_PIN] ?
            DUT_INPUT_FALL_STEP_UV[DQS_RX_PIN*VOLTAGE_W +: VOLTAGE_W] :
            default_dut_input_fall_step_uv),
        .RX_DQS_SKEW_CFG(DUT_RX_DQS_SKEW),
        .RX_DQ_SKEW_CFG(DUT_RX_DQ_SKEW),
        .TX_DQS_SKEW_CFG(DUT_TX_DQS_SKEW),
        .TX_DQ_SKEW_CFG(DUT_TX_DQ_SKEW),
        .DQ_TX_ANALOG_ENABLE(ANALOG_ENABLE),
        .DQS_TX_ANALOG_ENABLE(ANALOG_ENABLE),
        .DQ_TX_LOW_UV(DUT_OUTPUT_ENABLE[DQ_TX_PIN] ?
            DUT_LOW_UV[DQ_TX_PIN*VOLTAGE_W +: VOLTAGE_W] :
            default_dut_output_low_uv),
        .DQ_TX_HIGH_UV(DUT_OUTPUT_ENABLE[DQ_TX_PIN] ?
            DUT_HIGH_UV[DQ_TX_PIN*VOLTAGE_W +: VOLTAGE_W] :
            default_dut_output_high_uv),
        .DQ_TX_RISE_STEP_UV(DUT_OUTPUT_ENABLE[DQ_TX_PIN] ?
            DUT_RISE_STEP_UV[DQ_TX_PIN*VOLTAGE_W +: VOLTAGE_W] :
            default_dut_output_rise_step_uv),
        .DQ_TX_FALL_STEP_UV(DUT_OUTPUT_ENABLE[DQ_TX_PIN] ?
            DUT_FALL_STEP_UV[DQ_TX_PIN*VOLTAGE_W +: VOLTAGE_W] :
            default_dut_output_fall_step_uv),
        .DQS_TX_LOW_UV(DUT_OUTPUT_ENABLE[DQS_TX_PIN] ?
            DUT_LOW_UV[DQS_TX_PIN*VOLTAGE_W +: VOLTAGE_W] :
            default_dut_output_low_uv),
        .DQS_TX_HIGH_UV(DUT_OUTPUT_ENABLE[DQS_TX_PIN] ?
            DUT_HIGH_UV[DQS_TX_PIN*VOLTAGE_W +: VOLTAGE_W] :
            default_dut_output_high_uv),
        .DQS_TX_RISE_STEP_UV(DUT_OUTPUT_ENABLE[DQS_TX_PIN] ?
            DUT_RISE_STEP_UV[DQS_TX_PIN*VOLTAGE_W +: VOLTAGE_W] :
            default_dut_output_rise_step_uv),
        .DQS_TX_FALL_STEP_UV(DUT_OUTPUT_ENABLE[DQS_TX_PIN] ?
            DUT_FALL_STEP_UV[DQS_TX_PIN*VOLTAGE_W +: VOLTAGE_W] :
            default_dut_output_fall_step_uv),
        .DQ_RX_PIN_UV(dq_rx_pin_uv),
        .DQS_RX_PIN_UV(dqs_rx_pin_uv),
        .DQ_TX_PIN_UV(dq_tx_pin_uv),
        .DQS_TX_PIN_UV(dqs_tx_pin_uv)
    );

endmodule
