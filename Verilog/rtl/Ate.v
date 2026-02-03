module Ate (
    input  wire       CLK,
    input  wire       RST_N,

    // ATE -> DRAM
    input  wire       R,
    input  wire       W,
    input  wire [7:0] ADDR,
    input  wire       MRW,
    input  wire       MRR, 
    input  wire [7:0] MR_IN,

    // ATE -> Sampler
    input  wire       STRB,         // 1-cycle strobe pulse
    input  wire       STRB_SHIFT,
    input  wire [4:0] STRB_BACK,    // 0..31, 采过去N拍（0=当前拍）
    input  wire [4:0] STRB_FRONT,    // 0..31, 采未来N拍（0=当前拍）

    // ATE -> Driver
    input  wire [7:0] DQ_IN,
    input  wire       DRIV,
    input  wire       DRIV_SHIFT,
    input  wire [4:0] DRIV_FRONT,

    // DRAM -> 外部
    output wire       DQ_IE,
    output wire [7:0] DQ_OUT,
    output wire       DQ_OE,
    output wire       DQ_OUT_VALID,
    output wire [7:0] MR_OUT,

    // Sampler -> ATE
    output wire [7:0] STRB_DATA,
    output wire       STRB_VALID,

    // Driver -> 外部/DRAM
    output wire       DRIV_VALID,
    output wire [7:0] DQ_IN_DELAY,

    // Sampler -> Out_Register
    output reg  [4:0] STRB_CNTS,
    output reg  [7:0] OUT_REG [0:31]

);
    
    // =========================
    // DRAM
    // =========================
    Dram u_dram (
        .CLK    (CLK),
        .RST_N  (RST_N),
        .R      (R),
        .W      (W),
        .ADDR   (ADDR),
        .MR_IN  (MR_IN),
        .DRIV_VALID   (DRIV_VALID),
        .DQ_IN_DELAY  (DQ_IN_DELAY),
        .DQ_IE  (DQ_IE),
        .MRW    (MRW),
        .MRR    (MRR),
        .MR_OUT (MR_OUT),
        .DQ_OUT (DQ_OUT),
        .DQ_OE  (DQ_OE),
        .DQ_OUT_VALID   (DQ_OUT_VALID)
    );

    // =========================
    // Sampler (DEPTH=±32, fixed)
    // =========================
    Sampler u_samp (
        .CLK       (CLK),
        .RST_N     (RST_N),
        .DQ_OUT    (DQ_OUT),
        .DQ_OUT_VALID   (DQ_OUT_VALID),
        .STRB      (STRB),
        .STRB_SHIFT     (STRB_SHIFT),
        .STRB_BACK (STRB_BACK),
        .STRB_FRONT(STRB_FRONT),
        .STRB_DATA (STRB_DATA),
        .STRB_VALID(STRB_VALID)
    );

    // =========================
    // Out_Register (DEPTH=32)
    // =========================
    Out_Register u_out_reg (
        .CLK       (CLK),
        .RST_N     (RST_N),
        .STRB_DATA (STRB_DATA),
        .STRB_VALID(STRB_VALID),
        .STRB_CNTS(STRB_CNTS),
        .OUT_REG(OUT_REG)
    );    

    Driver u_driv(
        .CLK       (CLK),
        .RST_N     (RST_N),
        .DRIV      (DRIV),
        .DQ_IN     (DQ_IN),
        .DRIV_SHIFT(DRIV_SHIFT),
        .DRIV_FRONT(DRIV_FRONT),
        .DRIV_VALID(DRIV_VALID),
        .DQ_IN_DELAY(DQ_IN_DELAY)
    );


endmodule
