<0> START -> TEST -> STOP 

DEF MRW = E26 I2:9 I18:25     // Enable Address MR_IN
DEF WR  = E1  I2:9            // Enable Address
DEF DRV = E28 I10:17 DLY      // Enable DQ_IN Delay
DEF RD  = E0  I2:9            // Enable Address
DEF SMP =     O1:8   EXP DLY  //        DQ_OUT Expected Delay


            CTRL        |    REG          :                CMD             ;// This is a comment
            ---------------------------------------------------------------------
      TEST# FOR-2       |                 :                    ;                 ;
                        |                 :                    ;                 ;
                        |                 :                    ;                 ;
                        |                 :                    ;                 ;
            NOP         | ADDR =  0       : MRW < ADDR, 56     ;                 ; 
                        | ADDR =  1       : MRW < ADDR, 54     ;                 ;
                        |                 :                    ;                 ;
                        |                 :                    ;                 ;
            FOR-0       |                 :                    ;                 ;// This is a comment
                        |                 :                    ;                 ;
                        |                 :                    ;                 ;
                        |                 :                    ;                 ;
      WR1#   NOP        | DATA = 0x5A     :                    ;                 ;
                        |                 :                    ;                 ;
                        |                 :                    ;                 ;
                        |                 :                    ;                 ;
            NOP         | ADDR = 0x04     : WR < ADDR          ;                 ;
                        | ADDR = ADDR + 1 : WR < ADDR          ;                 ;
                        | ADDR = ADDR + 1 : WR < ADDR          ;                 ;
                        | ADDR = ADDR + 1 : WR < ADDR          ;                 ;
            FOR-4       |                 :                    ;                 ;
                        |                 :                    ;                 ;
                        |                 :                    ;                 ;
                        |                 :                    ;                 ;
            NOP         |                 :                    ; DRV < DATA, X   ;
                        |                 :                    ; DRV < DATA, X   ;
                        |                 :                    ; DRV < DATA, X   ;
                        |                 :                    ; DRV < DATA, X   ;
            FOR-5       |                 :                    ;                 ;
                        |                 :                    ;                 ;
                        |                 :                    ;                 ;
                        |                 :                    ;                 ;
            GOTO-0 STOP |                 :                    ;                 ;
                        |                 :                    ;                 ;
                        |                 :                    ;                 ;
                        |                 :                    ;                 ;
            NOP         |                 :                    ;                 ;
                        |                 :                    ;                 ;
                        |                 :                    ;                 ;
                        |                 :                    ;                 ;
      RD1#   NOP        |                 :                    ;                 ;
                        |                 :                    ;                 ;
                        |                 :                    ;                 ;
                        |                 :                    ;                 ;
            NOP         | ADDR = 0x04     : RD < ADDR          ;                 ;
                        | ADDR = ADDR + 1 : RD < ADDR          ;                 ;
                        | ADDR = ADDR + 1 : RD < ADDR          ;                 ;
                        | ADDR = ADDR + 1 : RD < ADDR          ;                 ;
            FOR-5       |                 :                    ;                 ;
                        |                 :                    ;                 ;
                        |                 :                    ;                 ;
                        |                 :                    ;                 ;
            NOP         |                 :                    ; SMP < DATA, Y   ;
                        |                 :                    ; SMP < DATA, Y   ;
                        |                 :                    ; SMP < DATA, Y   ;
                        |                 :                    ; SMP < DATA, Y   ;
            NOP         |                 :                    ;                 ;
                        |                 :                    ;                 ;
                        |                 :                    ;                 ;
                        |                 :                    ;                 ;
            GOTO-0  WR  |                 :                    ;                 ;
                        |                 :                    ;                 ;
                        |                 :                    ;                 ;
                        |                 :                    ;                 ;
            FOR-6       |                 :                    ;                 ;
                        |                 :                    ;                 ;
                        |                 :                    ;                 ;
                        |                 :                    ;                 ;
            RTN         |                 : CPA                ;                 ;
                        |                 :                    ;                 ;
                        |                 :                    ;                 ;
                        |                 :                    ;                 ;
            ---------------------------------------------------------------------

            ----------------------------------------------------------------
      RESET#NOP         |                 : RST             ;              ;
                        |                 :                 ;              ;
                        |                 :                 ;              ;
                        |                 :                 ;              ;
            RTN         |                 :                 ;              ;
                        |                 :                 ;              ;
                        |                 :                 ;              ;
                        |                 :                 ;              ;
            ----------------------------------------------------------------
