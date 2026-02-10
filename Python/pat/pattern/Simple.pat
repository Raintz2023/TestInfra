 CTRL |        REG         :                CMD                ;
----------------------------------------------------------------
NOP   |                    : MRW < ADDR, 56  ;                 ; 
      |                    : MRW < ADDR, 54  ;                 ;
      |                    :                 ;                 ;
      |                    :                 ;                 ;
FOR-4 | ADDR = 0, VAL = 56 : MRW < ADDR, VAL ;                 ; 
      | ADDR = 1, VAL = 54 : MRW < ADDR, VAL ;                 ;
      |                    :                 ;                 ;
      |                    :                 ;                 ;
NOP   | ADDR = 0           : MRW < ADDR, 57  ;                 ; 
      |           VAL = 54 : MRW < ADDR, VAL ;                 ;
      |                    :                 ;                 ;
      |                    :                 ;                 ;
FOR-2 | ADDR = ADDR + 1    : MRW < ADDR, 57  ;                 ; 
      |       VAL = VAL + 1: MRW < ADDR, VAL ;                 ;
      |                    :                 ;                 ;
      |                    :                 ;                 ;
----------------------------------------------------------------