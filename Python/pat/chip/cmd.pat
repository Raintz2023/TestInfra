COMMAND {

    MRW(addr, mr_in) {
        PULSE MRW;
        DRIVE ADDR = addr;
        DRIVE MR_IN = mr_in;
    }

    MRR(addr) {
        PULSE MRR;
        DRIVE ADDR = addr;
    }

    WT(addr) {
        PULSE W;
        DRIVE ADDR = addr;
    }

    W(val) {
        DRIVE DQ_RX_BIT = val;
    }

    WDQSH() {
        DRIVE DQS_RX_BIT = 1;
    }

    WDQSL() {
        DRIVE DQS_RX_BIT = 0;
    }

    RD(addr) {
        PULSE R;
        DRIVE ADDR = addr;
    }

    R(expect) {
        SAMPLE DQ_TX_BIT = expect;
    }

    RDQSH() {
        SAMPLE DQS_TX_BIT = 1;
    }

    RDQSL() {
        SAMPLE DQS_TX_BIT = 0;
    }

    RST() {
        PULSE RST_N;
    }

}
