module Out_Register (
    input  wire       CLK,
    input  wire       RST_N,

    input reg  [7:0] SAMP_DATA,
    input reg        SAMP_VALID,

    output reg  [4:0] SAMP_CNTS,
    output reg  [7:0] OUT_REG [0:31]
);

    integer i;

    always @(posedge CLK or negedge RST_N) begin
        if (!RST_N) begin

            SAMP_CNTS <= 5'd0;
            for (i=0; i<32; i=i+1) begin
                OUT_REG[i] <= 8'd0;
            end

        end else begin
            if (SAMP_VALID) begin
                SAMP_CNTS <= SAMP_CNTS + 5'd1;
                OUT_REG[SAMP_CNTS] <= SAMP_DATA;
            end
        end
    end

endmodule
