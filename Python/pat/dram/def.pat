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
        DRIVE DRIV;          <DELAY>
        DRIVE DQ_IN = dq_in; <DELAY>
    }

    CMD RD(addr) {
        DRIVE R;             
        DRIVE ADDR = addr;   
    }

    CMD SMP(expect) {
        SAMPLE DQ_OUT = expect; <DELAY>
    }

    CMD SMP_MR(expect) {
        SAMPLE MR_OUT = expect; <DELAY>
    }

    CMD RST() {
        DRIVE RST_N;
    }

END
