REGISTER {
    DEFINE {
        8'LOOP[0-3]    // ROLE: LOOP, unsigned
        8'ADDR[0-2]    // ROLE: ARG, unsigned
        8'X            // ROLE: ARG, signed
        8'Y            // ROLE: ARG, signed
        8'Z[0-2]       // ROLE: ARG, unsigned
        8'TEMP         // ROLE: ARG, signed
        1'DATA         // ROLE: EXPECT, unsigned
    }

    ALIAS {
        ADDR_0 = ARRAY_ADDR
        ADDR_1 = MR_ADDR
        ADDR_2 = FOO_ADDR
        Z_0 = RL
        Z_1 = WL
        Z_2 = VREF
    }

    DEFAULT {
        RL = 0
        WL = 0
    }
}
