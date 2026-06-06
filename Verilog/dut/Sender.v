module Sender(
    input                   [ 0 : 0]        CLK,
    input                   [ 0 : 0]        RST_N,

    output      wire        [ 0 : 0]        BIT_OUT,
    output      wire        [ 0 : 0]        BUSY,
    output      wire        [ 0 : 0]        VALID,

    input                   [ 0 : 0]        START,
    input                   [ 7 : 0]        DATA
);
    localparam WAIT_STATE = 0;
    localparam BUSY_STATE = 1;
    localparam DONE_STATE = 2;

    reg [9:0] pipe;
    reg [3:0] bit_counts;
    reg [2:0] current_state;

    assign BIT_OUT = (current_state != BUSY_STATE)? 1'b1: pipe[9];
    assign BUSY = (current_state == BUSY_STATE)? 1'b1: 1'b0;
    assign VALID = (current_state == DONE_STATE)? 1'b1: 1'b0;

    always @(posedge CLK) begin
        if (!RST_N) begin
            pipe <= 10'b0000000000;
            bit_counts <= 4'b0000;
            current_state <= WAIT_STATE;
        end
        else begin
            if (current_state == DONE_STATE)
                current_state <= WAIT_STATE;
            else if (current_state != BUSY_STATE && START) begin
                pipe <= {1'b0, DATA, 1'b1};
                current_state <= BUSY_STATE;
                bit_counts <= 4'd1;
            end
            else if (current_state == BUSY_STATE) begin
                pipe <= {pipe[8:0], 1'b0};
                if (bit_counts == 4'd9) begin
                    bit_counts <= 4'b0;
                    current_state <= DONE_STATE;
                end
                else begin
                    bit_counts <= bit_counts + 4'b0001;
                    current_state <= BUSY_STATE;
                end
            end
        end
    end

endmodule
