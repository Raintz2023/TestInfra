module AteInputDriver #(
    parameter PIN_NUM = 64,
    parameter VOLTAGE_W = 32
)(
    input  wire [PIN_NUM-1:0]           DIGITAL_IN,
    input  wire [PIN_NUM*VOLTAGE_W-1:0] VIL_UV,
    input  wire [PIN_NUM*VOLTAGE_W-1:0] VIH_UV,
    output wire [PIN_NUM*VOLTAGE_W-1:0] PIN_UV
);

genvar i;
generate
for (i = 0; i < PIN_NUM; i = i + 1) begin : PIN
    wire [VOLTAGE_W-1:0] vil_uv = VIL_UV[i*VOLTAGE_W +: VOLTAGE_W];
    wire [VOLTAGE_W-1:0] vih_uv = VIH_UV[i*VOLTAGE_W +: VOLTAGE_W];
    wire [VOLTAGE_W-1:0] target_uv = DIGITAL_IN[i] ? vih_uv : vil_uv;
    assign PIN_UV[i*VOLTAGE_W +: VOLTAGE_W] = target_uv;
end
endgenerate

endmodule
