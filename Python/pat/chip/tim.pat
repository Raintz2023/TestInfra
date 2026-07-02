TIMING {
    TS0 {
        PRD: 20
        NRZ {
            @default { EDGE: 1, BASE: 0 }
        }
        RZ  { EDGE_1: 8, EDGE_2: 10, BASE: 0 }
        RZZ { EDGE_1: 9, EDGE_2: 19, BASE: 0 }
        STB {
            @default { EDGE: 14, BASE: 0 }
        }
    }
    TS1 {
        PRD: 20
        NRZ {
            @default { EDGE: 1, BASE: 0 }
            @DQS     { EDGE: 1, BASE: 0, OPEN: 1 }
            @DQ      { EDGE: 1, BASE: 0, OPEN: 1 }
        }
        RZ  { EDGE_1: 8, EDGE_2: 10, BASE: 0 }
        RZZ { EDGE_1: 9, EDGE_2: 19, BASE: 0 }
        STB {
            @default { EDGE: 14, BASE: 0 }
            @DQS     { EDGE: 14, BASE: 0, OPEN: 1 }
            @DQ      { EDGE: 14, BASE: 0, OPEN: 1 }
        }
    }
    TS2 {
        PRD: 20
        NRZ {
            @default { EDGE: 1, BASE: 0 }
            @DQS     { EDGE: 1, BASE: 0, OPEN: 1 }
            @DQ      { EDGE: 1, BASE: 0, OPEN: 1 }
        }
        RZ  { EDGE_1: 8, EDGE_2: 10, BASE: 0 }
        RZZ { EDGE_1: 9, EDGE_2: 19, BASE: 0 }
        STB {
            @default { EDGE: 14, BASE: 0 }
            @DQS     { EDGE: 14, BASE: 0, OPEN: 1 }
            @DQ      { EDGE: 14, BASE: 0, OPEN: 1 }
        }
    }
}
