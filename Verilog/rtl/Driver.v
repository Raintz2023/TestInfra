// ======================================================
// 固定 DEPTH=32 的极简驱动器：支持向后驱动
// ======================================================
module Driver (
    input  wire       CLK,
    input  wire       RST_N,

    input  wire       DRIV,       // 1-cycle pulse
    input  wire       SHIFT,     //  1: right
    input  wire [4:0] DRIV_FRONT,  // + 0..31

    output reg        DRIV_VALID
);

    reg       fut_driv   [0:31];
    reg [1:0] driv_counter;
    integer i;

    always @(posedge CLK or negedge RST_N) begin
        if (!RST_N) begin
            DRIV_VALID <= 1'b0;

            for (i=0; i<32; i=i+1) begin
                fut_driv[i] <= 1'b0;
            end
            driv_counter <= 2'b00;

        end else begin
            if (driv_counter != 2'b00) begin
                driv_counter <= driv_counter - 1;
            end else begin
                DRIV_VALID <= 1'b0;
            end
            // DRIV触发记录未来驱动
            for (i=31; i>0; i=i-1) begin
                fut_driv[i] <= fut_driv[i-1];
            end
            fut_driv[0] <= 1'b0;

            // 在DRIV_FRONT级输出
            if (DRIV && SHIFT) begin
                if (DRIV_FRONT == 5'd0) begin
                    DRIV_VALID <= DRIV;
                end else begin
                    fut_driv[0] <= DRIV; 
                end
            end
            else if (DRIV && !SHIFT) begin
                DRIV_VALID <= DRIV;
                driv_counter <= 2'b11;
            end
            if (SHIFT && (DRIV_FRONT != 5'd0) && fut_driv[DRIV_FRONT - 1]) begin
                DRIV_VALID <= fut_driv[DRIV_FRONT - 1];
                driv_counter <= 2'b11;
            end
        end
    end

endmodule
