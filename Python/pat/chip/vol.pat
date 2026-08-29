VOLTAGE {
    VS0 {@digital}

    VS1 {
        VDC: 1200MV 
        VIN {
            @default { VIL: 0 , VIH: 1 }
            @DQ      { VIL: 0.25, VIH: 0.75 }
            @DQS     { VIL: 0.25, VIH: 0.75 }
        }
        VOUT {
            @default { VOL: 0.5, VOH: 0.5 }
            @DQ      { VOL: 0.5, VOH: 0.5 }
            @DQS     { VOL: 0.5, VOH: 0.5 }
        }
    }

    VS1 {
        VDC: 1200MV 
        VIN {
            @default { VIL: 0MV, VIH: 1200MV }
            @DQ      { VIL: 300MV, VIH: 900MV }
            @DQS     { VIL: 300MV, VIH: 900MV }
        }
        VOUT {
            @default { VOL: 600MV, VOH: 600MV }
            @DQ      { VOL: 600MV, VOH: 600MV }
            @DQS     { VOL: 600MV, VOH: 600MV }
        }
    }
}
