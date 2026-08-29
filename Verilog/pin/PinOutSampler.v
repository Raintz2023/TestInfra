module PinOutSampler #(
    parameter WIDTH = 1,
    parameter DEPTH = 32,
    parameter DELAY_W = 32
)(
    input  wire               CLK,
    input  wire               RST_N,

    input  wire               SAMP,
    input  wire [WIDTH-1:0]   SAMP_IN,
    input  wire [WIDTH-1:0]   SAMP_VALID_IN,
    input  wire [DELAY_W-1:0] SAMP_DELAY,

    output reg  [WIDTH-1:0]   SAMP_OUT,
    output reg  [WIDTH-1:0]   SAMP_VALID_OUT,
    output reg                SAMP_ALERT
);

    reg [31:0] phase_counter;
    reg        ev_valid [0:DEPTH-1];
    reg [31:0] ev_due [0:DEPTH-1];
    integer i;
    integer free_idx;

    always @(posedge CLK or negedge RST_N) begin
        if (!RST_N) begin
            phase_counter <= 32'd0;
            SAMP_ALERT <= 1'b0;
            SAMP_OUT   <= {WIDTH{1'b0}};
            SAMP_VALID_OUT <= {WIDTH{1'b0}};
            for (i = 0; i < DEPTH; i = i + 1) begin
                ev_valid[i] <= 1'b0;
                ev_due[i] <= 32'd0;
            end

        end else begin
            SAMP_ALERT <= 1'b0;
            SAMP_OUT   <= {WIDTH{1'b0}};
            SAMP_VALID_OUT <= {WIDTH{1'b0}};

            for (i = 0; i < DEPTH; i = i + 1) begin
                if (ev_valid[i] && (ev_due[i] == phase_counter)) begin
                    SAMP_ALERT <= 1'b1;
                    SAMP_OUT   <= SAMP_IN;
                    SAMP_VALID_OUT <= SAMP_VALID_IN;
                    ev_valid[i] <= 1'b0;
                end
            end

            if (SAMP) begin
                if (SAMP_DELAY == 32'd0) begin
                    SAMP_ALERT <= 1'b1;
                    SAMP_OUT   <= SAMP_IN;
                    SAMP_VALID_OUT <= SAMP_VALID_IN;
                end else begin
                    /* verilator lint_off BLKSEQ */
                    free_idx = -1;
                    for (i = 0; i < DEPTH; i = i + 1) begin
                        if (!ev_valid[i] && free_idx == -1) begin
                            free_idx = i;
                        end
                    end
                    /* verilator lint_on BLKSEQ */
                    if (free_idx >= 0) begin
                        ev_valid[free_idx] <= 1'b1;
                        ev_due[free_idx] <= phase_counter + SAMP_DELAY;
                    end
                end
            end

            phase_counter <= phase_counter + 32'd1;
        end
    end

endmodule
