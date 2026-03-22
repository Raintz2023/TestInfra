module Decoder (
    input  wire        CLK,
    input  wire        RST_N,
    input  wire [3:0]  IN,

    output reg  [15:0] OUT
);

    always @(posedge CLK or negedge RST_N) begin
        if (!RST_N)
            OUT <= 16'b0;
        else
            OUT <= 16'b1 << IN;
    end

endmodule