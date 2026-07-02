USE chip

        REGISTER  {
                DEFINE {
                    8'LOOP[0-3]    // ROLE: LOOP, unsigned
                    8'ADDR[0-1]    // ROLE: ARG, unsigned
                    8'X            // ROLE: ARG, signed
                    8'Y            // ROLE: ARG, signed
                    8'Z[0-1]       // ROLE: ARG, unsigned
                    8'TEMP         // ROLE: ARG, signed
                    1'DATA         // ROLE: EXPECT, unsigned
                }
                ALIAS {
                    Z_0 = RL
                    Z_1 = WL
                    ADDR_0 = ARRAY_ADDR
                    ADDR_1 = MR_ADDR
                }
        }

BEGIN
    <0> START
                GOTO-1 REG_INIT *
                GOTO-1 MRR2_BIT5_STATUS *
        STOP

    <1> START
                GOTO-1 REG_INIT *
                GOTO-1 MRR2_BIT1_STATUS *
        STOP

                    ---------------------------------------------------------------------------------------------------------
    MRR2_BIT5_STATUS# FOR-2     |                              :    ;                   ;             ;                      ;
                                |                              :    ;                   ;             ;                      ;
                                |                              :    ;                   ;             ;                      ;
                                |                              :    ;                   ;             ;                      ;
                    NOP         | MR_ADDR = 0                  :    ;MRW  < MR_ADDR, RL ;             ;                      ; 
                                | MR_ADDR = 1                  :    ;MRW  < MR_ADDR, WL ;             ;                      ;
                                |                              :    ;                   ;             ;                      ;
                                |                              :    ;                   ;             ;                      ;
                    NOP         |                              :    ;                   ;             ;                      ;
                                |                              :    ;                   ;             ;                      ;
                                |                              :    ;                   ;             ;                      ;
                                | ARRAY_ADDR = 0x04            :    ;                   ;             ;                      ;
                    NOP         |                              :    ;                   ;             ;                      ;
                                |                              :    ;                   ;             ;                      ;
                                |                              :    ;                   ;             ;                      ;
                                |                              :    ;                   ;             ;                      ;
                    NOP         |                              :    ;                   ;             ;                      ;
                                |                              :    ;                   ;             ;                      ;
                                |                              :    ;                   ;             ;                      ;
                                |                              :    ;WT < ARRAY_ADDR    ;             ;                      ;
                    NOP         |                              :    ;                   ;             ;                      ;
                                |                              :TS1 ;                   ;   RDQSL     ;                      ;
                                |                              :TS1 ;                   ;   RDQSL     ;                      ;
                                |                              :TS1 ;                   ;   RDQSH     ;                      ;
                    NOP         |                              :TS1 ;                   ;   RDQSH     ;                      ; 
                                | MR_ADDR = 0x02               :TS1 ;MRR< MR_ADDR       ;   RDQSL     ;       R < 0          ; // MRR MR2 BIT0 STB Y
                                |                              :TS1 ;                   ;   RDQSH     ;       R < 0          ;
                                |                              :TS1 ;                   ;   RDQSL     ;       R < 0          ;
                    NOP         |                              :TS1 ;                   ;   RDQSH     ;       R < 0          ;
                                |                              :TS1 ;                   ;   RDQSL     ;       R < 0          ;
                                |                              :TS1 ;                   ;   RDQSH     ;       R < 1          ;
                                |                              :TS1 ;                   ;   RDQSL     ;       R < 0          ;
                    NOP         |                              :TS1 ;                   ;   RDQSH     ;       R < 0          ;
                                |                              :TS1 ;                   ;   RDQSL     ;                      ;
                                |                              :TS1 ;                   ;   RDQSL     ;                      ;
                                |                              :    ;                   ;             ;                      ;
                    NOP         |                              :    ;                   ;             ;                      ;
                                |                              :    ;                   ;             ;                      ;
                                |                              :    ;                   ;             ;                      ;
                                |                              :    ;                   ;             ;                      ;
                    FOR-LOOP_1  |                              :    ;                   ;             ;                      ;
                                |                              :    ;                   ;             ;                      ;
                                |                              :    ;                   ;             ;                      ;
                                |                              :    ;                   ;             ;                      ;
                    NOP         |                              :    ;                   ;             ;                      ;
                                |                              :    ;                   ;             ;                      ;
                                |                              :    ;                   ;             ;                      ;
                                |                              :    ;                   ;             ;                      ;
                    RTN         |                              :    ;CPA                ;             ;                      ;
                                |                              :    ;                   ;             ;                      ;
                                |                              :    ;                   ;             ;                      ;
                                |                              :    ;                   ;             ;                      ;
                    ----------------------------------------------------------------------------------------------------------

                    ------------------------------------------------------------------------------------------------------------------------------
    MRR2_BIT1_STATUS# FOR-2     |                              :     ;                 ;                     ;             ;                      ;
                                |                              :     ;                 ;                     ;             ;                      ;
                                |                              :     ;                 ;                     ;             ;                      ;
                                |                              :     ;                 ;                     ;             ;                      ;
                    NOP         | MR_ADDR = 0                  :     ;                 ;  MRW  < MR_ADDR, RL ;             ;                      ; 
                                | MR_ADDR = 1                  :     ;                 ;  MRW  < MR_ADDR, WL ;             ;                      ;
                                |                              :     ;                 ;                     ;             ;                      ;
                                |                              :     ;                 ;                     ;             ;                      ;
                    NOP         |                              :     ;                 ;                     ;             ;                      ;
                                |                              :     ;                 ;                     ;             ;                      ;
                                |                              :     ;                 ;                     ;             ;                      ;
                                | ARRAY_ADDR = 0x04            :     ;                 ;                     ;             ;                      ;
                    NOP         |                              :     ;                 ;                     ;             ;                      ;
                                |                              :     ;                 ;                     ;             ;                      ;
                                |                              :     ;                 ;                     ;             ;                      ;
                                |                              :     ;                 ;                     ;             ;                      ;
                    NOP         |                              :     ;                 ;                     ;             ;                      ;
                                |                              :     ;                 ;                     ;             ;                      ;
                                |                              :     ;                 ;                     ;             ;                      ;
                                |                              :     ;                 ;                     ;             ;                      ;
                    NOP         |                              :     ;                 ;                     ;             ;                      ;
                                |                              : TS1 ;                 ;                     ;   RDQSL     ;                      ;
                                |                              : TS1 ;                 ;                     ;   RDQSL     ;                      ;
                                |                              : TS1 ;                 ;                     ;   RDQSH     ;                      ;
                    NOP         |                              : TS1 ;                 ;                     ;   RDQSH     ;                      ; 
                                | MR_ADDR = 0x02               : TS1 ; RD < ARRAY_ADDR ;  MRR< MR_ADDR       ;   RDQSL     ;       R < 0          ; // MRR MR2 BIT0 STB Y
                                |                              : TS1 ; RD < ARRAY_ADDR ;                     ;   RDQSH     ;       R < 1          ;
                                |                              : TS1 ; RD < ARRAY_ADDR ;                     ;   RDQSL     ;       R < 0          ;
                    NOP         |                              : TS1 ; RD < ARRAY_ADDR ;                     ;   RDQSH     ;       R < 0          ;
                                |                              : TS1 ; RD < ARRAY_ADDR ;                     ;   RDQSL     ;       R < 0          ;
                                |                              : TS1 ; RD < ARRAY_ADDR ;                     ;   RDQSH     ;       R < 0          ;
                                |                              : TS1 ; RD < ARRAY_ADDR ;                     ;   RDQSL     ;       R < 1          ;
                    NOP         |                              : TS1 ; RD < ARRAY_ADDR ;                     ;   RDQSH     ;       R < 0          ;
                                |                              : TS1 ;                 ;                     ;   RDQSL     ;                      ;
                                |                              : TS1 ;                 ;                     ;   RDQSL     ;                      ;
                                |                              :     ;                 ;                     ;             ;                      ;
                    NOP         |                              :     ;                 ;                     ;             ;                      ;
                                |                              :     ;                 ;                     ;             ;                      ;
                                |                              :     ;                 ;                     ;             ;                      ;
                                |                              :     ;                 ;                     ;             ;                      ;
                    FOR-LOOP_1  |                              :     ;                 ;                     ;             ;                      ;
                                |                              :     ;                 ;                     ;             ;                      ;
                                |                              :     ;                 ;                     ;             ;                      ;
                                |                              :     ;                 ;                     ;             ;                      ;
                    NOP         |                              :     ;                 ;                     ;             ;                      ;
                                |                              :     ;                 ;                     ;             ;                      ;
                                |                              :     ;                 ;                     ;             ;                      ;
                                |                              :     ;                 ;                     ;             ;                      ;
                    RTN         |                              :     ;                 ;   CPA               ;             ;                      ;
                                |                              :     ;                 ;                     ;             ;                      ;
                                |                              :     ;                 ;                     ;             ;                      ;
                                |                              :     ;                 ;                     ;             ;                      ;
                    ------------------------------------------------------------------------------------------------------------------------------
    INCLUDE Init

END