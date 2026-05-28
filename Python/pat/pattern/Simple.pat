USE dram

BEGIN
      <0> START -> TEST1 -> STOP
      <1> START -> TEST2 -> STOP
      //<2> START -> RESET -> STOP

            //      CTRL                   REG                                   CMD                        
                  ----------------------------------------------------------------------------------
            TEST1# FOR-2      |                              :                    ;                 ;
                              |                              :                    ;                 ;
                              |                              :                    ;                 ;
                              |                              :                    ;                 ;
                  NOP         | ADDR = 0                     : MRWR < ADDR, 34    ;                 ; 
                              | ADDR = 1                     : MRWR < ADDR, 34    ;                 ;
                              |                              :                    ;                 ;
                              |                              :                    ;                 ;
                  FOR-0       |                              :                    ;                 ;
                              |                              :                    ;                 ;
                              |                              :                    ;                 ;
                              |                              :                    ;                 ;
            WR1#    NOP       | DATA = 0x5A                  :                    ;                 ;
                              |                              :                    ;                 ;
                              |                              :                    ;                 ;
                              |                              :                    ;                 ;
                  NOP         | ADDR = 0x04                  : WR < ADDR          ;                 ;
                              | ADDR = ADDR + 1              : WR < ADDR          ;                 ;
                              | ADDR = ADDR + 1              : WR < ADDR          ;                 ;
                              | ADDR = ADDR + 1              : WR < ADDR          ;                 ;
                  FOR-1       |                              :                    ;                 ;
                              |                              :                    ;                 ;
                              |                              :                    ;                 ;
                              |                              :                    ;                 ;
                  NOP         | DELAY = X                    :                    ; DRV < DATA      ;
                              |                              :                    ; DRV < DATA      ;
                              |                              :                    ; DRV < DATA      ;
                              |                              :                    ; DRV < DATA      ;
                  FOR-5       |                              :                    ;                 ;
                              |                              :                    ;                 ;
                              |                              :                    ;                 ;
                              |                              :                    ;                 ;
                  NOP         |                              :                    ;                 ;
                              |                              :ALERT               ;                 ;
                              |                              :                    ;                 ;
                              |                              :                    ;                 ;
                  NOP         |                              :                    ;                 ;
                              |                              :                    ;                 ;
                              |                              :                    ;                 ;
                              |                              :                    ;                 ;
            RD1#  NOP         |                              :                    ;                 ;
                              |                              :                    ;                 ;
                              |                              :                    ;                 ;
                              |                              :                    ;                 ;
                  NOP         | ADDR = 0x04                  : RD < ADDR          ;                 ;
                              | ADDR = ADDR + 1              : RD < ADDR          ;                 ;
                              | ADDR = ADDR + 1              : RD < ADDR          ;                 ;
                              | ADDR = ADDR + 1              : RD < ADDR          ;                 ;
                  FOR-1       |                              :                    ;                 ;
                              |                              :                    ;                 ;
                              |                              :                    ;                 ;
                              |                              :                    ;                 ;
                  NOP         |  DELAY = Y                   :                    ; SMP < DATA      ;
                              |                              :                    ; SMP < DATA      ;
                              |                              :                    ; SMP < DATA      ;
                              |                              :                    ; SMP < DATA      ;
                  NOP         |                              :                    ;                 ;
                              |                              :                    ;                 ;
                              |                              :                    ;                 ;
                              |                              :                    ;                 ;
                  NOP         |                              :                    ;                 ;
                              |                              :                    ;                 ;
                              |                              :                    ;                 ;
                              |                              :                    ;                 ;
                  FOR-20      |                              :                    ;                 ;
                              |                              :                    ;                 ;
                              |                              :                    ;                 ;
                              |                              :                    ;                 ;
                  NOP         |                              : CPA                ;                 ;
                              |                              :                    ;                 ;
                              |                              :                    ;                 ;
                              |                              :                    ;                 ;
                  RTN         |                              :                    ;                 ;
                              |                              :                    ;                 ;
                              |                              :                    ;                 ;
                              |                              :                    ;                 ;
                  ----------------------------------------------------------------------------------


            //       CTRL                    REG                                 CMD                      
                  ----------------------------------------------------------------------------------
            TEST2#NOP         |                              :                    ;                 ;
                              |                              :                    ;                 ;
                              |                              :                    ;                 ;
                              |                              :                    ;                 ;
                  FOR-2       |                              :                    ;                 ;
                              |                              :                    ;                 ;
                              |                              :                    ;                 ;
                              |                              :                    ;                 ;
            MRW#  NOP         | ADDR = 0                     : MRWR < ADDR, 34    ;                 ; 
                              | ADDR = 1                     : MRWR < ADDR, 34    ;                 ;
                              |                              :                    ;                 ;
                              |                              :                    ;                 ;
                  FOR-0       |                              :                    ;                 ;// This is a comment
                              |                              :                    ;                 ;
                              |                              :                    ;                 ;
                              |                              :                    ;                 ;
                  NOP         |                              :                    ;                 ;
                              |                              :                    ;                 ;
                              |                              :                    ;                 ;
                              |                              :                    ;                 ;
            MRR#  NOP         | ADDR = 0x00                  : MRRD < ADDR        ;                 ;
                              |                              :                    ;                 ;
                              |                              :                    ;                 ;
                              |                              :                    ;                 ;
                  FOR-1       |                              :                    ;                 ;
                              |                              :                    ;                 ;
                              |                              :                    ;                 ;
                              |                              :                    ;                 ;
                  NOP         | DELAY = X, DATA = 36         :                    ; SMP_MR < DATA   ;
                              |                              :                    ;                 ;
                              |                              :                    ;                 ;
                              |                              :                    ;                 ;
                  FOR-2       |                              :                    ;                 ;
                              |                              :                    ;                 ;
                              |                              :                    ;                 ;
                              |                              :                    ;                 ;
                  NOP         | ADDR = 0x01                  : MRRD < ADDR        ;                 ;
                              |                              :                    ;                 ;
                              |                              :                    ;                 ;
                              |                              :                    ;                 ;
                  FOR-1       |                              :                    ;                 ;
                              |                              :                    ;                 ;
                              |                              :                    ;                 ;
                              |                              :                    ;                 ;
                  NOP         | DELAY = Y, DATA = 34         :                    ; SMP_MR < DATA   ;
                              |                              :                    ;                 ;
                              |                              :                    ;                 ;
                              |                              :                    ;                 ;
                  NOP         |                              :                    ;                 ;
                              |                              :                    ;                 ;
                              |                              :                    ;                 ;
                              |                              :                    ;                 ;
                  FOR-20      |                              :                    ;                 ;
                              |                              :                    ;                 ;
                              |                              :                    ;                 ;
                              |                              :                    ;                 ;
                  NOP         |                              :                    ;                 ;
                              |                              :                    ;                 ;
                              |                              :                    ;                 ;
                              |                              : CPA                ;                 ;
                  RTN         |                              :                    ;                 ;
                              |                              :                    ;                 ;
                              |                              :                    ;                 ;
                              |                              :                    ;                 ;
                  ----------------------------------------------------------------------------------

      INCLUDE Reset
END