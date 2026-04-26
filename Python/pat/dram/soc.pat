SOCKET
    IN  R            { PIN: 0,       WAV: NRZ, DEF: 0 }
    IN  W            { PIN: 1,       WAV: NRZ, DEF: 0 }
    IN  ADDR         { PIN: [2:9],   WAV: NRZ, DEF: 0 }
    IN  DQ_IN        { PIN: [10:17], WAV: NRZ, DEF: 0 }
    IN  MR_IN        { PIN: [18:25], WAV: NRZ, DEF: 0 }
    IN  MRW          { PIN: 26,      WAV: NRZ, DEF: 0 }
    IN  MRR          { PIN: 27,      WAV: NRZ, DEF: 0 }
    IN  DRIV         { PIN: 28,      WAV: NRZ, DEF: 0 }
    IN  CLK          { PIN: 29,      WAV: RZZ, DEF: 0 }
    IN  RST_N        { PIN: 30,      WAV: NRZ, DEF: 1 }

    OUT DQ_IE        { PIN: 0,       WAV: STB, EXP: 0 }
    OUT DQ_OUT       { PIN: [1:8],   WAV: STB, EXP: 0 }
    OUT MR_OUT       { PIN: [9:16],  WAV: STB, EXP: 0 }
    OUT DQ_OE        { PIN: 17,      WAV: STB, EXP: 0 }
    OUT DQ_OUT_VALID { PIN: 18,      WAV: STB, EXP: 0 }
END
