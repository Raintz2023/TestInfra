// Verification wrapper for a digital DUT core. A DUT with its own electrical
// input model can internalize this comparator and remove the exposed controls.
module DutInputComparator #(
    parameter PIN_NUM = 64,
    parameter VOLTAGE_W = 32
)(
    input  wire                         CLK,
    input  wire                         RST_N,
    input  wire [PIN_NUM-1:0]           ENABLE,
    input  wire [PIN_NUM-1:0]           DIGITAL_BYPASS,
    input  wire [PIN_NUM*VOLTAGE_W-1:0] ATE_PIN_UV,
    input  wire [PIN_NUM*VOLTAGE_W-1:0] VREF_UV,
    input  wire [PIN_NUM*VOLTAGE_W-1:0] RISE_STEP_UV,
    input  wire [PIN_NUM*VOLTAGE_W-1:0] FALL_STEP_UV,
    output wire [PIN_NUM-1:0]           DIGITAL_OUT,
    output wire [PIN_NUM*VOLTAGE_W-1:0] DUT_PIN_UV
);

genvar i;
generate
for (i = 0; i < PIN_NUM; i = i + 1) begin : PIN
    wire [VOLTAGE_W-1:0] ate_voltage_uv = ATE_PIN_UV[i*VOLTAGE_W +: VOLTAGE_W];
    wire [VOLTAGE_W-1:0] vref_uv = VREF_UV[i*VOLTAGE_W +: VOLTAGE_W];
    wire [VOLTAGE_W-1:0] rise_step_uv = RISE_STEP_UV[i*VOLTAGE_W +: VOLTAGE_W];
    wire [VOLTAGE_W-1:0] fall_step_uv = FALL_STEP_UV[i*VOLTAGE_W +: VOLTAGE_W];
    reg [VOLTAGE_W-1:0] voltage_uv;

    always @(posedge CLK) begin
        if (!RST_N) begin
            // DUT reset does not discharge the package pin. Keep the
            // electrical node at the voltage currently driven by the ATE.
            voltage_uv <= ate_voltage_uv;
        end else if (!ENABLE[i]) begin
            voltage_uv <= ate_voltage_uv;
        end else if (voltage_uv < ate_voltage_uv) begin
            if ((ate_voltage_uv - voltage_uv) <= rise_step_uv)
                voltage_uv <= ate_voltage_uv;
            else
                voltage_uv <= voltage_uv + rise_step_uv;
        end else if (voltage_uv > ate_voltage_uv) begin
            if ((voltage_uv - ate_voltage_uv) <= fall_step_uv)
                voltage_uv <= ate_voltage_uv;
            else
                voltage_uv <= voltage_uv - fall_step_uv;
        end
    end

    assign DIGITAL_OUT[i] = ENABLE[i] ? (voltage_uv >= vref_uv) : DIGITAL_BYPASS[i];
    assign DUT_PIN_UV[i*VOLTAGE_W +: VOLTAGE_W] = ENABLE[i] ? voltage_uv : ate_voltage_uv;
end
endgenerate

endmodule
