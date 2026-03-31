module Comparer #(
    parameter WIDTH = 4
)(
    input  wire             CLK,
    input  wire             RST_N,
    input  wire [WIDTH-1:0] TOP_DATA,
    input  wire [WIDTH-1:0] SAMP_OUT,
    input  wire [WIDTH-1:0] SAMP_ALERT,
    output reg              COMPARE_PASS,
    output reg              COMPARE_VALID
);

    always @(posedge CLK or negedge RST_N) begin
        if (!RST_N) begin
            COMPARE_PASS  <= 1'b0;
            COMPARE_VALID <= 1'b0;
        end else begin
            if (|SAMP_ALERT) begin
                COMPARE_PASS  <= ((SAMP_OUT & SAMP_ALERT) == (TOP_DATA & SAMP_ALERT));
                COMPARE_VALID <= 1'b1;
            end
        end
    end

endmodule
