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
                NOP                     | LOOP_3 = 1 : ALERT *
                GOTO-LOOP_3 REG_INIT *
                GOTO-LOOP_3 READ_TRAIN *
        STOP
                //       CTRL                    REG                                 CMD                      
                    -------------------------------------------------------------------------------------------------
        READ_TRAIN# NOP         |                              :     ;                   ;           ;               ;
                                |                              :     ;                   ;           ;               ;
                                |                              :     ;                   ;           ;               ;
                                |                              :     ;                   ;           ;               ;
                    FOR-2       |                              :     ;                   ;           ;               ;
                                |                              :     ;                   ;           ;               ;
                                |                              :     ;                   ;           ;               ;
                                |                              :     ;                   ;           ;               ;
                    NOP         | MR_ADDR = 0x00               :     ; MRW < MR_ADDR, RL ;           ;               ; 
                                |                              :     ;                   ;           ;               ;
                                |                              :     ;                   ;           ;               ;
                                |                              :     ;                   ;           ;               ;
                    NOP         |                              :     ;                   ;           ;               ;
                                |                              :     ;                   ;           ;               ;
                                |                              :     ;                   ;           ;               ;
                                |                              :     ;                   ;           ;               ;
                MRR#  NOP       |                              :     ;                   ;           ;               ;
                                |                              :     ;                   ;           ;               ;
                                |                              :     ;                   ;           ;               ;
                                |                              :     ;                   ;           ;               ;
                    NOP         |                              : TS1 ;                   ;  RDQSL    ;               ;
                                |                              : TS1 ;                   ;  RDQSL    ;               ;
                                |                              : TS1 ;                   ;  RDQSH    ;               ;
                                |                              : TS1 ;                   ;  RDQSH    ;               ;
                    NOP         | MR_ADDR = 0x03               : TS1 ; MRR  < MR_ADDR    ;  RDQSL    ; R < /DATA     ;
                                |                              : TS1 ;                   ;  RDQSH    ; R <  DATA     ;
                                |                              : TS1 ;                   ;  RDQSL    ; R < /DATA     ;
                                |                              : TS1 ;                   ;  RDQSH    ; R <  DATA     ;
                    NOP         |                              : TS1 ;                   ;  RDQSL    ; R <  DATA     ;
                                |                              : TS1 ;                   ;  RDQSH    ; R < /DATA     ;
                                |                              : TS1 ;                   ;  RDQSL    ; R <  DATA     ;
                                |                              : TS1 ;                   ;  RDQSH    ; R < /DATA     ;
                    NOP         |                              : TS1 ;                   ;  RDQSL    ;               ;
                                |                              : TS1 ;                   ;  RDQSL    ;               ;
                                |                              :     ;                   ;           ;               ;
                                |                              :     ;                   ;           ;               ;
                    FOR-LOOP_1  |                              :     ;                   ;           ;               ;
                                |                              :     ;                   ;           ;               ;
                                |                              :     ;                   ;           ;               ;
                                |                              :     ;                   ;           ;               ;
                    RTN         |                              : CPA ; ALERT             ;           ;               ;
                                |                              :     ;                   ;           ;               ;
                                |                              :     ;                   ;           ;               ;
                                |                              :     ;                   ;           ;               ;
                    -------------------------------------------------------------------------------------------------

        INCLUDE Init
END