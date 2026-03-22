module PinOutRegister #(
    parameter WIDTH    = 1,
    parameter DEPTH    = 16,
    parameter OFFSET_W = $clog2(DEPTH)
)(
    input  wire                  CLK,
    input  wire                  RST_N,

    input  wire [WIDTH-1:0]      SAMP_OUT,
    input  wire                  SAMP_ALERT,

    output reg  [OFFSET_W-1:0]   SAMP_CNTS
);
    
    reg [WIDTH-1:0] out_reg [0:DEPTH-1];

    integer i;

    always @(posedge CLK or negedge RST_N) begin
        if (!RST_N) begin
            SAMP_CNTS <= {OFFSET_W{1'b0}};

            for (i = 0; i < DEPTH; i = i + 1) begin
                out_reg[i] <= {WIDTH{1'b0}};
            end

        end else begin
            if (SAMP_ALERT) begin

                if (SAMP_CNTS != {OFFSET_W{1'b1}}) begin
                    out_reg[SAMP_CNTS] <= SAMP_OUT;
                    SAMP_CNTS <= SAMP_CNTS + 1;
                end

            end
        end
    end

endmodule