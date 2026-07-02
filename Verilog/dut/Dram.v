module Dram #(
    parameter integer RX_DQS_SKEW = 0,
    parameter integer RX_DQ_SKEW  = 1,
    parameter integer TX_DQS_SKEW = 2,
    parameter integer TX_DQ_SKEW  = 0
)(
    input  wire       CLK,
    input  wire       RST_N,
    input  wire       R,
    input  wire       W,
    input  wire [7:0] ADDR,
    input  wire       DQ_RX_BIT,
    input  wire       DQS_RX_BIT,
    input  wire [7:0] MR_IN,
    input  wire       MRW,   
    input  wire       MRR,

    output reg        DQ_IE,
    output reg        DQ_TX_BIT,
    output reg        DQS_TX_BIT,
    output reg        DQ_OE, 
    output reg        DQ_OUT_VALID
);
    localparam DQ_IDLE  = 1'b1;
    localparam DQS_IDLE = 1'b1;
    localparam SKEW_DEPTH = 4;
    localparam [7:0] MR4_MIN_TURNAROUND = 8'd24;

    localparam RX_IDLE = 2'd0;
    localparam RX_DATA = 2'd1;
    localparam RX_POST = 2'd2;

    reg [7:0] array [0:255];
    reg [7:0] mr0_rl;                       // RL=0~255
    reg [7:0] mr1_wl;                       // WL=0~255
    reg       mr2_error;                    // Sticky illegal-operation status
    reg       mr2_last_read_req;            // Most recent accepted array command was read
    reg       mr2_last_write_req;           // Most recent accepted array command was write
    reg       mr2_last_mrw_req;             // Last cycle wrote a mode register
    reg       mr2_last_write_data;          // Last cycle accepted write data into the array
    reg [7:0] mr4_turnaround;               // Minimum DQ command spacing for R/W/MRR
    reg [7:0] mr3_shift_data;               // Rotating MRR3 pattern, first value is 0x5A
    reg [7:0] dq_turnaround_timer;
    reg [7:0] pipe_out_data  [0:255];       // Out-put data pipeline
    reg       pipe_out_valid [0:255];       // Read requests save pipeline
    reg [7:0] pipe_mr_data   [0:255];       // Mode-register read data pipeline
    reg       pipe_mr_valid  [0:255];       // Mode-register read valid pipeline
    reg       pipe_in_valid  [0:255];       // Write requests save pipeline
    reg [7:0] pipe_in_addr   [0:255];       // In-put address pipeline

    reg [3:0] write_window_timer;     // 14-cycle DQS write frame opened WL cycles after W
    reg [7:0] write_window_addr;
    reg [1:0] rx_state;
    reg [3:0] rx_count;
    reg [2:0] rx_dqs_shift;
    reg [7:0] rx_data;
    reg [7:0] rx_addr;
    reg       rx_frame_valid;
    reg       rx_write_commit;

    reg       tx_active;
    reg [3:0] tx_count;
    reg [7:0] tx_payload;
    reg [SKEW_DEPTH:0] dq_rx_pipe;
    reg [SKEW_DEPTH:0] dqs_rx_pipe;
    reg       dq_tx_raw;
    reg       dqs_tx_raw;
    reg [SKEW_DEPTH:0] dq_tx_pipe;
    reg [SKEW_DEPTH:0] dqs_tx_pipe;
    wire      write_window_open;
    wire [7:0] active_write_addr;
    wire [7:0] status_reg;
    wire      dq_rx_skewed;
    wire      dqs_rx_skewed;
    wire      dq_tx_skewed;
    wire      dqs_tx_skewed;
    wire      dq_cmd_conflict;
    wire      dq_cmd_ready;
    wire      accept_read_cmd;
    wire      accept_write_cmd;
    wire      accept_mrr_cmd;
    wire      accept_mrw_cmd;
    wire      reject_dq_cmd;
    integer i;

    assign write_window_open = pipe_in_valid[mr1_wl] | (write_window_timer != 4'd0);
    assign active_write_addr = pipe_in_valid[mr1_wl] ? pipe_in_addr[mr1_wl] : write_window_addr;
    assign dq_rx_skewed  = skew_pick(dq_rx_pipe, RX_DQ_SKEW);
    assign dqs_rx_skewed = skew_pick(dqs_rx_pipe, RX_DQS_SKEW);
    assign dq_tx_skewed  = skew_pick(dq_tx_pipe, TX_DQ_SKEW);
    assign dqs_tx_skewed = skew_pick(dqs_tx_pipe, TX_DQS_SKEW);
    assign dq_cmd_conflict = (R & W) | (R & MRR) | (W & MRR);
    assign dq_cmd_ready = (dq_turnaround_timer == 8'd0);
    assign accept_read_cmd = R & dq_cmd_ready & ~W & ~MRR;
    assign accept_write_cmd = W & dq_cmd_ready & ~R & ~MRR;
    assign accept_mrr_cmd = MRR & dq_cmd_ready & ~R & ~W;
    assign accept_mrw_cmd = MRW & ((ADDR == 8'd0) | (ADDR == 8'd1) | (ADDR == 8'd2) | (ADDR == 8'd4));
    assign reject_dq_cmd = (R | W | MRR) & (dq_cmd_conflict | ~dq_cmd_ready);
    assign status_reg = {
        mr2_error,
        any_read_pending(),
        write_window_open,
        mr2_last_write_data,
        mr2_last_mrw_req,
        mr2_last_write_req,
        mr2_last_read_req,
        1'b0
    };

    function any_read_pending;
        integer j;
        begin
            any_read_pending = 1'b0;
            for (j = 0; j < 256; j = j + 1) begin
                any_read_pending = any_read_pending | pipe_out_valid[j];
            end
        end
    endfunction

    function dqs_frame_bit;
        input [3:0] index;
        begin
            case (index)
                4'd2, 4'd3, 4'd5, 4'd7, 4'd9, 4'd11: dqs_frame_bit = 1'b1;
                default: dqs_frame_bit = 1'b0;
            endcase
        end
    endfunction

    function skew_pick;
        input [SKEW_DEPTH:0] values;
        input integer skew;
        begin
            if (skew <= 0) begin
                skew_pick = values[0];
            end else if (skew >= SKEW_DEPTH) begin
                skew_pick = values[SKEW_DEPTH];
            end else begin
                skew_pick = values[skew];
            end
        end
    endfunction

    function payload_frame_bit;
        input [7:0] payload;
        input [3:0] index;
        begin
            case (index)
                4'd4: payload_frame_bit = payload[0];
                4'd5: payload_frame_bit = payload[1];
                4'd6: payload_frame_bit = payload[2];
                4'd7: payload_frame_bit = payload[3];
                4'd8: payload_frame_bit = payload[4];
                4'd9: payload_frame_bit = payload[5];
                4'd10: payload_frame_bit = payload[6];
                4'd11: payload_frame_bit = payload[7];
                default: payload_frame_bit = DQ_IDLE;
            endcase
        end
    endfunction

    always @(posedge CLK) begin
        if (!RST_N) begin
            DQ_TX_BIT <= DQ_IDLE;
            DQS_TX_BIT <= DQS_IDLE;
            dq_tx_raw <= DQ_IDLE;
            dqs_tx_raw <= DQS_IDLE;
            DQ_OE  <= 1'b0;
            DQ_IE  <= 1'b0;
            DQ_OUT_VALID <= 1'b0;
            mr0_rl <= 8'd8;
            mr1_wl <= 8'd8;
            mr2_error <= 1'b0;
            mr2_last_read_req <= 1'b0;
            mr2_last_write_req <= 1'b0;
            mr2_last_mrw_req <= 1'b0;
            mr2_last_write_data <= 1'b0;
            mr4_turnaround <= MR4_MIN_TURNAROUND;
            mr3_shift_data <= 8'b01011010;
            dq_turnaround_timer <= 8'd0;

            for (i = 0; i < 256; i = i + 1) begin
                pipe_out_data[i]  <= 8'd0;
                pipe_out_valid[i] <= 1'b0;
                pipe_mr_data[i]   <= 8'd0;
                pipe_mr_valid[i]  <= 1'b0;
            end

            for (i = 0; i < 256; i = i + 1) begin
                pipe_in_addr[i]  <= 8'd0;
                pipe_in_valid[i] <= 1'b0;
            end

            write_window_timer <= 4'd0;
            write_window_addr <= 8'd0;
            rx_state <= RX_IDLE;
            rx_count <= 4'd0;
            rx_dqs_shift <= 3'd0;
            rx_data <= 8'd0;
            rx_addr <= 8'd0;
            rx_frame_valid <= 1'b0;
            rx_write_commit <= 1'b0;
            tx_active <= 1'b0;
            tx_count <= 4'd0;
            tx_payload <= 8'd0;
            dq_rx_pipe <= {(SKEW_DEPTH + 1){DQ_IDLE}};
            dqs_rx_pipe <= {(SKEW_DEPTH + 1){DQS_IDLE}};
            dq_tx_pipe <= {(SKEW_DEPTH + 1){DQ_IDLE}};
            dqs_tx_pipe <= {(SKEW_DEPTH + 1){DQS_IDLE}};
        end else begin
            dq_rx_pipe <= {dq_rx_pipe[SKEW_DEPTH - 1:0], DQ_RX_BIT};
            dqs_rx_pipe <= {dqs_rx_pipe[SKEW_DEPTH - 1:0], DQS_RX_BIT};
            dq_tx_pipe <= {dq_tx_pipe[SKEW_DEPTH - 1:0], dq_tx_raw};
            dqs_tx_pipe <= {dqs_tx_pipe[SKEW_DEPTH - 1:0], dqs_tx_raw};

            DQ_TX_BIT <= dq_tx_skewed;
            DQS_TX_BIT <= dqs_tx_skewed;
            DQ_OE <= 1'b0;
            DQ_IE <= 1'b0;
            rx_write_commit <= 1'b0;
            mr2_last_mrw_req <= accept_mrw_cmd;
            mr2_last_write_data <= rx_write_commit;
            if (reject_dq_cmd) begin
                mr2_error <= 1'b1;
            end
            if (dq_turnaround_timer != 8'd0) begin
                dq_turnaround_timer <= dq_turnaround_timer - 8'd1;
            end
            if (accept_read_cmd | accept_write_cmd | accept_mrr_cmd) begin
                dq_turnaround_timer <= mr4_turnaround;
            end
            if (accept_read_cmd) begin
                mr2_last_read_req <= 1'b1;
                mr2_last_write_req <= 1'b0;
            end else if (accept_write_cmd) begin
                mr2_last_read_req <= 1'b0;
                mr2_last_write_req <= 1'b1;
            end

            if (tx_active) begin
                DQ_OUT_VALID <= 1'b1;
                dqs_tx_raw <= dqs_frame_bit(tx_count);
                if (tx_count >= 4'd4 && tx_count <= 4'd11) begin
                    dq_tx_raw <= payload_frame_bit(tx_payload, tx_count);
                end else begin
                    dq_tx_raw <= DQ_IDLE;
                end

                if (tx_count == 4'd13) begin
                    tx_active <= 1'b0;
                    tx_count <= 4'd0;
                end else begin
                    tx_count <= tx_count + 4'd1;
                end
            end else begin
                dq_tx_raw <= DQ_IDLE;
                dqs_tx_raw <= DQS_IDLE;
                DQ_OUT_VALID <= 1'b0;
            end

            //  ########################### WRITE ######################
            // In-put pipeline shift left 
            for (i=255; i>0; i=i-1) begin
                pipe_in_valid[i] <= pipe_in_valid[i-1];
                pipe_in_addr[i] <= pipe_in_addr[i-1];
            end
            // Level 0 loads accepted write requests.
            pipe_in_valid[0] <= accept_write_cmd;
            pipe_in_addr[0] <= ADDR;

            if (pipe_in_valid[mr1_wl]) begin
                write_window_timer <= 4'd13;
                write_window_addr <= pipe_in_addr[mr1_wl];
            end else if (write_window_timer != 4'd0) begin
                write_window_timer <= write_window_timer - 4'd1;
            end

            if (write_window_open) begin
                DQ_IE <= 1'b1;
                rx_dqs_shift <= {rx_dqs_shift[1:0], dqs_rx_skewed};

                if (rx_state == RX_IDLE) begin
                    if ({rx_dqs_shift[2:0], dqs_rx_skewed} == 4'b0011) begin
                        rx_state <= RX_DATA;
                        rx_count <= 4'd0;
                        rx_data <= 8'd0;
                        rx_addr <= active_write_addr;
                        rx_frame_valid <= 1'b1;
                    end
                end else if (rx_state == RX_DATA) begin
                    if (dqs_rx_skewed != rx_count[0]) begin
                        rx_frame_valid <= 1'b0;
                    end
                    rx_data[rx_count[2:0]] <= dq_rx_skewed;
                    if (rx_count == 4'd7) begin
                        rx_state <= RX_POST;
                        rx_count <= 4'd0;
                    end else begin
                        rx_count <= rx_count + 4'd1;
                    end
                end else if (rx_state == RX_POST) begin
                    if (dqs_rx_skewed != 1'b0) begin
                        rx_frame_valid <= 1'b0;
                    end
                    if (rx_count == 4'd1) begin
                        if (rx_frame_valid && dqs_rx_skewed == 1'b0) begin
                            array[rx_addr] <= rx_data;
                            rx_write_commit <= 1'b1;
                        end
                        rx_state <= RX_IDLE;
                        rx_count <= 4'd0;
                        rx_frame_valid <= 1'b0;
                        rx_dqs_shift <= 3'd0;
                    end else begin
                        rx_count <= 4'd1;
                    end
                end
            end else begin
                rx_state <= RX_IDLE;
                rx_count <= 4'd0;
                rx_frame_valid <= 1'b0;
                rx_dqs_shift <= 3'd0;
            end

            //  #######################################################

            //  ########################### READ ######################
            // Out-put pipeline shift left 
            for (i=255; i>0; i=i-1) begin
                pipe_out_data[i]  <= pipe_out_data[i - 1];
                pipe_out_valid[i] <= pipe_out_valid[i - 1];
            end
            // Level 0 loads accepted read requests.
            pipe_out_valid[0] <= accept_read_cmd;
            pipe_out_data[0]  <= array[ADDR];
            // PinInDriver makes the read command visible to the DUT one clock
            // after the tester-side pulse, so the read-return window must align
            // to that observed cycle as well.
            if (pipe_out_valid[mr0_rl]) begin
                tx_active <= 1'b1;
                tx_count <= 4'd1;
                tx_payload <= pipe_out_data[mr0_rl];
                dq_tx_raw <= DQ_IDLE;
                dqs_tx_raw <= dqs_frame_bit(4'd0);
                DQ_OUT_VALID <= 1'b1;
                DQ_OE  <= 1'b1;
            end
            //  #######################################################

            //  ########################### MRR #######################
            for (i=255; i>0; i=i-1) begin
                pipe_mr_data[i]  <= pipe_mr_data[i - 1];
                pipe_mr_valid[i] <= pipe_mr_valid[i - 1];
            end
            pipe_mr_valid[0] <= accept_mrr_cmd;
            if (ADDR == 8'd0) begin
                pipe_mr_data[0] <= mr0_rl;
            end else if (ADDR == 8'd1) begin
                pipe_mr_data[0] <= mr1_wl;
            end else if (ADDR == 8'd2) begin
                pipe_mr_data[0] <= status_reg;
            end else if (ADDR == 8'd3) begin
                pipe_mr_data[0] <= mr3_shift_data;
            end else if (ADDR == 8'd4) begin
                pipe_mr_data[0] <= mr4_turnaround;
            end else begin
                pipe_mr_data[0] <= 8'd0;
            end
            if (accept_mrr_cmd && ADDR == 8'd3) begin
                mr3_shift_data <= {mr3_shift_data[0], mr3_shift_data[7:1]};
            end
            if (pipe_mr_valid[mr0_rl]) begin
                tx_active <= 1'b1;
                tx_count <= 4'd1;
                tx_payload <= pipe_mr_data[mr0_rl];
                dq_tx_raw <= DQ_IDLE;
                dqs_tx_raw <= dqs_frame_bit(4'd0);
                DQ_OUT_VALID <= 1'b1;
                DQ_OE <= 1'b1;
            end
            //  #######################################################

            // Write MR. MR0/MR1/MR4 are writable. MR2 is status-clear, MR3 is read-only rotating ID.
            if (MRW && ADDR == 8'd0) begin
                mr0_rl <= MR_IN;
            end else if (MRW && ADDR == 8'd1) begin
                mr1_wl <= MR_IN;
            end else if (MRW && ADDR == 8'd2) begin
                if (MR_IN[3]) begin
                    mr2_error <= 1'b0;
                end
            end else if (MRW && ADDR == 8'd4) begin
                if (MR_IN < MR4_MIN_TURNAROUND) begin
                    mr4_turnaround <= MR4_MIN_TURNAROUND;
                end else begin
                    mr4_turnaround <= MR_IN;
                end
            end else if (MRW) begin
                mr2_error <= 1'b1;
            end

        end
    end
    
endmodule
