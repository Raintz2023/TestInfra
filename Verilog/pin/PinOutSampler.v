module PinOutSampler #(
    parameter WIDTH = 1,
    parameter DEPTH = 16,
    parameter OFFSET_W = $clog2(DEPTH)
)(
    input  wire               CLK,
    input  wire               RST_N,

    input  wire               SAMP,
    input  wire [WIDTH-1:0]   SAMP_IN,
    input  wire [OFFSET_W-1:0] SAMP_OFFSET,

    output reg  [WIDTH-1:0]   SAMP_OUT,
    output reg                SAMP_ALERT
);

    reg [WIDTH-1:0] fut_samp_in [0:DEPTH-1];
    reg             fut_samp    [0:DEPTH-1];

    integer i;

    always @(posedge CLK or negedge RST_N) begin
        if (!RST_N) begin
            SAMP_ALERT <= 1'b0;
            SAMP_OUT   <= {WIDTH{1'b0}};

            for (i=0; i<DEPTH; i=i+1) begin
                fut_samp_in[i] <= {WIDTH{1'b0}};
                fut_samp[i]    <= 1'b0;
            end

        end else begin

            SAMP_ALERT <= 1'b0;
            SAMP_OUT   <= {WIDTH{1'b0}};

            // shift pipeline
            for (i=DEPTH-1; i>0; i=i-1) begin
                fut_samp_in[i] <= fut_samp_in[i-1];
                fut_samp[i]    <= fut_samp[i-1];
            end

            fut_samp_in[0] <= {WIDTH{1'b0}};
            fut_samp[0]    <= 1'b0;

            // record event
            if (SAMP) begin
                if (SAMP_OFFSET == {OFFSET_W{1'b0}}) begin
                    SAMP_ALERT <= 1'b1;
                    SAMP_OUT   <= SAMP_IN;
                end else begin
                    fut_samp[0]    <= 1'b1;
                    fut_samp_in[0] <= SAMP_IN;
                end
            end

            // delayed output
            if ((SAMP_OFFSET != {OFFSET_W{1'b0}}) && fut_samp[SAMP_OFFSET-1]) begin
                SAMP_ALERT <= 1'b1;
                SAMP_OUT   <= fut_samp_in[SAMP_OFFSET-1];
            end
        end
    end

endmodule
