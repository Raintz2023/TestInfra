module PinOutRegister #(
    parameter DEPTH    = 16,
    parameter OFFSET_W = $clog2(DEPTH)
)(
    input  wire                  CLK,
    input  wire                  RST_N,

    input  wire                  SAMP_ALERT,

    output reg  [OFFSET_W-1:0]   SAMP_CNTS
);

    always @(posedge CLK or negedge RST_N) begin
        if (!RST_N) begin
            SAMP_CNTS <= {OFFSET_W{1'b0}};

        end else begin
            if (SAMP_ALERT) begin

                if (SAMP_CNTS != {OFFSET_W{1'b1}}) begin
                    SAMP_CNTS <= SAMP_CNTS + 1;
                end

            end
        end
    end

endmodule
