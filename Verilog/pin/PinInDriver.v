module PinInDriver #(
    parameter WIDTH = 1,
    parameter DEPTH = 32,
    parameter OFFSET_W = $clog2(DEPTH)
)(
    input  wire               CLK,
    input  wire               RST_N,

    input  wire               DRIV,
    input  wire [WIDTH-1:0]   DRIV_IN,
    input  wire [OFFSET_W-1:0] DRIV_OFFSET,

    output reg  [WIDTH-1:0]   DRIV_OUT,
    output reg                DRIV_ALERT
);

    reg [WIDTH-1:0] pending_driv_in;
    reg [OFFSET_W-1:0] pending_cycles;
    reg pending_driv;

    always @(posedge CLK or negedge RST_N) begin
        if (!RST_N) begin
            DRIV_ALERT <= 1'b0;
            DRIV_OUT   <= {WIDTH{1'b0}};
            pending_driv <= 1'b0;
            pending_driv_in <= {WIDTH{1'b0}};
            pending_cycles <= {OFFSET_W{1'b0}};

        end else begin

            DRIV_ALERT <= 1'b0;
            DRIV_OUT   <= {WIDTH{1'b0}};

            if (pending_driv) begin
                if (pending_cycles == {{(OFFSET_W-1){1'b0}}, 1'b1}) begin
                    DRIV_ALERT <= 1'b1;
                    DRIV_OUT   <= pending_driv_in;
                    pending_driv <= 1'b0;
                    pending_driv_in <= {WIDTH{1'b0}};
                    pending_cycles <= {OFFSET_W{1'b0}};
                end else begin
                    pending_cycles <= pending_cycles - {{(OFFSET_W-1){1'b0}}, 1'b1};
                end
            end

            // Keep one delayed event in flight per pin. This matches current
            // protocol usage and avoids simulator sensitivity around array
            // indexing on delayed queues.
            if (DRIV) begin
                if (DRIV_OFFSET == {OFFSET_W{1'b0}}) begin
                    DRIV_ALERT <= 1'b1;
                    DRIV_OUT   <= DRIV_IN;
                end else begin
                    pending_driv <= 1'b1;
                    pending_driv_in <= DRIV_IN;
                    pending_cycles <= DRIV_OFFSET;
                end
            end
        end
    end

endmodule
