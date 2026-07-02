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

      <3> START
            GOTO-1 REG_INIT *
            GOTO-1 MRR2_BIT0_STATUS *
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
      READ_TRAIN# NOP         |                              :     ;                       ;                 ;
                              |                              :     ;                       ;                 ;
                              |                              :     ;                       ;                 ;
                              |                              :     ;                       ;                 ;
                  FOR-2       |                              :     ;                       ;                 ;
                              |                              :     ;                       ;                 ;
                              |                              :     ;                       ;                 ;
                              |                              :     ;                       ;                 ;
            MRW#  NOP         | MR_ADDR = 0x00               :     ;MRW < MR_ADDR, RL      ;                 ; 
                              |                              :     ;                       ;                 ;
                              |                              :     ;                       ;                 ;
                              |                              :     ;                       ;                 ;
                  NOP         |                              :     ;                       ;                 ;
                              |                              :     ;                       ;                 ;
                              |                              :     ;                       ;                 ;
                              |                              :     ;                       ;                 ;
            MRR#  NOP         |                              :     ;                       ;                 ;
                              |                              :     ;                       ;                 ;
                              |                              :     ;                       ;                 ;
                              |                              :     ;                       ;                 ;
                  NOP         | MR_ADDR = 0x03               :     ;                       ;                 ;
                              |                              :     ;                       ;                 ;
                              |                              :     ;                       ;                 ;
                              |                              :     ;                       ;                 ;
                  NOP         |                              : TS1 ;MRR  < MR_ADDR         ; SAMP <  0       ;
                              |                              : TS1 ;                       ; SAMP < /DATA    ;
                              |                              : TS1 ;                       ; SAMP <  DATA    ;
                              |                              : TS1 ;                       ; SAMP < /DATA    ;
                  NOP         |                              : TS1 ;                       ; SAMP <  DATA    ;
                              |                              : TS1 ;                       ; SAMP <  DATA    ;
                              |                              : TS1 ;                       ; SAMP < /DATA    ;
                              |                              : TS1 ;                       ; SAMP <  DATA    ;
                  NOP         |                              : TS1 ;                       ; SAMP < /DATA    ;
                              |                              : TS1 ;                       ; SAMP <  1       ;
                              |                              :     ;                       ;                 ;
                              |                              :     ;                       ;                 ;
                  FOR-LOOP_1  |                              :     ;                       ;                 ;
                              |                              :     ;                       ;                 ;
                              |                              :     ;                       ;                 ;
                              |                              :     ;                       ;                 ;
                  RTN         |                              : CPA ;ALERT                  ;                 ;
                              |                              :     ;ALERT                  ;                 ;
                              |                              :     ;ALERT                  ;                 ;
                              |                              :     ;ALERT                  ;                 ;
                  ----------------------------------------------------------------------------------------

            //      CTRL                   REG                                   CMD                        
                  ---------------------------------------------------------------------------------------
      WRITE_TRAIN# FOR-2      |                              :    ;                           ;                     ;
                              |                              :    ;                           ;                     ;
                              |                              :    ;                           ;                     ;
                              |                              :    ;                           ;                     ;
                  NOP         | MR_ADDR = 0                  :    ;MRW  < MR_ADDR, RL         ;                     ; 
                              | MR_ADDR = 1                  :    ;MRW  < MR_ADDR, WL         ;                     ;
                              |                              :    ;                           ;                     ;
                              |                              :    ;                           ;                     ;
                  NOP         |                              :    ;                           ;                     ;
                              |                              :    ;                           ;                     ;
                              |                              :    ;                           ;                     ;
                              |                              :    ;                           ;                     ;
                  NOP         |                              :    ;                           ;                     ;
                              |                              :    ;                           ;                     ;
                              |                              :    ;                           ;                     ;
                              |                              :    ;                           ;                     ;
                  NOP         | ARRAY_ADDR = 0x04            :    ;                           ;                     ;
                              |                              :    ;                           ;                     ;
                              |                              :    ;                           ;                     ;
                              |                              :    ;                           ;                     ;
                  NOP         |                              :    ;                           ;                     ;
                              |                              :    ;                           ;                     ;
                              |                              :    ;                           ;                     ;
                              |                              :    ;                           ;                     ;
                  NOP         |                              :    ;WT < ARRAY_ADDR            ; DRIV_START <  0     ;
                              |                              :    ;                           ; DRIV <   DATA       ;
                              |                              :    ;                           ; DRIV <  /DATA       ;
                              |                              :    ;                           ; DRIV <   DATA       ;
                  NOP         |                              :    ;                           ; DRIV <  /DATA       ;
                              |                              :    ;                           ; DRIV <  /DATA       ;
                              |                              :    ;                           ; DRIV <   DATA       ;
                              |                              :    ;                           ; DRIV <  /DATA       ;
                  NOP         |                              :    ;                           ; DRIV <   DATA       ;
                              |                              :    ;                           ; DRIV <   1          ; 
                              |                              :    ;                           ;                     ;
                              |                              :    ;                           ;                     ;
                  NOP         |                              :    ;                           ;                     ;
                              |                              :    ;                           ;                     ;
                              |                              :    ;                           ;                     ;
                              |                              :    ;                           ;                     ;
                  FOR-LOOP_1  |                              :    ;                           ;                     ;
                              |                              :    ;                           ;                     ;
                              |                              :    ;                           ;                     ;
                              |                              :    ;                           ;                     ;
                  NOP         |                              :    ;                           ;                     ;
                              |                              :    ;                           ;                     ;
                              |                              :    ;                           ;                     ;
                              |                              :    ;                           ;                     ;
                  NOP         | ARRAY_ADDR = 0x04            :    ;                           ;                     ;
                              |                              :    ;                           ;                     ;
                              |                              :    ;                           ;                     ;
                              |                              :    ;                           ;                     ;
                  NOP         |                              :    ;                           ;                     ;
                              |                              :    ;                           ;                     ;
                              |                              :    ;                           ;                     ;
                              |                              :    ;                           ;                     ;
                  NOP         |                              :TS1 ;RD < ARRAY_ADDR            ; SAMP <  0           ;
                              |                              :TS1 ;                           ; SAMP <  DATA        ;
                              |                              :TS1 ;                           ; SAMP < /DATA        ;
                              |                              :TS1 ;                           ; SAMP <  DATA        ;
                  NOP         |                              :TS1 ;                           ; SAMP < /DATA        ;
                              |                              :TS1 ;                           ; SAMP < /DATA        ;
                              |                              :TS1 ;                           ; SAMP <  DATA        ;
                              |                              :TS1 ;                           ; SAMP < /DATA        ;
                  NOP         |                              :TS1 ;                           ; SAMP <  DATA        ;
                              |                              :TS1 ;                           ; SAMP <  1           ;
                              |                              :    ;                           ;                     ;
                              |                              :    ;                           ;                     ;
                  NOP         |                              :    ;                           ;                     ;
                              |                              :    ;                           ;                     ;
                              |                              :    ;                           ;                     ;
                              |                              :    ;                           ;                     ;
                  NOP         |                              :    ;                           ;                     ;
                              |                              :    ;                           ;                     ;
                              |                              :    ;                           ;                     ;
                              |                              :    ;                           ;                     ;
                  FOR-LOOP_1  |                              :    ;                           ;                     ;
                              |                              :    ;                           ;                     ;
                              |                              :    ;                           ;                     ;
                              |                              :    ;                           ;                     ;
                  NOP         |                              :    ;CPA                        ;                     ;
                              |                              :    ;                           ;                     ;
                              |                              :    ;                           ;                     ;
                              |                              :    ;                           ;                     ;
                  RTN         |                              :    ;                           ;                     ;
                              |                              :    ;                           ;                     ;
                              |                              :    ;                           ;                     ;
                              |                              :    ;                           ;                     ;
                  ---------------------------------------------------------------------------------------

            //      CTRL                   REG                                   CMD                        
                  ---------------------------------------------------------------------------------------
      WRITE_READ# FOR-2       |                              :    ;                       ;                      ;
                              |                              :    ;                       ;                      ;
                              |                              :    ;                       ;                      ;
                              |                              :    ;                       ;                      ;
                  NOP         | MR_ADDR = 0                  :    ;MRW  < MR_ADDR, RL     ;                      ; 
                              | MR_ADDR = 1                  :    ;MRW  < MR_ADDR, WL     ;                      ;
                              |                              :    ;                       ;                      ;
                              |                              :    ;                       ;                      ;
                  NOP         |                              :    ;                       ;                      ;
                              |                              :    ;                       ;                      ;
                              |                              :    ;                       ;                      ;
                              | ARRAY_ADDR = 0x04            :    ;                       ;                      ;
            WR#   NOP         |                              :    ;                       ;                      ;
                              |                              :    ;                       ;                      ;
                              |                              :    ;                       ;                      ;
                              |                              :    ;                       ;                      ;
                  NOP         |                              :    ;                       ;                      ;
                              |                              :    ;                       ;                      ;
                              |                              :    ;                       ;                      ;
                              |                              :    ;                       ;                      ;
                  NOP         |                              :    ;                       ;                      ;
                              |                              :    ;                       ;                      ;
                              |                              :    ;                       ;                      ;
                              |                              :    ;                       ;                      ;
                  NOP         |                              :    ;WT < ARRAY_ADDR        ; DRIV_START <  0      ;
                              |                              :    ;                       ; DRIV <   DATA        ;
                              |                              :    ;                       ; DRIV <  /DATA        ;
                              |                              :    ;                       ; DRIV <   DATA        ;
                  NOP         |                              :    ;                       ; DRIV <  /DATA        ;
                              |                              :    ;                       ; DRIV <  /DATA        ;
                              |                              :    ;                       ; DRIV <   DATA        ;
                              |                              :    ;                       ; DRIV <  /DATA        ;
                  NOP         |                              :    ;                       ; DRIV <   DATA        ;
                              |                              :    ;                       ; DRIV <   1           ;
                              |                              :    ;                       ;                      ;
                              |                              :    ;                       ;                      ;
                  NOP         |                              :    ;                       ;                      ;
                              |                              :    ;                       ;                      ;
                              |                              :    ;                       ;                      ;
                              |                              :    ;                       ;                      ;
                  FOR-LOOP_1  |                              :    ;                       ;                      ;
                              |                              :    ;                       ;                      ;
                              |                              :    ;                       ;                      ;
                              |                              :    ;                       ;                      ;
            RD#   NOP         |                              :    ;                       ;                      ;
                              |                              :    ;                       ;                      ;
                              |                              :    ;                       ;                      ;
                              |                              :    ;                       ;                      ;
                  NOP         |                              :    ;                       ;                      ;
                              |                              :    ;                       ;                      ;
                              |                              :    ;                       ;                      ;
                              |                              :    ;                       ;                      ;
                  NOP         |                              :    ;                       ;                      ;
                              |                              :    ;                       ;                      ;
                              |                              :    ;                       ;                      ;
                              |                              :    ;                       ;                      ;
                  NOP         |                              :TS1 ;RD < ARRAY_ADDR        ; SAMP < 0             ;
                              |                              :TS1 ;                       ; SAMP <  DATA         ;
                              |                              :TS1 ;                       ; SAMP < /DATA         ;
                              |                              :TS1 ;                       ; SAMP <  DATA         ;
                  NOP         |                              :TS1 ;                       ; SAMP < /DATA         ;
                              |                              :TS1 ;                       ; SAMP < /DATA         ;
                              |                              :TS1 ;                       ; SAMP <  DATA         ;
                              |                              :TS1 ;                       ; SAMP < /DATA         ;
                  NOP         |                              :TS1 ;                       ; SAMP <  DATA         ;
                              |                              :TS1 ;                       ; SAMP <  1            ;
                              |                              :    ;                       ;                      ;
                              |                              :    ;                       ;                      ;
                  NOP         |                              :    ;                       ;                      ;
                              |                              :    ;                       ;                      ;
                              |                              :    ;                       ;                      ;
                              |                              :    ;                       ;                      ;
                  NOP         |                              :    ;                       ;                      ;
                              |                              :    ;                       ;                      ;
                              |                              :    ;                       ;                      ;
                              |                              :    ;                       ;                      ;
                  FOR-LOOP_1  |                              :    ;                       ;                      ;
                              |                              :    ;                       ;                      ;
                              |                              :    ;                       ;                      ;
                              |                              :    ;                       ;                      ;
                  NOP         |                              :    ;                       ;                      ;
                              |                              :    ;                       ;                      ;
                              |                              :    ;                       ;                      ;
                              |                              :    ;                       ;                      ;
             GOTO-LOOP_2 WR   |  ARRAY_ADDR = ARRAY_ADDR + 1 :    ;                       ;                      ;
                              |  DATA  = /DATA               :    ;                       ;                      ;
                              |                              :    ;                       ;                      ;
                              |                              :    ;                       ;                      ;
                  RTN         |                              :    ;CPA                    ;                      ;
                              |                              :    ;                       ;                      ;
                              |                              :    ;                       ;                      ;
                              |                              :    ;                       ;                      ;
                  ---------------------------------------------------------------------------------------

                  ---------------------------------------------------------------------------------------
