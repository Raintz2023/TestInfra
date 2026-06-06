DEFINE

    CMD MRWR(addr, mr_in) {
        DRIVE MRW;           
        DRIVE ADDR = addr;   
        DRIVE MR_IN = mr_in; 
    }

    CMD MRRD(addr) {
        DRIVE MRR;           
        DRIVE ADDR = addr;   
    }

    CMD WR(addr) {
        DRIVE W;             
        DRIVE ADDR = addr;   
    }

    CMD DRV(dq_in) {
        DRIVE DQ_RX_VALID;       <DELAY>
        DRIVE DQ_RX_DATA = dq_in; <DELAY>
    }

    CMD RD(addr) {
        DRIVE R;             
        DRIVE ADDR = addr;   
    }

    CMD SMP(expect) {
        SAMPLE DQ_TX_DATA = expect; <DELAY>
    }

    CMD SMP_MR(expect) {
        SAMPLE DQ_TX_DATA = expect; <DELAY>
    }

    CMD RST() {
        DRIVE RST_N;
    }

END
