module Dram(
    input  wire       CLK,
    input  wire       RST_N,
    input  wire       R,
    input  wire       W,
    input  wire [7:0] ADDR,
    input  wire [7:0] DQ_IN_DELAY,
    input  wire [7:0] MR_IN,
    input  wire       MRW,   
    input  wire       MRR,
    input  wire       DRIV_VALID,

    output reg        DQ_IE,
    output reg  [7:0] DQ_OUT,
    output reg  [7:0] MR_OUT,
    output reg        DQ_OE, 
    output wire       DQ_OUT_VALID
);
    reg [7:0] array [0:255];
    reg [7:0] mr0_rl;                       // RL=0~255
    reg [7:0] mr1_wl;                       // WL=0~255
    reg [7:0] pipe_out_data  [0:255];       // Out-put data pipeline
    reg       pipe_out_valid [0:255];       // Read requests save pipeline
    reg       pipe_in_valid  [0:255];       // Write requests save pipeline
    reg [7:0] pipe_in_addr   [0:255];       // In-put address pipeline

    reg [7:0] pipe_dq_oe;             // DQ_OE pipeline be used to indicate that the data out-put is valid

    integer i;

    always @(posedge CLK or negedge RST_N) begin
        if (!RST_N) begin
            DQ_OUT <= 8'd0;
            DQ_OE  <= 1'b0;
            mr0_rl <= 8'd8;
            mr1_wl <= 8'd8;

            for (i = 0; i < 256; i = i + 1) begin
                pipe_out_data[i]  <= 8'd0;
                pipe_out_valid[i] <= 1'b0;
            end

            for (i = 0; i < 256; i = i + 1) begin
                pipe_in_addr[i]  <= 8'd0;
                pipe_in_valid[i] <= 1'b0;
            end

            pipe_dq_oe <= 8'd0;

        end else begin
            DQ_OE <= 1'b0;
            DQ_IE <= 1'b0;
            //  ########################### WRITE ######################
            // In-put pipeline shift left 
            for (i=255; i>0; i=i-1) begin
                pipe_in_valid[i] <= pipe_in_valid[i-1];
                pipe_in_addr[i] <= pipe_in_addr[i-1];
            end
            // Level 0 loads new request W = 1
            pipe_in_valid[0] <= W;
            pipe_in_addr[0] <= ADDR;
            // In WL level in-put
            if (pipe_in_valid[mr1_wl - 1]) begin
                DQ_IE  <= 1'b1;
                if (DRIV_VALID) begin
                    array[pipe_in_addr[mr1_wl - 1]] <= DQ_IN_DELAY;
                end
            end

            //  #######################################################

            //  ########################### READ ######################
            // Out-put pipeline shift left 
            for (i=255; i>0; i=i-1) begin
                pipe_out_data[i]  <= pipe_out_data[i - 1];
                pipe_out_valid[i] <= pipe_out_valid[i - 1];
            end
            // Level 0 loads new request R = 1
            pipe_out_valid[0] <= R;
            pipe_out_data[0]  <= array[ADDR];
            // In RL level out-put
            if (pipe_out_valid[mr0_rl - 1]) begin
                DQ_OUT <= pipe_out_data[mr0_rl - 1];
                DQ_OE  <= 1'b1;
            end
            //  #######################################################

            // Write MR
            if (MRW && ADDR == 8'd0) mr0_rl <= MR_IN;
            if (MRW && ADDR == 8'd1) mr1_wl <= MR_IN;

            // Read MR
            if (MRR && ADDR == 8'd0) MR_OUT <= mr0_rl;
            if (MRR && ADDR == 8'd1) MR_OUT <= mr1_wl;

            // The OUT data lasts for 8 cycles. 
            // For the consecutive 8 cycles, no data is out-put (DQ_OE = 0). 
            // The DQ_OUT returns to its default value of 0.
            pipe_dq_oe <= {pipe_dq_oe[6:0], DQ_OE};
            if (pipe_dq_oe == 8'b10000000) begin   
                DQ_OUT <= 8'd0;
            end

        end
    end

    assign  DQ_OUT_VALID = DQ_OE | (pipe_dq_oe > 8'd0);

endmodule