MRR2_BIT5_STATUS# FOR-2       |                              :    ;                       ;                      ;
                              |                              :    ;                       ;                      ;
                              |                              :    ;                       ;                      ;
                              |                              :    ;                       ;                      ;
                  NOP         | MR_ADDR = 0                  :    ;MRW  < MR_ADDR, RL     ;                      ; 
                              | MR_ADDR = 1                  :    ;MRW  < MR_ADDR, WL     ;                      ;
                              |                              :    ;                       ;                      ;
                              |                              :    ;                       ;                      ;
                  NOP         |                              :    ;                       ;                      ;
                              |                              :    ;                       ;                      ;
                              |                              :    ;                       ;                      ;
                              | ARRAY_ADDR = 0x04            :    ;                       ;                      ;
            WR0#   NOP        |                              :    ;                       ;                      ;
                              |                              :    ;                       ;                      ;
                              |                              :    ;                       ;                      ;
                              |                              :    ;                       ;                      ;
                  NOP         |                              :    ;                       ;                      ;
                              |                              :    ;                       ;                      ;
                              |                              :    ;                       ;                      ;
                              |                              :    ;                       ;                      ;
                  NOP         |                              :    ;                       ;                      ;
                              |                              :    ;                       ;                      ;
                              |                              :    ;                       ;                      ;
                              |                              :    ;                       ;                      ;
                  NOP         |                              :    ;WT < ARRAY_ADDR        ;                      ; 
                              | MR_ADDR = 0x02               :TS1 ;MRR< MR_ADDR           ; SAMP < 0             ; // MRR MR2 BIT0 STB Y
                              |                              :TS1 ;                       ; SAMP < 0             ;
                              |                              :TS1 ;                       ; SAMP < 0             ;
                  NOP         |                              :TS1 ;                       ; SAMP < 1             ;
                              |                              :TS1 ;                       ; SAMP < 0             ;
                              |                              :TS1 ;                       ; SAMP < 0             ;
                              |                              :TS1 ;                       ; SAMP < 0             ;
                  NOP         |                              :TS1 ;                       ; SAMP < 0             ;
                              |                              :TS1 ;                       ; SAMP < 0             ;
                              |                              :TS1 ;                       ; SAMP < 1             ;
                              |                              :    ;                       ;                      ;
                  NOP         |                              :    ;                       ;                      ;
                              |                              :    ;                       ;                      ;
                              |                              :    ;                       ;                      ;
                              |                              :    ;                       ;                      ;
                  FOR-LOOP_1  |                              :    ;                       ;                      ;
                              |                              :    ;                       ;                      ;
                              |                              :    ;                       ;                      ;
                              |                              :    ;                       ;                      ;
                  FOR-LOOP_1  |                              :    ;                       ;                      ;
                              |                              :    ;                       ;                      ;
                              |                              :    ;                       ;                      ;
                              |                              :    ;                       ;                      ;
                  NOP         |                              :    ;                       ;                      ;
                              |                              :    ;                       ;                      ;
                              |                              :    ;                       ;                      ;
                              |                              :    ;                       ;                      ;
                  RTN         |                              :    ;CPA                    ;                      ;
                              |                              :    ;                       ;                      ;
                              |                              :    ;                       ;                      ;
                              |                              :    ;                       ;                      ;
                  ---------------------------------------------------------------------------------------

      INCLUDE Reset
END
