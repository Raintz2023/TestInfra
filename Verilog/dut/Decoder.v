module Decoder (
    input  wire        CLK,
    input  wire        RST_N,
    input  wire [3:0]  IN_,

    output reg  [15:0] OUT_
);

    always @(posedge CLK or negedge RST_N) begin
        if (!RST_N)
            OUT_ <= 16'b0;
        else
            OUT_ <= 16'b1 << IN_;
    end

endmodule