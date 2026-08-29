SOCKET {
    IN  CLK          { PIN: 0,       WAV: RZZ,     DEF: 0,   SUP: VIN    }
    IN  RST_N        { PIN: 1,       WAV: RZ,      DEF: 1,   SUP: VIN    }
    IN  R            { PIN: 2,       WAV: RZ,      DEF: 0,   SUP: VIN    }
    IN  W            { PIN: 3,       WAV: RZ,      DEF: 0,   SUP: VIN    }
    IN  ADDR         { PIN: [4:11],  WAV: NRZ,     DEF: 0,   SUP: VIN    }
    IN  DQ_RX_BIT    { PIN: 12,      WAV: NRZ@DQ,  DEF: 1,   SUP: VIN@DQ }
    IN  DQS_RX_BIT   { PIN: 13,      WAV: NRZ@DQS, DEF: 1,   SUP: VIN@DQS}
    IN  MR_IN        { PIN: [14:21], WAV: NRZ,     DEF: 0,   SUP: VIN    }
    IN  MRW          { PIN: 22,      WAV: RZ,      DEF: 0,   SUP: VIN    }
    IN  MRR          { PIN: 23,      WAV: RZ,      DEF: 0,   SUP: VIN    }

    OUT DQ_IE        { PIN: 0, WAV: STB     , SUP: VOUT }
    OUT DQ_TX_BIT    { PIN: 1, WAV: STB@DQ  , SUP: VOUT@DQ }
    OUT DQS_TX_BIT   { PIN: 2, WAV: STB@DQS , SUP: VOUT@DQS }
    OUT DQ_OE        { PIN: 3, WAV: STB     , SUP: VOUT }
    OUT DQ_OUT_VALID { PIN: 4, WAV: STB     , SUP: VOUT }

    POWER VDDQ       { SUP: VDC }
}
