USE chip
VOLTAGE = VS0

    BEGIN
    <0> START   
                GOTO-1 RESET *
                GOTO-1 REG_INIT *
                GOTO-1 WRITE_READ *
        STOP

                //      CTRL                   REG                                   CMD                        
                    -------------------------------------------------------------------------------------------------------
        WRITE_READ#FOR-2        |                              :     ;                  ;             ;                     ;
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
                                | ARRAY_ADDR = 0x04            :     ;                  ;             ;                     ;
            WRITE#  NOP         |                              :     ;                  ;             ;                     ;
                                |                              :     ;                  ;             ;                     ;
                                |                              :     ;                  ;             ;                     ;
                                |                              :     ;                  ;             ;                     ;
                    NOP         |                              :     ;                  ;             ;                     ;
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
                                |      FOO_ADDR = 0x00         :     ;                  ;             ;                     ;
                    FOR-LOOP_1  |                              :     ;                  ;             ;                     ;
                                |                              :     ;                  ;             ;                     ;
                                |                              :     ;                  ;             ;                     ;
                                |                              :     ;                  ;             ;                     ;
                    NOP         |                              :     ;                  ;             ;                     ;
                                |                              :     ;                  ;             ;                     ;
                                |                              :     ;                  ;             ;                     ;
                                |                              :     ;                  ;             ;                     ;
                    NOP         |                              :     ;                  ;             ;                     ;
                                |                              :     ;                  ;             ;                     ;
                                |                              :     ;                  ;             ;                     ;
                                |                              :     ;WT < FOO_ADDR     ;             ;                     ;
            READ#   NOP         |                              : TS1 ;RD < ARRAY_ADDR   ;    RDQSL    ;                     ;
                                |                              : TS1 ;                  ;    RDQSL    ;                     ;
                                |                              : TS1 ;                  ;    RDQSH    ;                     ;
                                |                              : TS1 ;                  ;    RDQSH    ;                     ;
                    NOP         |                              : TS1 ;                  ;    RDQSL    ;    R <  DATA        ;
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
            GOTO-LOOP_2  WRITE  |  ARRAY_ADDR = ARRAY_ADDR + 1 :     ;                  ;             ;                     ;
                                |  DATA = /DATA                :     ;                  ;             ;                     ;
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
    INCLUDE Reset
    END
