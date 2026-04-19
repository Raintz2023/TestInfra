USE ../dram

BEGIN
      <0> START -> TEST1 -> STOP
      <1> START -> TEST2 -> STOP

                  CTRL        |    REG          :                CMD             ;// This is a comment
                  ---------------------------------------------------------------------
            TEST1# FOR-2      |                 :                    ;                 ;
                              |                 :                    ;                 ;
                              |                 :                    ;                 ;
                              |                 :                    ;                 ;
                  NOP         | ADDR =  0       : MRWR < ADDR, 36    ;                 ; 
                              | ADDR =  1       : MRWR < ADDR, 34    ;                 ;
                              |                 :                    ;                 ;
                              |                 :                    ;                 ;
                  FOR-0       |                 :                    ;                 ;// This is a comment
                              |                 :                    ;                 ;
                              |                 :                    ;                 ;
                              |                 :                    ;                 ;
            WR1#    NOP       | DATA = 0x5A     :                    ;                 ;
                              |                 :                    ;                 ;
                              |                 :                    ;                 ;
                              |                 :                    ;                 ;
                  NOP         | ADDR = 0x04     : WR < ADDR          ;                 ;
                              | ADDR = ADDR + 1 : WR < ADDR          ;                 ;
                              | ADDR = ADDR + 1 : WR < ADDR          ;                 ;
                              | ADDR = ADDR + 1 : WR < ADDR          ;                 ;
                  FOR-X       |                 :                    ;                 ;
                              |                 :                    ;                 ;
                              |                 :                    ;                 ;
                              |                 :                    ;                 ;
                  NOP         |                 :                    ; DRV < DATA      ;
                              |                 :                    ; DRV < DATA      ;
                              |                 :                    ; DRV < DATA      ;
                              |                 :                    ; DRV < DATA      ;
                  FOR-5       |                 :                    ;                 ;
                              |                 :                    ;                 ;
                              |                 :                    ;                 ;
                              |                 :                    ;                 ;
                  NOP         |                 :TS1                 ;                 ;
                              |                 :ALERT               ;                 ;
                              |                 :                    ;                 ;
                              |                 :                    ;                 ;
                  NOP         |                 :                    ;                 ;
                              |                 :                    ;                 ;
                              |                 :                    ;                 ;
                              |                 :                    ;                 ;
            RD1#    NOP       |                 :                    ;                 ;
                              |                 :                    ;                 ;
                              |                 :                    ;                 ;
                              |                 :                    ;                 ;
                  NOP         | ADDR = 0x04     : RD < ADDR          ;                 ;
                              | ADDR = ADDR + 1 : RD < ADDR          ;                 ;
                              | ADDR = ADDR + 1 : RD < ADDR          ;                 ;
                              | ADDR = ADDR + 1 : RD < ADDR          ;                 ;
                  FOR-Y       |                 :                    ;                 ;
                              |                 :                    ;                 ;
                              |                 :                    ;                 ;
                              |                 :                    ;                 ;
                  NOP         |                 :                    ; SMP < DATA      ;
                              |                 :                    ; SMP < DATA      ;
                              |                 :                    ; SMP < DATA      ;
                              |                 :                    ; SMP < DATA      ;
                  NOP         |                 :                    ;                 ;
                              |                 :                    ;                 ;
                              |                 :                    ;                 ;
                              |                 :                    ;                 ;
                  GOTO-0  WR1 |                 :                    ;                 ;
                              |                 :                    ;                 ;
                              |                 :                    ;                 ;
                              |                 :                    ;                 ;
                  FOR-6       |                 :                    ;                 ;
                              |                 :                    ;                 ;
                              |                 :                    ;                 ;
                              |                 :                    ;                 ;
                  NOP         |                 : CPA                ;                 ;
                              |                 :                    ;                 ;
                              |                 :                    ;                 ;
                              |                 :                    ;                 ;
                  RTN         |                 :                    ;                 ;
                              |                 :                    ;                 ;
                              |                 :                    ;                 ;
                              |                 :                    ;                 ;
                  ---------------------------------------------------------------------


                  CTRL        |    REG          :                CMD             ;// This is a comment
                  ---------------------------------------------------------------------
            TEST2#NOP         |                 :    TS1             ;                 ;
                              |                 :                    ;                 ;
                              |                 :                    ;                 ;
                              |                 :                    ;                 ;
                  FOR-2       |                 :                    ;                 ;
                              |                 :                    ;                 ;
                              |                 :                    ;                 ;
                              |                 :                    ;                 ;
                  NOP         | ADDR =  0       : MRWR < ADDR, 36    ;                 ; 
                              | ADDR =  1       : MRWR < ADDR, 34    ;                 ;
                              |                 :                    ;                 ;
                              |                 :                    ;                 ;
                  FOR-0       |                 :                    ;                 ;// This is a comment
                              |                 :                    ;                 ;
                              |                 :                    ;                 ;
                              |                 :                    ;                 ;
            WR2#    NOP       | DATA = 0x5A     :                    ;                 ;
                              |                 :                    ;                 ;
                              |                 :                    ;                 ;
                              |                 :                    ;                 ;
                  NOP         | ADDR = 0x04     : WR < ADDR          ;                 ;
                              | ADDR = ADDR + 1 : WR < ADDR          ;                 ;
                              | ADDR = ADDR + 1 : WR < ADDR          ;                 ;
                              | ADDR = ADDR + 1 : WR < ADDR          ;                 ;
                  FOR-X       |                 :                    ;                 ;
                              |                 :                    ;                 ;
                              |                 :                    ;                 ;
                              |                 :                    ;                 ;
                  NOP         |                 :                    ; DRV < DATA      ;
                              |                 :                    ; DRV < DATA      ;
                              |                 :                    ; DRV < DATA      ;
                              |                 :                    ; DRV < DATA      ;
                  FOR-5       |                 :                    ;                 ;
                              |                 :                    ;                 ;
                              |                 :                    ;                 ;
                              |                 :                    ;                 ;
                  NOP         |                 :                    ;                 ;
                              |                 :                    ;                 ;
                              |                 :                    ;                 ;
                              |                 :                    ;                 ;
                  NOP         |                 : TS0                ;                 ;
                              |                 : ALERT              ;                 ;
                              |                 :                    ;                 ;
                              |                 :                    ;                 ;
            RD2#    NOP       |                 :                    ;                 ;
                              |                 :                    ;                 ;
                              |                 :                    ;                 ;
                              |                 :                    ;                 ;
                  NOP         | ADDR = 0x04     : RD < ADDR          ;                 ;
                              | ADDR = ADDR + 1 : RD < ADDR          ;                 ;
                              | ADDR = ADDR + 1 : RD < ADDR          ;                 ;
                              | ADDR = ADDR + 1 : RD < ADDR          ;                 ;
                  FOR-Y       |                 :                    ;                 ;
                              |                 :                    ;                 ;
                              |                 :                    ;                 ;
                              |                 :                    ;                 ;
                  NOP         |                 :                    ; SMP < DATA      ;
                              |                 :                    ; SMP < DATA      ;
                              |                 :                    ; SMP < DATA      ;
                              |                 :                    ; SMP < DATA      ;
                  NOP         |                 :                    ;                 ;
                              |                 :                    ;                 ;
                              |                 :                    ;                 ;
                              |                 :                    ;                 ;
                  GOTO-0  WR2 |                 :                    ;                 ;
                              |                 :                    ;                 ;
                              |                 :                    ;                 ;
                              |                 :                    ;                 ;
                  FOR-6       |                 :                    ;                 ;
                              |                 :                    ;                 ;
                              |                 :                    ;                 ;
                              |                 :                    ;                 ;
                  NOP         |                 : CPA                ;                 ;
                              |                 :                    ;                 ;
                              |                 :                    ;                 ;
                              |                 :                    ;                 ;
                  RTN         |                 :                    ;                 ;
                              |                 :                    ;                 ;
                              |                 :                    ;                 ;
                              |                 :                    ;                 ;
                  ---------------------------------------------------------------------
END