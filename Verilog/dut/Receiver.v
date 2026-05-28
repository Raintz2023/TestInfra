module Receiver(
    input                   [ 0 : 0]        CLK, 
    input                   [ 0 : 0]        RST_N,

    output      wire        [ 7 : 0]        DOUT,
    output      wire        [ 0 : 0]        BUSY,
    output      wire        [ 0 : 0]        DONE,
    output      wire        [ 0 : 0]        PRE,
    output      wire        [ 0 : 0]        POST,

    input                   [ 0 : 0]        START,
    input                   [ 0 : 0]        DIN
);
    localparam WAIT_STATE = 0;
    localparam BUSY_STATE = 1;
    localparam DONE_STATE = 2;

    reg [9:0] pipe;
    reg [3:0] bit_counts;
    reg [2:0] current_state;
    wire [7:0] DOUT_TEMP;
    
    assign PRE  = (current_state != BUSY_STATE)? pipe[9]: 1'b1;
    assign POST = (current_state != BUSY_STATE)? pipe[0]: 1'b0;
    assign DOUT_TEMP = (current_state != BUSY_STATE)? pipe[8:1]: 8'b11111111;
    assign BUSY = (current_state == BUSY_STATE)? 1'b1: 1'b0;
    assign DONE = (current_state == DONE_STATE)? 1'b1: 1'b0;

    always @(posedge CLK) begin
        if (!RST_N) begin
            pipe <= 10'b0000000000;
            bit_counts <= 4'b0000;
            current_state <= WAIT_STATE;
        end
        else begin
            if (current_state == DONE_STATE) begin
                current_state <= WAIT_STATE;
            end
            else if (current_state != BUSY_STATE && START) begin
                pipe <= {pipe[8:0], DIN};
                current_state <= BUSY_STATE;
                bit_counts <= 4'd1;
            end
            else if (current_state == BUSY_STATE) begin
                pipe <= {pipe[8:0], DIN};
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

    assign DOUT = (PRE == 1'b0 && POST == 1'b1)? DOUT_TEMP: 8'b11111111;

endmodule
