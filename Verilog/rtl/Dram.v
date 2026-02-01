module Dram(
    input  wire       CLK,
    input  wire       RST_N,
    input  wire       R,
    input  wire       W,
    input  wire [7:0] ADDR,
    input  wire [7:0] DQ_IN,
    input  wire       MRW,   
    input  wire       MRR,
    input  wire       DRIV_VALID,

    output reg        DQ_IE,
    output reg  [7:0] DQ_OUT,
    output reg        DQ_OE, 
    output wire       DQ_OUT_VALID
);
    reg [7:0] array [0:255];
    reg [7:0] mr0_rl;                 // RL=0~255
    reg [7:0] mr1_wl;                 // WL=0~255
    reg [7:0] pipe_out_data [0:255];       // 数据输出流水线
    reg       pipe_out_valid[0:255];       // 有效位输出流水线
    reg [7:0] pipe_in_data [0:255];       // 数据输入流水线
    reg       pipe_in_valid[0:255];       // 有效位输入流水线
    reg [7:0] pipe_in_addr[0:255];        // 数据输入地址流水线

    reg [7:0] pipe_dq_oe;             // DQ_OE流水线，用来标记数据输出有效

    integer i;

    always @(posedge CLK or negedge RST_N) begin
        if (!RST_N) begin
            DQ_OUT <= 8'd0;
            DQ_OE  <= 1'b0;
            mr0_rl <= 8'd8;
            mr1_wl <= 8'd8;

            for (i=0; i<256; i=i+1) begin
                pipe_out_data[i]  <= 8'd0;
                pipe_out_valid[i] <= 1'b0;
            end

            for (i=0; i<256; i=i+1) begin
                pipe_in_data[i]  <= 8'd0;
                pipe_in_valid[i] <= 1'b0;
            end

            pipe_dq_oe <= 8'd0;

        end else begin
            DQ_OE <= 1'b0;
            DQ_IE <= 1'b0;
            //  ########################### 写 ######################
            // 输入流水线整体后移 
            for (i=255; i>0; i=i-1) begin
                pipe_in_data[i]  <= pipe_in_data[i-1];
                pipe_in_valid[i] <= pipe_in_valid[i-1];
                pipe_in_addr[i] <= pipe_in_addr[i-1];
            end
            pipe_in_valid[0] <= W;
            pipe_in_data[0]  <= DQ_IN;
            pipe_in_addr[0] <= ADDR;
            // 在 WL 级输入
            if (pipe_in_valid[mr1_wl]) begin
                DQ_IE  <= 1'b1;
                if (DRIV_VALID) begin
                    array[ADDR] <= pipe_in_data[mr1_wl];
                end
            end

            //  ####################################################

            //  ########################### 读 ######################
            // 输出流水线整体后移 
            for (i=255; i>0; i=i-1) begin
                pipe_out_data[i]  <= pipe_out_data[i-1];
                pipe_out_valid[i] <= pipe_out_valid[i-1];
            end
            // 第0级装入新请求 R=1
            pipe_out_valid[0] <= R;
            pipe_out_data[0]  <= array[ADDR];
            // 在 RL 级输出
            if (pipe_out_valid[mr0_rl]) begin
                DQ_OUT <= pipe_out_data[mr0_rl];
                DQ_OE  <= 1'b1;
            end
            //  ####################################################

            // 写 MR
            if (MRW && ADDR == 8'd0) mr0_rl <= DQ_IN;
            if (MRW && ADDR == 8'd1) mr1_wl <= DQ_IN;

            // 读 MR
            if (MRR && ADDR == 8'd0) DQ_OUT <= mr0_rl;
            if (MRR && ADDR == 8'd1) DQ_OUT <= mr1_wl;

            // OUT数据持续8周期，连续八个周期不采数据(DQ_OE=0)，DQ_OUT 恢复默认值0
            pipe_dq_oe <= {pipe_dq_oe[6:0], DQ_OE};
            if (pipe_dq_oe == 8'b10000000) begin   
                DQ_OUT <= 8'd0;
            end

        end
    end

    assign  DQ_OUT_VALID = DQ_OE | (pipe_dq_oe > 8'd0);

endmodule
