// Verification wrapper for a digital DUT core. A DUT with its own electrical
// output model can internalize this driver and remove the exposed controls.
module DutOutputDriver #(
    parameter PIN_NUM = 64,
    parameter VOLTAGE_W = 32
)(
    input  wire                         CLK,
    input  wire                         RST_N,
    input  wire [PIN_NUM-1:0]           ENABLE,
    input  wire [PIN_NUM-1:0]           DIGITAL_IN,
    input  wire [PIN_NUM*VOLTAGE_W-1:0] LOW_UV,
    input  wire [PIN_NUM*VOLTAGE_W-1:0] HIGH_UV,
    input  wire [PIN_NUM*VOLTAGE_W-1:0] RISE_STEP_UV,
    input  wire [PIN_NUM*VOLTAGE_W-1:0] FALL_STEP_UV,
    output wire [PIN_NUM*VOLTAGE_W-1:0] PIN_UV
);

genvar i;
generate
for (i = 0; i < PIN_NUM; i = i + 1) begin : PIN
    wire [VOLTAGE_W-1:0] low_uv = LOW_UV[i*VOLTAGE_W +: VOLTAGE_W];
    wire [VOLTAGE_W-1:0] high_uv = HIGH_UV[i*VOLTAGE_W +: VOLTAGE_W];
    wire [VOLTAGE_W-1:0] rise_step_uv = RISE_STEP_UV[i*VOLTAGE_W +: VOLTAGE_W];
    wire [VOLTAGE_W-1:0] fall_step_uv = FALL_STEP_UV[i*VOLTAGE_W +: VOLTAGE_W];
    wire [VOLTAGE_W-1:0] target_uv = DIGITAL_IN[i] ? high_uv : low_uv;
    reg  [VOLTAGE_W-1:0] voltage_uv;

    always @(posedge CLK) begin
        if (!RST_N) begin
            // Reset changes the DUT logic target, not the physical rail.
            voltage_uv <= target_uv;
        end else if (!ENABLE[i]) begin
            voltage_uv <= target_uv;
        end else if (voltage_uv < target_uv) begin
            if ((target_uv - voltage_uv) <= rise_step_uv)
                voltage_uv <= target_uv;
            else
                voltage_uv <= voltage_uv + rise_step_uv;
        end else if (voltage_uv > target_uv) begin
            if ((voltage_uv - target_uv) <= fall_step_uv)
                voltage_uv <= target_uv;
            else
                voltage_uv <= voltage_uv - fall_step_uv;
        end
    end

    assign PIN_UV[i*VOLTAGE_W +: VOLTAGE_W] = voltage_uv;
end
endgenerate

endmodule
