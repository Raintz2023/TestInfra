module Encoder  (
    input  wire       CLK,
    input  wire       RST_N,
    input  wire [15:0] IN_,

    output reg  [3:0] OUT_
);

    integer i;

    always @(posedge CLK or negedge RST_N) begin
        if (!RST_N)
            OUT_ <= 0;
        else begin
            OUT_ <= 0;
            for (i = 0; i < 16; i = i + 1)
                if (IN_[i])
                    OUT_ <= i[4-1:0];
        end
    end

endmodule
