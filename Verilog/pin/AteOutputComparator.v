module AteOutputComparator #(
    parameter PIN_NUM = 64,
    parameter VOLTAGE_W = 32
)(
    input  wire [PIN_NUM-1:0]           ENABLE,
    input  wire [PIN_NUM-1:0]           DIGITAL_BYPASS,
    input  wire [PIN_NUM*VOLTAGE_W-1:0] PIN_UV,
    input  wire [PIN_NUM*VOLTAGE_W-1:0] VOL_UV,
    input  wire [PIN_NUM*VOLTAGE_W-1:0] VOH_UV,
    output wire [PIN_NUM-1:0]           DIGITAL_OUT,
    output wire [PIN_NUM-1:0]           DIGITAL_VALID
);

genvar i;
generate
for (i = 0; i < PIN_NUM; i = i + 1) begin : PIN
    wire [VOLTAGE_W-1:0] voltage_uv = PIN_UV[i*VOLTAGE_W +: VOLTAGE_W];
    wire [VOLTAGE_W-1:0] vol_uv = VOL_UV[i*VOLTAGE_W +: VOLTAGE_W];
    wire [VOLTAGE_W-1:0] voh_uv = VOH_UV[i*VOLTAGE_W +: VOLTAGE_W];

    assign DIGITAL_OUT[i] = ENABLE[i] ? (voltage_uv >= voh_uv) : DIGITAL_BYPASS[i];
    assign DIGITAL_VALID[i] = !ENABLE[i] || (voltage_uv <= vol_uv) || (voltage_uv >= voh_uv);
end
endgenerate

endmodule
