// ======================================================================================
// Fixed DEPTH=32 minimalist sampler: Supports forward sampling and backward sampling
// ======================================================================================
module Sampler (
    input  wire       CLK,
    input  wire       RST_N,

    input  wire [7:0] DQ_OUT,
    input  wire       DQ_OUT_VALID,

    input  wire       STRB,       // 1-cycle pulse
    input  wire       STRB_SHIFT,     // 0: left 1: right
    input  wire [4:0] STRB_BACK,  // - 0..31
    input  wire [4:0] STRB_FRONT,  // + 0..31

    output reg  [7:0] STRB_DATA,
    output reg        STRB_VALID // Only be valid if DQ out is valid
);

    reg [7:0] hist_data [0:31];
    reg       hist_data_valid   [0:31];
    reg [4:0] now_ptr;

    wire [4:0] pre_ptr = now_ptr - STRB_BACK;

    reg       fut_oe   [0:31];

    integer i;

    always @(posedge CLK or negedge RST_N) begin
        if (!RST_N) begin
            now_ptr     <= 5'd0;
            STRB_DATA  <= 8'd0;
            STRB_VALID <= 1'b0;
            for (i=0; i<32; i=i+1) begin
                hist_data[i] <= 8'd0;
                hist_data_valid[i]   <= 1'b0;
            end

            for (i=0; i<32; i=i+1) begin
                fut_oe[i] <= 1'b0;
            end

        end else begin
            STRB_VALID <= 1'b0;

            // 每拍记录一次DQ输出状态，环形缓冲
            hist_data[now_ptr] <= DQ_OUT;
            hist_data_valid[now_ptr]   <= DQ_OUT_VALID;
            now_ptr <= now_ptr + 5'd1;

            // STRB触发历史采样
            if (STRB && !STRB_SHIFT) begin
                if (STRB_BACK == 5'd0) begin   // 当前拍直接输出，不可用pre_ptr，因为当前拍还未存储
                    STRB_DATA  <= DQ_OUT;
                    STRB_VALID <= DQ_OUT_VALID;
                end else begin
                    STRB_DATA  <= hist_data[pre_ptr]; // 之前的拍已经存储，用pre_ptr
                    STRB_VALID <= hist_data_valid[pre_ptr];
                end
            end

            // 流水线整体向右移位
            for (i=31; i>0; i=i-1) begin
                fut_oe[i] <= fut_oe[i-1];
            end
            fut_oe[0] <= 1'b0;

            // STRB触发未来采样
            if (STRB && STRB_SHIFT) begin
                if (STRB_FRONT == 5'd0) begin   // 当前拍直接输出
                    STRB_DATA  <= DQ_OUT;
                    STRB_VALID <= DQ_OUT_VALID;
                end else begin
                    fut_oe[0] <= STRB;  
                end
            end
            // 在STRB_FRONT级输出
            if (STRB_SHIFT && (STRB_FRONT != 5'd0) && fut_oe[STRB_FRONT - 1]) begin   // 切记是k-1，非阻塞赋值存在一个延迟
                STRB_DATA <= DQ_OUT;
                STRB_VALID <= DQ_OUT_VALID; 
            end

        end
    end

endmodule
