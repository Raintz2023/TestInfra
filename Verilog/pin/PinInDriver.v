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

    // Keep one delayed drive slot per future cycle so repeated requests
    // are observed one-by-one on DRIV_ALERT with their original data.
    reg [DEPTH-1:0] pending_driv_valid;
    reg [DEPTH-1:0] next_pending_driv_valid;
    reg [WIDTH-1:0] pending_driv_data [0:DEPTH-1];
    reg [WIDTH-1:0] next_pending_driv_data [0:DEPTH-1];
    integer i;
    localparam [OFFSET_W-1:0] ONE = {{(OFFSET_W-1){1'b0}}, 1'b1};

    always @(*) begin
        next_pending_driv_valid = {1'b0, pending_driv_valid[DEPTH-1:1]};
        for (i = 0; i < DEPTH - 1; i = i + 1) begin
            next_pending_driv_data[i] = pending_driv_data[i + 1];
        end
        next_pending_driv_data[DEPTH - 1] = {WIDTH{1'b0}};

        if (DRIV && (DRIV_OFFSET != {OFFSET_W{1'b0}})) begin
            next_pending_driv_valid[DRIV_OFFSET - ONE] = 1'b1;
            next_pending_driv_data[DRIV_OFFSET - ONE] = DRIV_IN;
        end
    end

    always @(posedge CLK or negedge RST_N) begin
        if (!RST_N) begin
            DRIV_ALERT <= 1'b0;
            DRIV_OUT   <= {WIDTH{1'b0}};
            pending_driv_valid <= {DEPTH{1'b0}};
            for (i = 0; i < DEPTH; i = i + 1) begin
                pending_driv_data[i] <= {WIDTH{1'b0}};
            end

        end else begin
            DRIV_ALERT <= 1'b0;
            DRIV_OUT   <= {WIDTH{1'b0}};

            if (pending_driv_valid[0]) begin
                DRIV_ALERT <= 1'b1;
                DRIV_OUT   <= pending_driv_data[0];
            end

            if (DRIV) begin
                if (DRIV_OFFSET == {OFFSET_W{1'b0}}) begin
                    DRIV_ALERT <= 1'b1;
                    DRIV_OUT   <= DRIV_IN;
                end
            end

            pending_driv_valid <= next_pending_driv_valid;
            for (i = 0; i < DEPTH; i = i + 1) begin
                pending_driv_data[i] <= next_pending_driv_data[i];
            end
        end
    end

endmodule
