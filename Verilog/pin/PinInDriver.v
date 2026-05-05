module PinInDriver #(
    parameter WIDTH = 1,
    parameter DEPTH = 32,
    parameter DELAY_W = 32
)(
    input  wire               CLK,
    input  wire               RST_N,

    input  wire               DRIV,
    input  wire [WIDTH-1:0]   DRIV_IN,
    input  wire [DELAY_W-1:0] DRIV_DELAY,
    input  wire [DELAY_W-1:0] DRIV_DURATION,

    output reg  [WIDTH-1:0]   DRIV_OUT,
    output reg                DRIV_ALERT
);

    reg [31:0] phase_counter;
    reg        ev_valid [0:DEPTH-1];
    reg        ev_active [0:DEPTH-1];
    reg [31:0] ev_due   [0:DEPTH-1];
    reg [31:0] ev_until [0:DEPTH-1];
    reg [WIDTH-1:0] ev_data [0:DEPTH-1];
    integer i;
    integer free_idx;

    always @(posedge CLK or negedge RST_N) begin
        if (!RST_N) begin
            phase_counter <= 32'd0;
            DRIV_ALERT <= 1'b0;
            DRIV_OUT   <= {WIDTH{1'b0}};
            for (i = 0; i < DEPTH; i = i + 1) begin
                ev_valid[i] <= 1'b0;
                ev_active[i] <= 1'b0;
                ev_due[i] <= 32'd0;
                ev_until[i] <= 32'd0;
                ev_data[i] <= {WIDTH{1'b0}};
            end

        end else begin
            DRIV_ALERT <= 1'b0;

            if (DRIV) begin
                if (DRIV_DELAY == 32'd0) begin
                    DRIV_ALERT <= 1'b1;
                    DRIV_OUT   <= DRIV_IN;
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
                        ev_active[free_idx] <= 1'b0;
                        ev_due[free_idx] <= phase_counter + DRIV_DELAY;
                        ev_until[free_idx] <= phase_counter + DRIV_DELAY + DRIV_DURATION;
                        ev_data[free_idx] <= DRIV_IN;
                    end
                end
            end

            for (i = 0; i < DEPTH; i = i + 1) begin
                if (ev_valid[i] && (ev_until[i] == phase_counter)) begin
                    DRIV_OUT <= {WIDTH{1'b0}};
                    ev_valid[i] <= 1'b0;
                    ev_active[i] <= 1'b0;
                end else if (ev_valid[i]) begin
                    if (ev_due[i] == phase_counter) begin
                        ev_active[i] <= 1'b1;
                    end
                    if (ev_active[i] || (ev_due[i] == phase_counter)) begin
                        DRIV_ALERT <= 1'b1;
                        DRIV_OUT   <= ev_data[i];
                    end
                end
            end

            phase_counter <= phase_counter + 32'd1;
        end
    end

endmodule
