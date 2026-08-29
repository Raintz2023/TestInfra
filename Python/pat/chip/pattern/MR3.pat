USE chip
VOLTAGE = VS0

        FUNCTION { DEQUE } 

    BEGIN

        <0> START
                NOP                     | LOOP_3 = 1 : ALERT *
                GOTO-LOOP_3 REG_INIT *
                GOTO-LOOP_3 MR3 *
        STOP
                //       CTRL                    REG                                 CMD                      
                    ----------------------------------------------------------------------------------------------------
        MR3#        NOP         |                              :     ;                   ;           ;            ;     ;
                                |                              :     ;                   ;           ;            ;     ;
                                |                              :     ;                   ;           ;            ;     ;
                                |                              :     ;                   ;           ;            ;     ;
                    FOR-2       |                              :     ;                   ;           ;            ;     ;
                                |                              :     ;                   ;           ;            ;     ;
                                |                              :     ;                   ;           ;            ;     ;
                                |                              :     ;                   ;           ;            ;     ;
                    NOP         | MR_ADDR = 0x00               :     ; MRW < MR_ADDR, RL ;           ;            ;     ; 
                                |                              :     ;                   ;           ;            ;     ;
                                |                              :     ;                   ;           ;            ;     ;
                                |                              :     ;                   ;           ;            ;     ;
                    NOP         |                              :     ;                   ;           ;            ;     ;
                                |                              :     ;                   ;           ;            ;     ;
                                |                              :     ;                   ;           ;            ;     ;
                                | MR_ADDR = 0x03               :     ;                   ;           ;            ;     ;
                MRR#  NOP       |                              :     ;                   ;           ;            ;     ;
                                |                              :     ;                   ;           ;            ;     ;
                                |                              :     ;                   ;           ;            ;     ;
                                |                              :     ;                   ;           ;            ;     ;
                    NOP         |                              : TS1 ;                   ;  RDQSL    ;            ;     ;
                                |                              : TS1 ;                   ;  RDQSL    ;            ;     ;
                                |                              : TS1 ;                   ;  RDQSH    ;            ;     ;
                                |                              : TS1 ;                   ;  RDQSH    ;            ;     ;
                    NOP         |                              : TS1 ; MRR  < MR_ADDR    ;  RDQSL    ; R < DEQUE  ; POP ;
                                |                              : TS1 ;                   ;  RDQSH    ; R < DEQUE  ; POP ;
                                |                              : TS1 ;                   ;  RDQSL    ; R < DEQUE  ; POP ;
                                |                              : TS1 ;                   ;  RDQSH    ; R < DEQUE  ; POP ;
                    NOP         |                              : TS1 ;                   ;  RDQSL    ; R < DEQUE  ; POP ;
                                |                              : TS1 ;                   ;  RDQSH    ; R < DEQUE  ; POP ;
                                |                              : TS1 ;                   ;  RDQSL    ; R < DEQUE  ; POP ;
                                |                              : TS1 ;                   ;  RDQSH    ; R < DEQUE  ; POP ;
                    NOP         |                              : TS1 ;                   ;  RDQSL    ;            ;     ;
                                |                              : TS1 ;                   ;  RDQSL    ;            ;     ;
                                |                              :     ;                   ;           ;            ;     ;
                                |                              :     ;                   ;           ;            ;     ;
                    FOR-LOOP_1  |                              :     ;                   ;           ;            ;     ;
                                |                              :     ;                   ;           ;            ;     ;
                                |                              :     ;                   ;           ;            ;     ;
                                |                              :     ;                   ;           ;            ;     ;
                GOTO-LOOP_2 MRR |                              :     ;                   ;           ;            ;     ;
                                |                              :     ;                   ;           ;            ;     ;
                                |                              :     ;                   ;           ;            ;     ;
                                |                              :     ;                   ;           ;            ;     ;
                    RTN         |                              : CPA ; ALERT             ;           ;            ;     ;
                                |                              :     ;                   ;           ;            ;     ;
                                |                              :     ;                   ;           ;            ;     ;
                                |                              :     ;                   ;           ;            ;     ;
                    ----------------------------------------------------------------------------------------------------

        INCLUDE Init
END
