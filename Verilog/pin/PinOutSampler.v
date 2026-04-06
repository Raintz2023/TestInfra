module PinOutSampler #(
    parameter WIDTH = 1,
    parameter DEPTH = 32,
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

    // Keep one pending marker per future cycle so repeated sample requests
    // can be observed one-by-one on SAMP_ALERT.
    reg [DEPTH-1:0] pending_samp;
    reg [DEPTH-1:0] next_pending_samp;
    localparam [OFFSET_W-1:0] ONE = {{(OFFSET_W-1){1'b0}}, 1'b1};

    always @(*) begin
        next_pending_samp = {1'b0, pending_samp[DEPTH-1:1]};

        if (SAMP && (SAMP_OFFSET != {OFFSET_W{1'b0}})) begin
            next_pending_samp[SAMP_OFFSET - ONE] = 1'b1;
        end
    end

    always @(posedge CLK or negedge RST_N) begin
        if (!RST_N) begin
            SAMP_ALERT <= 1'b0;
            SAMP_OUT   <= {WIDTH{1'b0}};
            pending_samp <= {DEPTH{1'b0}};

        end else begin
            SAMP_ALERT <= 1'b0;
            SAMP_OUT   <= {WIDTH{1'b0}};

            if (pending_samp[0]) begin
                SAMP_ALERT <= 1'b1;
                // Sample the DUT output at the delayed observation point,
                // rather than replaying the value captured when SAMP was requested.
                SAMP_OUT   <= SAMP_IN;
            end

            if (SAMP) begin
                if (SAMP_OFFSET == {OFFSET_W{1'b0}}) begin
                    SAMP_ALERT <= 1'b1;
                    SAMP_OUT   <= SAMP_IN;
                end
            end

            pending_samp <= next_pending_samp;
        end
    end

endmodule
