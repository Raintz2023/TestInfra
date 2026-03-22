module PinInRegister #(
    parameter WIDTH    = 1,
    parameter DEPTH    = 16,
    parameter OFFSET_W = $clog2(DEPTH)
)(
    input  wire                  CLK,
    input  wire                  RST_N,

    input  wire [WIDTH-1:0]      DRIV_OUT,
    input  wire                  DRIV_ALERT,

    output reg  [OFFSET_W-1:0]   DRIV_CNTS
);

    reg [WIDTH-1:0] in_reg [0:DEPTH-1];

    integer i;

    always @(posedge CLK or negedge RST_N) begin
        if (!RST_N) begin
            DRIV_CNTS <= {OFFSET_W{1'b0}};

            for (i = 0; i < DEPTH; i = i + 1) begin
                in_reg[i] <= {WIDTH{1'b0}};
            end

        end else begin
            if (DRIV_ALERT) begin

                if (DRIV_CNTS != {OFFSET_W{1'b1}}) begin
                    in_reg[DRIV_CNTS] <= DRIV_OUT;
                    DRIV_CNTS <= DRIV_CNTS + 1;
                end

            end
        end
    end

endmodule