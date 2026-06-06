SOCKET
    IN  CLK          { PIN: 0       , WAV: RZZ, DEF: 0 }
    IN  RST_N        { PIN: 1       , WAV: NRZ, DEF: 1 }
    IN  DQ_RX_START  { PIN: 2       , WAV: RZ,  DEF: 0 }
    IN  R            { PIN: 3       , WAV: RZ,  DEF: 0 }
    IN  W            { PIN: 4       , WAV: RZ,  DEF: 0 }
    IN  ADDR         { PIN: [5:12]  , WAV: NRZ, DEF: 0 }
    IN  DQ_RX_BIT    { PIN: 13      , WAV: NRZ, DEF: 0 }
    IN  MR_IN        { PIN: [14:21] , WAV: NRZ, DEF: 0 }
    IN  MRW          { PIN: 22      , WAV: RZ,  DEF: 0 }
    IN  MRR          { PIN: 23      , WAV: RZ,  DEF: 0 }

    OUT DQ_IE        { PIN: 0       , WAV: STB, EXP: 0 }
    OUT DQ_TX_BIT    { PIN: 1       , WAV: STB, EXP: 0 }
    OUT DQ_OE        { PIN: 2       , WAV: STB, EXP: 0 }
    OUT DQ_OUT_VALID { PIN: 3       , WAV: STB, EXP: 0 }
END
