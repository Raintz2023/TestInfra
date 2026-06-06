USE chip

      REGISTER  {
            8'LOOP[0:3], 8'ADDR[0:1], 8'X, 8'Y[0:1]=[Y, Y_TRAIN], 8'Z[0:1]=[RL, WL], 8'TEMP, 8'DELAY, 1'DATA
      }


BEGIN

      <0> START
            NOP                     | LOOP_3 = 1 : ALERT *
            GOTO-LOOP_3 REG_INIT *
            GOTO-LOOP_3 READ_TRAIN *
      STOP

      <1> START
            NOP                     | LOOP_3 = 1 *
            GOTO-LOOP_3 REG_INIT *
            GOTO-LOOP_3 WRITE_TRAIN *
      STOP

      <2> START
                  NOP               | LOOP_3 = 1                   :     ;                   ;                 ;
                                    |                              :     ;                   ;                 ;
                                    |                              :     ;                   ;                 ;
                                    |                              :     ;                   ;                 ;
            GOTO-LOOP_3 REG_INIT *
            GOTO-LOOP_3 WRITE_READ *
      STOP 

           //       CTRL                    REG                                 CMD                      
                  ---------------------------------------------------------------------------------------
      REG_INIT#   NOP         | DATA  = 1                    :     ;                   ;                 ;
                              |                              :     ;                   ;                 ;
                              | LOOP_1 = 20                  :     ;                   ;                 ;
                              |                              :     ;                   ;                 ;
                  NOP         | LOOP_2 = 10                  :     ;                   ;                 ;
                              |                              :     ;                   ;                 ;
                              |                              :     ;                   ;                 ;
                              |                              :     ;                   ;                 ;
                  NOP         |                              :     ;                   ;                 ; 
                              |                              :     ;                   ;                 ;
                              |                              :     ;                   ;                 ;
                              |                              :     ;                   ;                 ;
                  NOP         |                              :     ;                   ;                 ;
                              |                              :     ;                   ;                 ;
                              |                              :     ;                   ;                 ;
                              |                              :     ;                   ;                 ;
                  FOR-2       |                              :     ;                   ;                 ;
                              |                              :     ;                   ;                 ;
                              |                              :     ;                   ;                 ;
                              |                              :     ;                   ;                 ;
                  RTN         |                              :     ;                   ;                 ;
                              |                              :     ;                   ;                 ;
                              |                              :     ;                   ;                 ;
                              |                              :     ;                   ;                 ;
                  ---------------------------------------------------------------------------------------
            //       CTRL                    REG                                 CMD                      
                  ---------------------------------------------------------------------------------------
      READ_TRAIN# NOP         |                              :     ;                   ;                 ;
                              |                              :     ;                   ;                 ;
                              |                              :     ;                   ;                 ;
                              |                              :     ;                   ;                 ;
                  FOR-2       |                              :     ;                   ;                 ;
                              |                              :     ;                   ;                 ;
                              |                              :     ;                   ;                 ;
                              |                              :     ;                   ;                 ;
            MRW#  NOP         | ADDR_1 = 0x00                :     ;MRW < ADDR_1, RL   ;                 ; 
                              |                              :     ;                   ;                 ;
                              |                              :     ;                   ;                 ;
                              |                              :     ;                   ;                 ;
                  NOP         |                              :     ;                   ;                 ;
                              |                              :     ;                   ;                 ;
                              |                              :     ;                   ;                 ;
                              |                              :     ;                   ;                 ;
            MRR#  NOP         |                              :     ;                   ;                 ;
                              |                              :     ;                   ;                 ;
                              |                              :     ;                   ;                 ;
                              |                              :     ;                   ;                 ;
                  NOP         | ADDR_1 = 0x02                :     ;                   ;                 ;
                              |                              :     ;                   ;                 ;
                              |                              :     ;                   ;                 ;
                              |                              :     ;                   ;                 ;
                  NOP         | DELAY = RL                   : TS1 ;MRR  < ADDR_1      ; SAMP <  0       ;
                              |                              : TS1 ;                   ; SAMP <  DATA    ;
                              |                              : TS1 ;                   ; SAMP < /DATA    ;
                              |                              : TS1 ;                   ; SAMP <  DATA    ;
                  NOP         |                              : TS1 ;                   ; SAMP < /DATA    ;
                              |                              : TS1 ;                   ; SAMP < /DATA    ;
                              |                              : TS1 ;                   ; SAMP <  DATA    ;
                              |                              : TS1 ;                   ; SAMP < /DATA    ;
                  NOP         |                              : TS1 ;                   ; SAMP <  DATA    ;
                              |                              : TS1 ;                   ; SAMP <  1       ;
                              |                              :     ;                   ;                 ;
                              | DELAY = 0                    :     ;                   ;                 ;
                  FOR-LOOP_1  |                              :     ;                   ;                 ;
                              |                              :     ;                   ;                 ;
                              |                              :     ;                   ;                 ;
                              |                              :     ;                   ;                 ;
                  RTN         |                              : CPA ;                   ;                 ;
                              |                              :     ;                   ;                 ;
                              |                              :     ;                   ;                 ;
                              |                              :     ;                   ;                 ;
                  ----------------------------------------------------------------------------------------

            //      CTRL                   REG                                   CMD                        
                  ---------------------------------------------------------------------------------------
      WRITE_TRAIN# FOR-2      |                              :    ;                   ;                     ;
                              |                              :    ;                   ;                     ;
                              |                              :    ;                   ;                     ;
                              |                              :    ;                   ;                     ;
                  NOP         | ADDR_1 = 0                   :    ;MRW  < ADDR_1, RL  ;                     ; 
                              | ADDR_1 = 1                   :    ;MRW  < ADDR_1, WL  ;                     ;
                              |                              :    ;                   ;                     ;
                              |                              :    ;                   ;                     ;
                  NOP         |                              :    ;                   ;                     ;
                              |                              :    ;                   ;                     ;
                              |                              :    ;                   ;                     ;
                              |                              :    ;                   ;                     ;
                  NOP         |                              :    ;                   ;                     ;
                              |                              :    ;                   ;                     ;
                              |                              :    ;                   ;                     ;
                              |                              :    ;                   ;                     ;
                  NOP         | ADDR_1 = 0x04                :    ;                   ;                     ;
                              |                              :    ;                   ;                     ;
                              |                              :    ;                   ;                     ;
                              |                              :    ;                   ;                     ;
                  NOP         |                              :    ;                   ;                     ;
                              |                              :    ;                   ;                     ;
                              |                              :    ;                   ;                     ;
                              |                              :    ;                   ;                     ;
                  NOP         | DELAY =  Y                   :    ;WT < ADDR_1        ; DRIV_START <  0     ;
                              |                              :    ;                   ; DRIV <   DATA       ;
                              |                              :    ;                   ; DRIV <  /DATA       ;
                              |                              :    ;                   ; DRIV <   DATA       ;
                  NOP         |                              :    ;                   ; DRIV <  /DATA       ;
                              |                              :    ;                   ; DRIV <  /DATA       ;
                              |                              :    ;                   ; DRIV <   DATA       ;
                              |                              :    ;                   ; DRIV <  /DATA       ;
                  NOP         |                              :    ;                   ; DRIV <   DATA       ;
                              |                              :    ;                   ; DRIV <   1          ; 
                              |                              :    ;                   ;                     ;
                              |                              :    ;                   ;                     ;
                  NOP         | DELAY = 0                    :    ;                   ;                     ;
                              |                              :    ;                   ;                     ;
                              |                              :    ;                   ;                     ;
                              |                              :    ;                   ;                     ;
                  FOR-LOOP_1  |                              :    ;                   ;                     ;
                              |                              :    ;                   ;                     ;
                              |                              :    ;                   ;                     ;
                              |                              :    ;                   ;                     ;
                  NOP         |                              :    ;                   ;                     ;
                              |                              :    ;                   ;                     ;
                              |                              :    ;                   ;                     ;
                              |                              :    ;                   ;                     ;
                  NOP         | ADDR_1 = 0x04                :    ;                   ;                     ;
                              |                              :    ;                   ;                     ;
                              |                              :    ;                   ;                     ;
                              |                              :    ;                   ;                     ;
                  NOP         |                              :    ;                   ;                     ;
                              |                              :    ;                   ;                     ;
                              |                              :    ;                   ;                     ;
                              |                              :    ;                   ;                     ;
                  NOP         | DELAY = RL                   :TS1 ;RD < ADDR_1        ; SAMP <  0           ;
                              |                              :TS1 ;                   ; SAMP <  DATA        ;
                              |                              :TS1 ;                   ; SAMP < /DATA        ;
                              |                              :TS1 ;                   ; SAMP <  DATA        ;
                  NOP         |                              :TS1 ;                   ; SAMP < /DATA        ;
                              |                              :TS1 ;                   ; SAMP < /DATA        ;
                              |                              :TS1 ;                   ; SAMP <  DATA        ;
                              |                              :TS1 ;                   ; SAMP < /DATA        ;
                  NOP         |                              :TS1 ;                   ; SAMP <  DATA        ;
                              |                              :TS1 ;                   ; SAMP <  1           ;
                              |                              :    ;                   ;                     ;
                              |                              :    ;                   ;                     ;
                  NOP         |                              :    ;                   ;                     ;
                              | DELAY = 0                    :    ;                   ;                     ;
                              |                              :    ;                   ;                     ;
                              |                              :    ;                   ;                     ;
                  NOP         |                              :    ;                   ;                     ;
                              |                              :    ;                   ;                     ;
                              |                              :    ;                   ;                     ;
                              |                              :    ;                   ;                     ;
                  FOR-LOOP_1  |                              :    ;                   ;                     ;
                              |                              :    ;                   ;                     ;
                              |                              :    ;                   ;                     ;
                              |                              :    ;                   ;                     ;
                  NOP         |                              :    ;CPA                ;                     ;
                              |                              :    ;                   ;                     ;
                              |                              :    ;                   ;                     ;
                              |                              :    ;                   ;                     ;
                  RTN         |                              :    ;                   ;                     ;
                              |                              :    ;                   ;                     ;
                              |                              :    ;                   ;                     ;
                              |                              :    ;                   ;                     ;
                  ---------------------------------------------------------------------------------------

            //      CTRL                   REG                                   CMD                        
                  ---------------------------------------------------------------------------------------
      WRITE_READ# FOR-2       |                              :    ;                   ;                      ;
                              |                              :    ;                   ;                      ;
                              |                              :    ;                   ;                      ;
                              |                              :    ;                   ;                      ;
                  NOP         | ADDR_1 = 0                   :    ;MRW  < ADDR_1, RL  ;                      ; 
                              | ADDR_1 = 1                   :    ;MRW  < ADDR_1, WL  ;                      ;
                              |                              :    ;                   ;                      ;
                              |                              :    ;                   ;                      ;
                  NOP         |                              :    ;                   ;                      ;
                              |                              :    ;                   ;                      ;
                              |                              :    ;                   ;                      ;
                              | ADDR_1 = 0x04                :    ;                   ;                      ;
            WR#   NOP         |                              :    ;                   ;                      ;
                              |                              :    ;                   ;                      ;
                              |                              :    ;                   ;                      ;
                              |                              :    ;                   ;                      ;
                  NOP         |                              :    ;                   ;                      ;
                              |                              :    ;                   ;                      ;
                              |                              :    ;                   ;                      ;
                              |                              :    ;                   ;                      ;
                  NOP         |                              :    ;                   ;                      ;
                              |                              :    ;                   ;                      ;
                              |                              :    ;                   ;                      ;
                              |                              :    ;                   ;                      ;
                  NOP         | DELAY =  Y_TRAIN             :    ;WT < ADDR_1        ; DRIV_START <  0      ;
                              |                              :    ;                   ; DRIV <   DATA        ;
                              |                              :    ;                   ; DRIV <  /DATA        ;
                              |                              :    ;                   ; DRIV <   DATA        ;
                  NOP         |                              :    ;                   ; DRIV <  /DATA        ;
                              |                              :    ;                   ; DRIV <  /DATA        ;
                              |                              :    ;                   ; DRIV <   DATA        ;
                              |                              :    ;                   ; DRIV <  /DATA        ;
                  NOP         |                              :    ;                   ; DRIV <   DATA        ;
                              |                              :    ;                   ; DRIV <   1           ;
                              |                              :    ;                   ;                      ;
                              |                              :    ;                   ;                      ;
                  NOP         | DELAY = 0                    :    ;                   ;                      ;
                              |                              :    ;                   ;                      ;
                              |                              :    ;                   ;                      ;
                              |                              :    ;                   ;                      ;
                  FOR-LOOP_1  |                              :    ;                   ;                      ;
                              |                              :    ;                   ;                      ;
                              |                              :    ;                   ;                      ;
                              |                              :    ;                   ;                      ;
            RD#   NOP         |                              :    ;                   ;                      ;
                              |                              :    ;                   ;                      ;
                              |                              :    ;                   ;                      ;
                              |                              :    ;                   ;                      ;
                  NOP         |                              :    ;                   ;                      ;
                              |                              :    ;                   ;                      ;
                              |                              :    ;                   ;                      ;
                              |                              :    ;                   ;                      ;
                  NOP         |                              :    ;                   ;                      ;
                              |                              :    ;                   ;                      ;
                              |                              :    ;                   ;                      ;
                              |                              :    ;                   ;                      ;
                  NOP         | DELAY = RL                   :TS1 ;RD < ADDR_1        ; SAMP < 0             ;
                              |                              :TS1 ;                   ; SAMP <  DATA         ;
                              |                              :TS1 ;                   ; SAMP < /DATA         ;
                              |                              :TS1 ;                   ; SAMP <  DATA         ;
                  NOP         |                              :TS1 ;                   ; SAMP < /DATA         ;
                              |                              :TS1 ;                   ; SAMP < /DATA         ;
                              |                              :TS1 ;                   ; SAMP <  DATA         ;
                              |                              :TS1 ;                   ; SAMP < /DATA         ;
                  NOP         |                              :TS1 ;                   ; SAMP <  DATA         ;
                              |                              :TS1 ;                   ; SAMP <  1            ;
                              |                              :    ;                   ;                      ;
                              |                              :    ;                   ;                      ;
                  NOP         |                              :    ;                   ;                      ;
                              | DELAY = 0                    :    ;                   ;                      ;
                              |                              :    ;                   ;                      ;
                              |                              :    ;                   ;                      ;
                  NOP         |                              :    ;                   ;                      ;
                              |                              :    ;                   ;                      ;
                              |                              :    ;                   ;                      ;
                              |                              :    ;                   ;                      ;
                  FOR-LOOP_1  |                              :    ;                   ;                      ;
                              |                              :    ;                   ;                      ;
                              |                              :    ;                   ;                      ;
                              |                              :    ;                   ;                      ;
                  NOP         |                              :    ;                   ;                      ;
                              |                              :    ;                   ;                      ;
                              |                              :    ;                   ;                      ;
                              |                              :    ;                   ;                      ;
             GOTO-LOOP_2 WR   |  ADDR_1 = ADDR_1 + 1         :    ;                   ;                      ;
                              |  DATA  = /DATA               :    ;                   ;                      ;
                              |                              :    ;                   ;                      ;
                              |                              :    ;                   ;                      ;
                  RTN         |                              :    ;CPA                ;                      ;
                              |                              :    ;                   ;                      ;
                              |                              :    ;                   ;                      ;
                              |                              :    ;                   ;                      ;
                  ---------------------------------------------------------------------------------------

      INCLUDE Reset
END
