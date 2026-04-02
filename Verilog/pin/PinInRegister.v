module PinInRegister #(
    parameter DEPTH    = 32,
    parameter OFFSET_W = $clog2(DEPTH)
)(
    input  wire                  CLK,
    input  wire                  RST_N,

    input  wire                  DRIV_ALERT,

    output reg  [OFFSET_W-1:0]   DRIV_CNTS
);

    always @(posedge CLK or negedge RST_N) begin
        if (!RST_N) begin
            DRIV_CNTS <= {OFFSET_W{1'b0}};

        end else begin
            if (DRIV_ALERT) begin

                if (DRIV_CNTS != {OFFSET_W{1'b1}}) begin
                    DRIV_CNTS <= DRIV_CNTS + 1;
                end

            end
        end
    end

endmodule
