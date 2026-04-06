<1> START -> TEST1 -> STOP 
// <2> START -> TEST2 -> STOP 

DEF MRW = E26 I2:9 I18:25     // Enable Address MR_IN
DEF WR  = E1  I2:9            // Enable Address
DEF DRV = E28 I10:17 DLY      // Enable DQ_IN Delay
DEF RD  = E0  I2:9            // Enable Address
DEF SMP =     O1:8   EXP DLY  //        DQ_OUT Expected Delay

            CTRL        |    REG          :                CMD             ;// This is a comment
            ----------------------------------------------------------------
      TEST1#FOR-2       |                 :                    ;                 ;
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
      WR#   NOP         | DATA = 0x5A     :                    ;                 ;
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
      RD#   NOP         |                 :                    ;                 ;
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
            ----------------------------------------------------------------


//            ----------------------------------------------------------------
//      TEST2#FOR-2       |                 :                 ;              ;
//                        |                 :                 ;              ;
//                        |                 :                 ;              ;
//                        |                 :                 ;              ;
//            NOP         | ADDR =  0       : MRW < ADDR, 56  ;              ; 
//                        | ADDR =  1       : MRW < ADDR, 54  ;              ;
//                        |                 :                 ;              ;
//                        |                 :                 ;              ;
//            FOR-0       |                 :                 ;              ;// This is a comment
//                        |                 :                 ;              ;
//                        |                 :                 ;              ;
//                        |                 :                 ;              ;
//            NOP         |                 :                 ;              ;
//                        |                 :                 ;              ;
//                        |                 :                 ;              ;
//                        | ADDR =  0       :                 ;              ;
//            NOP         |                 :                 ;              ;
//                        |                 :                 ;              ;
//                        |                 :                 ;              ;
//                        | ADDR = ADDR + 4 : WR < ADDR       ;              ;
//            FOR-5       |                 :                 ;              ;
//                        |                 :                 ;              ;
//                        |                 :                 ;              ;
//                        |                 :                 ;              ;
//            NOP         |                 :                 ; DRV < X      ;
//                        |                 :                 ; DRV < X, T   ;
//                        |                 :                 ; DRV < X      ;
//                        |                 :                 ; DRV < X, T   ;
//            FOR-2       |                 :                 ;              ;
//                        |                 :                 ;              ;
//                        |                 :                 ;              ;
//                        |                 :                 ;              ;
//            GOTO-0 STOP |                 :                 ;              ;
//                        |                 :                 ;              ;
//                        |                 :                 ;              ;
//                        |                 :                 ;              ;
//            NOP         |                 :                 ;              ;
//                        |                 :                 ;              ;
//                        |                 :                 ;              ;
//                        | ADDR =  0       :                 ;              ;
//            NOP         |                 :                 ;              ;
//                        |                 :                 ;              ;
//                        |                 :                 ;              ;
//                        | ADDR = ADDR + 4 : RD < ADDR       ;              ;
//            FOR-6       |                 :                 ;              ;
//                        |                 :                 ;              ;
//                        |                 :                 ;              ;
//                        |                 :                 ;              ;
//            NOP         |                 :                 ; SMP < Y      ;
//                        |                 :                 ; SMP < Y, T   ;
//                        |                 :                 ; SMP < Y      ;
//                        |                 :                 ; SMP < Y, T   ;
//            GOTO-0 TEST2|                 :                 ;              ;
//                        |                 :                 ;              ;
//                        |                 :                 ;              ;
//                        |                 :                 ;              ;
//            FOR-6       |                 :                 ;              ;
//                        |                 :                 ;              ;
//                        |                 :                 ;              ;
//                        |                 :                 ;              ;
//            RTN         |                 :                 ;              ;
//                        |                 :                 ;              ;
//                        |                 :                 ;              ;
//                        |                 :                 ;              ;
//            ----------------------------------------------------------------//

//            ----------------------------------------------------------------
//      RESET#NOP         |                 : RST             ;              ;
//                        |                 :                 ;              ;
//                        |                 :                 ;              ;
//                        |                 :                 ;              ;
//            RTN         |                 :                 ;              ;
//                        |                 :                 ;              ;
//                        |                 :                 ;              ;
//                        |                 :                 ;              ;
//            ----------------------------------------------------------------
