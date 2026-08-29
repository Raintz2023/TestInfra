module Socket #(
    parameter PIN_IN_NUM  = 24,
    parameter PIN_OUT_NUM = 5,
    parameter DEPTH    = 32,
    parameter OFFSET_W = $clog2(DEPTH),
    parameter DELAY_W  = 32,
    parameter VOLTAGE_W = 32
)(
    input wire ATE_CLK,
    input wire ATE_RST_N,
    input wire DUT_ANALOG_ENABLE,
    /* verilator lint_off UNUSEDSIGNAL */
    input wire ALERT,
    input wire [31:0] TOP_DATA,
    /* verilator lint_on UNUSEDSIGNAL */

    input  wire [PIN_IN_NUM-1:0] DRIV,
    input  wire [PIN_IN_NUM-1:0] DRIV_IN,
    input  wire [PIN_IN_NUM-1:0] DRIV_RETURN_IN,
    input  wire [PIN_IN_NUM*DELAY_W-1:0] DRIV_DELAY,
    input  wire [PIN_IN_NUM*DELAY_W-1:0] DRIV_DURATION,

    output wire [PIN_IN_NUM-1:0] DRIV_ALERT,
    output wire [PIN_IN_NUM*OFFSET_W-1:0] DRIV_CNTS,

    // A voltage-controlled pin may feed an asynchronous DUT reset while the
    // same configuration also drives the synchronous slew model.
    /* verilator lint_off SYNCASYNCNET */
    /* verilator lint_off UNUSEDSIGNAL */
    input wire [PIN_IN_NUM*VOLTAGE_W-1:0] ATE_VIL_UV,
    input wire [PIN_IN_NUM*VOLTAGE_W-1:0] ATE_VIH_UV,
    input wire [PIN_IN_NUM-1:0] DUT_INPUT_ENABLE,
    input wire [PIN_IN_NUM*VOLTAGE_W-1:0] DUT_VREF_UV,
    input wire [PIN_IN_NUM*VOLTAGE_W-1:0] DUT_INPUT_RISE_STEP_UV,
    input wire [PIN_IN_NUM*VOLTAGE_W-1:0] DUT_INPUT_FALL_STEP_UV,
    input wire [VOLTAGE_W-1:0] DUT_VDDQ_UV,
    input wire [3:0] DUT_RX_DQS_SKEW,
    input wire [3:0] DUT_RX_DQ_SKEW,
    input wire [3:0] DUT_TX_DQS_SKEW,
    input wire [3:0] DUT_TX_DQ_SKEW,
    output wire [PIN_IN_NUM*VOLTAGE_W-1:0] ATE_PIN_IN_UV,
    output wire [PIN_IN_NUM*VOLTAGE_W-1:0] PIN_IN_UV,
    /* verilator lint_on UNUSEDSIGNAL */
    /* verilator lint_on SYNCASYNCNET */

    input  wire [PIN_OUT_NUM-1:0] SAMP,
    input  wire [PIN_OUT_NUM*DELAY_W-1:0] SAMP_DELAY,

    output wire [PIN_OUT_NUM-1:0] SAMP_OUT,
    output wire [PIN_OUT_NUM-1:0] SAMP_VALID,
    output wire [PIN_OUT_NUM-1:0] SAMP_ALERT,
    output wire [PIN_OUT_NUM*OFFSET_W-1:0] SAMP_CNTS,
    output wire [PIN_OUT_NUM-1:0] PIN_OUT_DIGITAL,

    input wire [PIN_OUT_NUM-1:0] DUT_OUTPUT_ENABLE,
    input wire [PIN_OUT_NUM*VOLTAGE_W-1:0] DUT_LOW_UV,
    input wire [PIN_OUT_NUM*VOLTAGE_W-1:0] DUT_HIGH_UV,
    input wire [PIN_OUT_NUM*VOLTAGE_W-1:0] DUT_OUTPUT_RISE_STEP_UV,
    input wire [PIN_OUT_NUM*VOLTAGE_W-1:0] DUT_OUTPUT_FALL_STEP_UV,
    input wire [PIN_OUT_NUM-1:0] ATE_OUTPUT_ENABLE,
    input wire [PIN_OUT_NUM*VOLTAGE_W-1:0] ATE_VOL_UV,
    input wire [PIN_OUT_NUM*VOLTAGE_W-1:0] ATE_VOH_UV,
    output wire [PIN_OUT_NUM*VOLTAGE_W-1:0] PIN_OUT_UV
);
    wire [PIN_IN_NUM-1:0] ate_drive_wire;
    wire [PIN_OUT_NUM-1:0] dut_output_wire;
    wire [PIN_OUT_NUM-1:0] ate_sample_wire;
    wire [PIN_OUT_NUM-1:0] ate_sample_valid_wire;

    PinIn #(
        .PIN_NUM(PIN_IN_NUM),
        .DEPTH(DEPTH),
        .DELAY_W(DELAY_W)
    ) pin_in (
        .CLK        (ATE_CLK),
        .RST_N      (ATE_RST_N),

        .DRIV       (DRIV),
        .DRIV_IN    (DRIV_IN),
        .DRIV_RETURN_IN(DRIV_RETURN_IN),
        .DRIV_DELAY (DRIV_DELAY),
        .DRIV_DURATION(DRIV_DURATION),
        .DRIV_OUT   (ate_drive_wire),
        .DRIV_ALERT (DRIV_ALERT),
        .DRIV_CNTS  (DRIV_CNTS)
    );

    AteInputDriver #(
        .PIN_NUM(PIN_IN_NUM),
        .VOLTAGE_W(VOLTAGE_W)
    ) ate_input_driver (
        .DIGITAL_IN(ate_drive_wire),
        .VIL_UV(ATE_VIL_UV),
        .VIH_UV(ATE_VIH_UV),
        .PIN_UV(ATE_PIN_IN_UV)
    );

    DUT #(
        .VOLTAGE_W(VOLTAGE_W)
    ) dut (
        .ATE_CLK(ATE_CLK),
        .ATE_RST_N(ATE_RST_N),
        .DUT_ANALOG_ENABLE(DUT_ANALOG_ENABLE),
        .IN(ate_drive_wire),
        .DUT_INPUT_ENABLE(DUT_INPUT_ENABLE),
        .ATE_PIN_IN_UV(ATE_PIN_IN_UV),
        .DUT_INPUT_RISE_STEP_UV(DUT_INPUT_RISE_STEP_UV),
        .DUT_INPUT_FALL_STEP_UV(DUT_INPUT_FALL_STEP_UV),
        .DUT_RX_DQS_SKEW(DUT_RX_DQS_SKEW),
        .DUT_RX_DQ_SKEW(DUT_RX_DQ_SKEW),
        .DUT_TX_DQS_SKEW(DUT_TX_DQS_SKEW),
        .DUT_TX_DQ_SKEW(DUT_TX_DQ_SKEW),
        .DUT_OUTPUT_ENABLE(DUT_OUTPUT_ENABLE),
        .DUT_LOW_UV(DUT_LOW_UV),
        .DUT_HIGH_UV(DUT_HIGH_UV),
        .DUT_RISE_STEP_UV(DUT_OUTPUT_RISE_STEP_UV),
        .DUT_FALL_STEP_UV(DUT_OUTPUT_FALL_STEP_UV),
        .DUT_VDDQ_UV(DUT_VDDQ_UV),
        .OUT(dut_output_wire),
        .PIN_IN_UV(PIN_IN_UV),
        .PIN_OUT_UV(PIN_OUT_UV)
    );

    AteOutputComparator #(
        .PIN_NUM(PIN_OUT_NUM),
        .VOLTAGE_W(VOLTAGE_W)
    ) ate_output_comparator (
        .ENABLE(ATE_OUTPUT_ENABLE),
        .DIGITAL_BYPASS(dut_output_wire),
        .PIN_UV(PIN_OUT_UV),
        .VOL_UV(ATE_VOL_UV),
        .VOH_UV(ATE_VOH_UV),
        .DIGITAL_OUT(ate_sample_wire),
        .DIGITAL_VALID(ate_sample_valid_wire)
    );

    // Continuous, non-sampling monitor path for C++ testbench control flow.
    // Unlike SAMP_OUT, this bus does not pulse low between sample events.
    assign PIN_OUT_DIGITAL = ate_sample_wire;

    PinOut #(
        .PIN_NUM(PIN_OUT_NUM),
        .DEPTH(DEPTH),
        .DELAY_W(DELAY_W)
    ) pin_out (
        .CLK        (ATE_CLK),
        .RST_N      (ATE_RST_N),

        .SAMP       (SAMP),
        .SAMP_IN    (ate_sample_wire),
        .SAMP_VALID_IN(ate_sample_valid_wire),
        .SAMP_DELAY (SAMP_DELAY),

        .SAMP_OUT   (SAMP_OUT),
        .SAMP_VALID_OUT(SAMP_VALID),
        .SAMP_ALERT (SAMP_ALERT),
        .SAMP_CNTS  (SAMP_CNTS)
    );

endmodule
