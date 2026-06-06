DEFINE

    CMD MRW(addr, mr_in) {
        DRIVE MRW;           
        DRIVE ADDR = addr;   
        DRIVE MR_IN = mr_in; 
    }

    CMD MRR(addr) {
        DRIVE MRR;           
        DRIVE ADDR = addr;   
    }

    CMD WT(addr) {
        DRIVE W;             
        DRIVE ADDR = addr;   
    }

    CMD DRIV(val) {
        DRIVE DQ_RX_BIT = val;   <DELAY>
    }
    CMD DRIV_START(val) {
        DRIVE DQ_RX_START;       <DELAY>
        DRIVE DQ_RX_BIT = val;   <DELAY>
    }

    CMD RD(addr) {
        DRIVE R;             
        DRIVE ADDR = addr;   
    }

    CMD SAMP(expect) {
        SAMPLE DQ_TX_BIT = expect; <DELAY>
    }
    
    CMD SAMP_START(expect) {
        SAMPLE DQ_TX_BIT = expect; <DELAY>
    }

    CMD RST() {
        DRIVE RST_N;
    }

END
