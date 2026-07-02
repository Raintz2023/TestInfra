SOCKET {
    IN  R            { PIN: 0,       WAV: RZ,  DEF: 0 }
    IN  W            { PIN: 1,       WAV: RZ,  DEF: 0 }
    IN  ADDR         { PIN: [2:9],   WAV: NRZ, DEF: 0 }
    IN  DQ_RX_DATA   { PIN: [10:17], WAV: NRZ, DEF: 0 }
    IN  DQ_RX_VALID  { PIN: 18,      WAV: RZ,  DEF: 0 }
    IN  MR_IN        { PIN: [19:26], WAV: NRZ, DEF: 0 }
    IN  MRW          { PIN: 27,      WAV: RZ,  DEF: 0 }
    IN  MRR          { PIN: 28,      WAV: RZ,  DEF: 0 }
    IN  CLK          { PIN: 29,      WAV: RZZ, DEF: 0 }
    IN  RST_N        { PIN: 30,      WAV: NRZ, DEF: 1 }

    OUT DQ_IE        { PIN: 0,       WAV: STB }
    OUT DQ_TX_DATA   { PIN: [1:8],   WAV: STB }
    OUT DQ_OE        { PIN: 9,       WAV: STB }
    OUT DQ_OUT_VALID { PIN: 10,      WAV: STB }
}
