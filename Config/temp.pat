DEFINE

    CMD MRWR(addr, mr_in, dly) {
        DRIVE MRW;           <DELAY dly>
        DRIVE ADDR = addr;   <DELAY dly>
        DRIVE MR_IN = mr_in; <DELAY dly>
    }

    CMD MRRD(addr, dly) {
        DRIVE MRR;           <DELAY dly>
        DRIVE ADDR = addr;   <DELAY dly>
    }

    CMD WR(addr, dly) {
        DRIVE W;             <DELAY dly>
        DRIVE ADDR = addr;   <DELAY dly>
    }

    CMD DRV(dq_in, dly) {
        DRIVE DRIV;          <DELAY dly>
        DRIVE DQ_IN = dq_in; <DELAY dly>
    }

    CMD RD(addr, dly) {
        DRIVE R;             <DELAY dly>
        DRIVE ADDR = addr;   <DELAY dly>
    }

    CMD SMP(expect, dly) {
        SAMPLE DQ_OUT = expect; <DELAY dly>
    }

    CMD SMP_MR(expect, dly) {
        SAMPLE MR_OUT = expect; <DELAY dly>
    }

    CMD RST() {
        DRIVE RST_N;
    }
END
