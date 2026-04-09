BEGIN
      <1> START -> TRAINING -> STOP 
      <2> START -> TEST -> STOP 
      <3> START -> RESET -> STOP

      INCLUDE ../def/DramPin

                  CTRL        |    REG          :                CMD             ;// This is a comment
                  ---------------------------------------------------------------------
            TRAINING#FOR-2    |                 :                    ;                 ;
                              |                 :                    ;                 ;
                              |                 :                    ;                 ;
                              |                 :                    ;                 ;
                  NOP         | ADDR =  0       : MRW < ADDR, 55     ;                 ; 
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
                  ---------------------------------------------------------------------



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
      INCLUDE ./Reset

END
