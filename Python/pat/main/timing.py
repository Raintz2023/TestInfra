def _read_write_timing_updates(x: int, y: int) -> dict:
    """Move TS1 drive timing by x and TS2 sample timing by y."""
    return {
        "TS1": {
            "PRD": 10,
            "NRZ": 1,
            "NRZ_BASE": x,
            "RZ": 1,
            "RZ_RETURN": 3,
            "RZ_BASE": 0,
            "RZZ_RISE": 2,
            "RZZ_FALL": 7,
            "STB": 8,
            "STB_BASE": 0,
        },
        "TS2": {
            "PRD": 10,
            "NRZ": 1,
            "NRZ_BASE": 0,
            "RZ": 1,
            "RZ_RETURN": 3,
            "RZ_BASE": 0,
            "RZZ_RISE": 2,
            "RZZ_FALL": 7,
            "STB": 8,
            "STB_BASE": y,
        },
    }


def _mr_timing_updates(x: int, y: int) -> dict:
    """Move TS1/TS2 sample timing for mode-register read training."""
    return {
        "TS1": {
            "PRD": 20,
            "NRZ": 1,
            "NRZ_BASE": 0,
            "RZ": 8,
            "RZ_RETURN": 10,
            "RZ_BASE": 0,
            "RZZ_RISE": 9,
            "RZZ_FALL": 19,
            "STB": 8,
            "STB_BASE": x,
        },
        "TS2": {
            "PRD": 10,
            "NRZ": 1,
            "NRZ_BASE": 0,
            "RZ": 1,
            "RZ_RETURN": 3,
            "RZ_BASE": 0,
            "RZZ_RISE": 2,
            "RZZ_FALL": 7,
            "STB": 8,
            "STB_BASE": y,
        },
    }


def _serial_timing_updates(x: int, y: int) -> dict:
    """Use larger Serial timing while sweeping TS1 drive and TS2 sample base."""
    return {
        "TS1": {
            "PRD": 20,
            "NRZ": 1,
            "NRZ_BASE": x,
            "RZ": 8,
            "RZ_RETURN": 10,
            "RZ_BASE": x,
            "RZZ_RISE": 9,
            "RZZ_FALL": 19,
            "RZZ_BASE": x,
            "STB": 8,
            "STB_BASE": 0,
        },
        "TS2": {
            "PRD": 20,
            "NRZ": 1,
            "NRZ_BASE": y,
            "RZ": 8,
            "RZ_RETURN": 10,
            "RZ_BASE": y,
            "RZZ_RISE": 9,
            "RZZ_FALL": 19,
            "RZZ_BASE": y,
            "STB": 8,
            "STB_BASE": y,
        },
    }

def _train_timing_updates(x: int, y: int) -> dict:
    """Use larger Serial timing while sweeping TS1 drive and TS2 sample base."""
    return {
        "TS1": {
            "PRD": 20,
            "NRZ": 1,
            "NRZ_BASE": 0,
            "RZ": 8,
            "RZ_RETURN": 10,
            "RZ_BASE": 0,
            "RZZ_RISE": 9,
            "RZZ_FALL": 19,
            "RZZ_BASE": 0,
            "STB": 14,
            "STB_BASE": x,
        },
        "TS2": {
            "PRD": 20,
            "NRZ": 1,
            "NRZ_BASE": y,
            "RZ": 8,
            "RZ_RETURN": 10,
            "RZ_BASE": y,
            "RZZ_RISE": 9,
            "RZZ_FALL": 19,
            "RZZ_BASE": y,
            "STB": 14,
            "STB_BASE": 0,
        },
    }