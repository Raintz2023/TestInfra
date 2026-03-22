module Encoder #(
    parameter IN_WIDTH  = 16,
    parameter OUT_WIDTH = 4
) (
    input  wire       CLK,
    input  wire       RST_N,
    input  wire [IN_WIDTH-1:0] IN,

    output reg  [OUT_WIDTH-1:0] OUT
);

    integer i;

    always @(posedge CLK or negedge RST_N) begin
        if (!RST_N)
            OUT <= 0;
        else begin
            OUT <= 0;
            for (i = 0; i < IN_WIDTH; i = i + 1)
                if (IN[i])
                    OUT <= i[OUT_WIDTH-1:0];
        end
    end

endmodule