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

    CMD WT(addr) {
        DRIVE W;             
        DRIVE ADDR = addr;   
    }

    CMD DRIV(val) {
        DRIVE DQ_IN = val;   <DELAY>
    }
    CMD DRIV_START(val) {
        DRIVE START_IN;      <DELAY>
        DRIVE DQ_IN = val;   <DELAY>
    }
    CMD DRIV_END() {
        DRIVE DRIV;          <DELAY>
    }

    CMD RD(addr) {
        DRIVE R;             
        DRIVE ADDR = addr;   
    }

    CMD SAMP(expect) {
        SAMPLE DOUT_TX = expect; <DELAY>
    }
    CMD SAMP_START(expect) {
        DRIVE START_OUT;         <DELAY>
        SAMPLE DOUT_TX = expect; <DELAY>
    }

    CMD SMP_MR(expect) {
        SAMPLE MR_OUT = expect; <DELAY>
    }

    CMD RST() {
        DRIVE RST_N;
    }

END
