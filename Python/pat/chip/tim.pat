TIMING {
    TS0 {
        PRD: 100PS
        NRZ {
            @default { EDGE: 0.05, BASE: 0 }
            @DQS     { EDGE: 0.05, BASE: 0 }
            @DQ      { EDGE: 0.05, BASE: 0 }
        }
        RZ  { EDGE_1: 0.40, EDGE_2: 0.50, BASE: 0 }
        RZZ { EDGE_1: 0.45, EDGE_2: 0.95, BASE: 0 }
        STB {
            @default { EDGE: 0.70, BASE: 0 }
            @DQS     { EDGE: 0.70, BASE: 0 }
            @DQ      { EDGE: 0.70, BASE: 0 }
        }
    }

    TS1 {
        PRD: 100PS
        NRZ {
            @default { EDGE: 5PS, BASE: 0 }
            @DQS     { EDGE: 5PS, BASE: 0 }
            @DQ      { EDGE: 5PS, BASE: 0 }
        }
        RZ  { EDGE_1: 40PS, EDGE_2: 50PS, BASE: 0 }
        RZZ { EDGE_1: 45PS, EDGE_2: 95PS, BASE: 0 }
        STB {
            @default { EDGE: 70PS, BASE: 0 }
            @DQS     { EDGE: 70PS, BASE: 0 }
            @DQ      { EDGE: 70PS, BASE: 0 }
        }
    }
}
