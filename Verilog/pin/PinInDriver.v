module PinInDriver #(
    parameter WIDTH = 1,
    parameter DEPTH = 16,
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

    reg [WIDTH-1:0] fut_driv_in [0:DEPTH-1];
    reg             fut_driv    [0:DEPTH-1];

    integer i;

    always @(posedge CLK or negedge RST_N) begin
        if (!RST_N) begin
            DRIV_ALERT <= 1'b0;
            DRIV_OUT   <= {WIDTH{1'b0}};

            for (i=0; i<DEPTH; i=i+1) begin
                fut_driv_in[i] <= {WIDTH{1'b0}};
                fut_driv[i]    <= 1'b0;
            end

        end else begin

            DRIV_ALERT <= 1'b0;
            DRIV_OUT   <= {WIDTH{1'b0}};

            // shift pipeline
            for (i=DEPTH-1; i>0; i=i-1) begin
                fut_driv_in[i] <= fut_driv_in[i-1];
                fut_driv[i]    <= fut_driv[i-1];
            end

            fut_driv_in[0] <= {WIDTH{1'b0}};
            fut_driv[0]    <= 1'b0;

            // record event
            if (DRIV) begin
                if (DRIV_OFFSET == {OFFSET_W{1'b0}}) begin
                    DRIV_ALERT <= 1'b1;
                    DRIV_OUT   <= DRIV_IN;
                end else begin
                    $display("Now in DRIV_OFFSET %d", fut_driv);
                    fut_driv[0]    <= 1'b1;
                    fut_driv_in[0] <= DRIV_IN;
                end
            end

            // delayed output
            if ((DRIV_OFFSET != {OFFSET_W{1'b0}}) && fut_driv[DRIV_OFFSET-1]) begin
                DRIV_ALERT <= 1'b1;
                DRIV_OUT   <= fut_driv_in[DRIV_OFFSET-1];
            end
        end
    end

endmodule