SOCKET
    IN  CLK          { PIN: 0       , WAV: RZZ, DEF: 0 }
    IN  RST_N        { PIN: 1       , WAV: NRZ, DEF: 1 }
    IN  START_IN     { PIN: 2       , WAV: NRZ, DEF: 0 }
    IN  START_OUT    { PIN: 3       , WAV: NRZ, DEF: 0 }
    IN  R            { PIN: 4       , WAV: NRZ, DEF: 0 }
    IN  W            { PIN: 5       , WAV: NRZ, DEF: 0 }
    IN  ADDR         { PIN: [6:13]  , WAV: NRZ, DEF: 0 }
    IN  DQ_IN        { PIN: 14      , WAV: NRZ, DEF: 0 }
    IN  MR_IN        { PIN: [15:22] , WAV: NRZ, DEF: 0 }
    IN  MRW          { PIN: 23      , WAV: NRZ, DEF: 0 }
    IN  MRR          { PIN: 24      , WAV: NRZ, DEF: 0 }
    IN  DRIV         { PIN: 25      , WAV: NRZ, DEF: 0 }

    OUT DQ_IE        { PIN: 0       , WAV: STB, EXP: 0 }
    OUT DOUT_TX      { PIN: 1       , WAV: STB, EXP: 0 }
    OUT MR_OUT       { PIN: [2:9]   , WAV: STB, EXP: 0 }
    OUT DQ_OE        { PIN: 10      , WAV: STB, EXP: 0 }
    OUT DQ_OUT_VALID { PIN: 11      , WAV: STB, EXP: 0 }
END
