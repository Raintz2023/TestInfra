COMMAND
    DEF MRWR = MRW  (ADDR) (MR_IN)   // Enable Address MR_IN
    DEF MRRD = MRR  (ADDR)
    DEF WR   = W    (ADDR)           // Enable Address
    DEF DRV  = DRIV (DQ_IN)          // Enable DQ_IN Delay
    DEF RD   = R    (ADDR)           // Enable Address
    DEF SMP  = DQ_OUT                // DQ_OUT Expected Delay
    DEF SMP_MR = MR_OUT
    DEF RST = RST_N
END
