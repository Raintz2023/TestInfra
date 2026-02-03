// ======================================================
// 固定 DEPTH=32 的极简驱动器：支持向后驱动
// ======================================================

// *** 需要把DQ_IN数据存入，和DRIV一起延迟输入DRAM
module Driver (
    input  wire       CLK,
    input  wire       RST_N,

    input  wire       DRIV,       // 1-cycle pulse
    input  wire       DRIV_SHIFT,     //  1: right
    input  wire [4:0] DRIV_FRONT,  // + 0..31
    input  wire [7:0] DQ_IN,

    output reg        DRIV_VALID,
    output reg [7:0]  DQ_IN_DELAY
);

    reg       fut_driv   [0:31];
    reg [7:0] fut_dq_in  [0:31];
    reg [1:0] driv_counter;
    reg [2:0] dq_in_counter;
    integer i;

    always @(posedge CLK or negedge RST_N) begin
        if (!RST_N) begin
            DRIV_VALID <= 1'b0;

            for (i=0; i<32; i=i+1) begin
                fut_driv[i] <= 1'b0;
            end

            for (i=0; i<32; i=i+1) begin
                fut_dq_in[i] <= 8'd0;
            end

            driv_counter <= 2'b00;
            dq_in_counter <= 3'b000;

        end else begin
            if (driv_counter != 2'b00) begin
                driv_counter <= driv_counter - 1;
            end else begin
                DRIV_VALID <= 1'b0;
            end
            if (dq_in_counter != 3'b000) begin
                dq_in_counter <= dq_in_counter - 1;
            end else begin
                DQ_IN_DELAY <= 8'd0;
            end

            // DRIV触发记录未来驱动
            for (i=31; i>0; i=i-1) begin
                fut_driv[i] <= fut_driv[i-1];
            end
            fut_driv[0] <= 1'b0;

            for (i=31; i>0; i=i-1) begin
                fut_dq_in[i] <= fut_dq_in[i-1];
            end
            fut_dq_in[0] <= 8'd0;

            // 在DRIV_FRONT级输出
            if (DRIV && DRIV_SHIFT) begin
                if (DRIV_FRONT == 5'd0) begin
                    DRIV_VALID <= DRIV;
                    DQ_IN_DELAY <= DQ_IN;
                end else begin
                    fut_driv[0] <= DRIV;
                    fut_dq_in[0] <= DQ_IN;
                end
            end
            else if (DRIV && !DRIV_SHIFT) begin
                DRIV_VALID <= DRIV;
                DQ_IN_DELAY <= DQ_IN;
                driv_counter <= 2'b11;
                dq_in_counter <= 3'b111;
            end

            if (DRIV_SHIFT && (DRIV_FRONT != 5'd0) && fut_driv[DRIV_FRONT - 1]) begin
                DRIV_VALID <= fut_driv[DRIV_FRONT - 1];
                DQ_IN_DELAY <= fut_dq_in[DRIV_FRONT - 1];
                driv_counter <= 2'b11;
                dq_in_counter <= 3'b111;
            end
        end
    end

endmodule
