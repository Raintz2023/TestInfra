COMMAND {

    MRWR(addr, mr_in) {
        PULSE MRW;
        DRIVE ADDR = addr;
        DRIVE MR_IN = mr_in;
    }

    MRRD(addr) {
        PULSE MRR;
        DRIVE ADDR = addr;
    }

    WR(addr) {
        PULSE W;
        DRIVE ADDR = addr;
    }

    DRV(dq_in) {
        PULSE DQ_RX_VALID; <DELAY>
        DRIVE DQ_RX_DATA = dq_in; <DELAY>
    }

    RD(addr) {
        PULSE R;
        DRIVE ADDR = addr;
    }

    SMP(expect) {
        SAMPLE DQ_TX_DATA = expect; <DELAY>
    }

    SMP_MR(expect) {
        SAMPLE DQ_TX_DATA = expect; <DELAY>
    }

    RST() {
        DRIVE RST_N = 0;
    }

}
