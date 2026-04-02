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

    reg [OFFSET_W-1:0] pending_cycles;
    reg pending_samp;

    always @(posedge CLK or negedge RST_N) begin
        if (!RST_N) begin
            SAMP_ALERT <= 1'b0;
            SAMP_OUT   <= {WIDTH{1'b0}};
            pending_samp <= 1'b0;
            pending_cycles <= {OFFSET_W{1'b0}};

        end else begin

            SAMP_ALERT <= 1'b0;
            SAMP_OUT   <= {WIDTH{1'b0}};

            if (pending_samp) begin
                if (pending_cycles == {{(OFFSET_W-1){1'b0}}, 1'b1}) begin
                    SAMP_ALERT <= 1'b1;
                    // Sample the DUT output at the delayed observation point,
                    // rather than replaying the value captured when SAMP was requested.
                    SAMP_OUT   <= SAMP_IN;
                    pending_samp <= 1'b0;
                    pending_cycles <= {OFFSET_W{1'b0}};
                end else begin
                    pending_cycles <= pending_cycles - {{(OFFSET_W-1){1'b0}}, 1'b1};
                end
            end

            // Keep one delayed event in flight per pin. This matches current
            // protocol usage and avoids simulator sensitivity around array
            // indexing on delayed queues.
            if (SAMP) begin
                if (SAMP_OFFSET == {OFFSET_W{1'b0}}) begin
                    SAMP_ALERT <= 1'b1;
                    SAMP_OUT   <= SAMP_IN;
                end else begin
                    pending_samp <= 1'b1;
                    pending_cycles <= SAMP_OFFSET;
                end
            end
        end
    end

endmodule
