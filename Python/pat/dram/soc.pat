SOCKET
    PIN R     = I0     = [NRZ] 0
    PIN W     = I1     = [NRZ] 0
    PIN ADDR  = I2:9   = [NRZ] 0
    PIN DQ_IN = I10:17 = [NRZ] 0
    PIN MR_IN = I18:25 = [NRZ] 0
    PIN MRW   = I26    = [NRZ] 0
    PIN MRR   = I27    = [NRZ] 0
    PIN DRIV  = I28    = [NRZ] 0
    PIN CLK   = I29    = [RZZ] 0
    PIN RST_N = I30    = [NRZ] 1

    PIN DQ_IE        = O0     = [STB] 0
    PIN DQ_OUT       = O1:8   = [STB] 0
    PIN MR_OUT       = O9:16  = [STB] 0
    PIN DQ_OE        = O17    = [STB] 0
    PIN DQ_OUT_VALID = O18    = [STB] 0
END

PIN 