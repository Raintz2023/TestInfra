TIMING
// 必须存在PRD 其他如果不写对应波形驱动点 那么默认无法驱动该波形
// 因此 apply_phase需要增加判断 
// 虽然现在STB只有一种采样波形 但是仍然需要和其他波形对齐
    SET TS0 = [PRD 10] [NRZ 1] [RZZ 2 7] [STB 8]
    SET TS1 = [PRD 20] [NRZ 2] [RZZ 4 14] [STB 16]
END