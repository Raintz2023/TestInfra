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
                GOTO-1 WRITE_TRAIN *
        STOP

                //      CTRL                   REG                                   CMD                        
                    -------------------------------------------------------------------------------------------------------
        WRITE_TRAIN#FOR-2       |                              :     ;                  ;             ;                     ;
                                |                              :     ;                  ;             ;                     ;
                                |                              :     ;                  ;             ;                     ;
                                |                              :     ;                  ;             ;                     ;
                    NOP         | MR_ADDR = 0                  :     ;MRW  < MR_ADDR, RL;             ;                     ; 
                                | MR_ADDR = 1                  :     ;MRW  < MR_ADDR, WL;             ;                     ;
                                |                              :     ;                  ;             ;                     ;
                                |                              :     ;                  ;             ;                     ;
                    NOP         |                              :     ;                  ;             ;                     ;
                                |                              :     ;                  ;             ;                     ;
                                |                              :     ;                  ;             ;                     ;
                                |                              :     ;                  ;             ;                     ;
                    NOP         |                              :     ;                  ;             ;                     ;
                                |                              :     ;                  ;             ;                     ;
                                |                              :     ;                  ;             ;                     ;
                                |                              :     ;                  ;             ;                     ;
                    NOP         | ARRAY_ADDR = 0x04            :     ;                  ;             ;                     ;
                                |                              :     ;                  ;             ;                     ;
                                |                              :     ;                  ;             ;                     ;
                                |                              :     ;                  ;             ;                     ;
                    NOP         |                              : TS1 ;                  ;    WDQSL    ;                     ;
                                |                              : TS1 ;                  ;    WDQSL    ;                     ;
                                |                              : TS1 ;                  ;    WDQSH    ;                     ;
                                |                              : TS1 ;                  ;    WDQSH    ;                     ;
                    NOP         |                              : TS1 ;WT < ARRAY_ADDR   ;    WDQSL    ;    W <   DATA       ;
                                |                              : TS1 ;                  ;    WDQSH    ;    W <  /DATA       ;
                                |                              : TS1 ;                  ;    WDQSL    ;    W <   DATA       ;
                                |                              : TS1 ;                  ;    WDQSH    ;    W <  /DATA       ;
                    NOP         |                              : TS1 ;                  ;    WDQSL    ;    W <  /DATA       ;
                                |                              : TS1 ;                  ;    WDQSH    ;    W <   DATA       ;
                                |                              : TS1 ;                  ;    WDQSL    ;    W <  /DATA       ;
                                |                              : TS1 ;                  ;    WDQSH    ;    W <   DATA       ;
                    NOP         |                              : TS1 ;                  ;    WDQSL    ;                     ;
                                |                              : TS1 ;                  ;    WDQSL    ;                     ; 
                                |                              :     ;                  ;             ;                     ;
                                |                              :     ;                  ;             ;                     ;
                    NOP         |                              :     ;                  ;             ;                     ;
                                |                              :     ;                  ;             ;                     ;
                                |                              :     ;                  ;             ;                     ;
                                |                              :     ;                  ;             ;                     ;
                    FOR-LOOP_1  |                              :     ;                  ;             ;                     ;
                                |                              :     ;                  ;             ;                     ;
                                |                              :     ;                  ;             ;                     ;
                                |                              :     ;                  ;             ;                     ;
                    NOP         |                              :     ;                  ;             ;                     ;
                                |                              :     ;                  ;             ;                     ;
                                |                              :     ;                  ;             ;                     ;
                                |                              :     ;                  ;             ;                     ;
                    NOP         | ARRAY_ADDR = 0x04            :     ;                  ;             ;                     ;
                                |                              :     ;                  ;             ;                     ;
                                |                              :     ;                  ;             ;                     ;
                                |                              :     ;                  ;             ;                     ;
                    NOP         |                              : TS1 ;                  ;    RDQSL    ;                     ;
                                |                              : TS1 ;                  ;    RDQSL    ;                     ;
                                |                              : TS1 ;                  ;    RDQSH    ;                     ;
                                |                              : TS1 ;                  ;    RDQSH    ;                     ;
                    NOP         |                              : TS1 ;RD < ARRAY_ADDR   ;    RDQSL    ;    R <  DATA        ;
                                |                              : TS1 ;                  ;    RDQSH    ;    R < /DATA        ;
                                |                              : TS1 ;                  ;    RDQSL    ;    R <  DATA        ;
                                |                              : TS1 ;                  ;    RDQSH    ;    R < /DATA        ;
                    NOP         |                              : TS1 ;                  ;    RDQSL    ;    R < /DATA        ;
                                |                              : TS1 ;                  ;    RDQSH    ;    R <  DATA        ;
                                |                              : TS1 ;                  ;    RDQSL    ;    R < /DATA        ;
                                |                              : TS1 ;                  ;    RDQSH    ;    R <  DATA        ;
                    NOP         |                              : TS1 ;                  ;    RDQSL    ;                     ;
                                |                              : TS1 ;                  ;    RDQSL    ;                     ;
                                |                              :     ;                  ;             ;                     ;
                                |                              :     ;                  ;             ;                     ;
                    NOP         |                              :     ;                  ;             ;                     ;
                                |                              :     ;                  ;             ;                     ;
                                |                              :     ;                  ;             ;                     ;
                                |                              :     ;                  ;             ;                     ;
                    NOP         |                              :     ;                  ;             ;                     ;
                                |                              :     ;                  ;             ;                     ;
                                |                              :     ;                  ;             ;                     ;
                                |                              :     ;                  ;             ;                     ;
                    FOR-LOOP_1  |                              :     ;                  ;             ;                     ;
                                |                              :     ;                  ;             ;                     ;
                                |                              :     ;                  ;             ;                     ;
                                |                              :     ;                  ;             ;                     ;
                    NOP         |                              :     ;CPA               ;             ;                     ;
                                |                              :     ;                  ;             ;                     ;
                                |                              :     ;                  ;             ;                     ;
                                |                              :     ;                  ;             ;                     ;
                    RTN         |                              :     ;                  ;             ;                     ;
                                |                              :     ;                  ;             ;                     ;
                                |                              :     ;                  ;             ;                     ;
                                |                              :     ;                  ;             ;                     ;
                    -------------------------------------------------------------------------------------------------------

    INCLUDE Init
    END