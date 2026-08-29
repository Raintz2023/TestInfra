USE chip
VOLTAGE = VS0

BEGIN

        <0> START
                NOP                     | LOOP_3 = 1 : ALERT *
                GOTO-LOOP_3 REG_INIT *
                GOTO-LOOP_3 MR *
        STOP
                //       CTRL                    REG                                 CMD                      
                    -------------------------------------------------------------------------------------------------
            MR#     NOP         |                              :     ;                   ;           ;               ;
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
                    NOP         | MR_ADDR = TEMP               : TS1 ; MRR  < MR_ADDR    ;  RDQSL    ; R < DATA      ;
                                |                              : TS1 ;                   ;  RDQSH    ;               ;
                                |                              : TS1 ;                   ;  RDQSL    ;               ;
                                |                              : TS1 ;                   ;  RDQSH    ;               ;
                    NOP         |                              : TS1 ;                   ;  RDQSL    ;               ;
                                |                              : TS1 ;                   ;  RDQSH    ;               ;
                                |                              : TS1 ;                   ;  RDQSL    ;               ;
                                |                              : TS1 ;                   ;  RDQSH    ;               ;
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
