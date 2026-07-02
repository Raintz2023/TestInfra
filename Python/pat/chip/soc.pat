SOCKET {
    IN  CLK          { PIN: 0,       WAV: RZZ,     DEF: 0 }
    IN  RST_N        { PIN: 1,       WAV: RZ,      DEF: 1 }
    IN  R            { PIN: 2,       WAV: RZ,      DEF: 0 }
    IN  W            { PIN: 3,       WAV: RZ,      DEF: 0 }
    IN  ADDR         { PIN: [4:11],  WAV: NRZ,     DEF: 0 }
    IN  DQ_RX_BIT    { PIN: 12,      WAV: NRZ@DQ,  DEF: 1 }
    IN  DQS_RX_BIT   { PIN: 13,      WAV: NRZ@DQS, DEF: 1 }
    IN  MR_IN        { PIN: [14:21], WAV: NRZ,     DEF: 0 }
    IN  MRW          { PIN: 22,      WAV: RZ,      DEF: 0 }
    IN  MRR          { PIN: 23,      WAV: RZ,      DEF: 0 }

    OUT DQ_IE        { PIN: 0, WAV: STB }
    OUT DQ_TX_BIT    { PIN: 1, WAV: STB@DQ }
    OUT DQS_TX_BIT   { PIN: 2, WAV: STB@DQS }
    OUT DQ_OE        { PIN: 3, WAV: STB }
    OUT DQ_OUT_VALID { PIN: 4, WAV: STB }
}
