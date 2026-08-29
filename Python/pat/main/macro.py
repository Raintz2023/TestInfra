from define import TiContext, TiScanCases
from Python.pat.physical import Period, Time, Voltage
from subroutine import (
    sr_parse_range,
    sr_rotate_right8,
    sr_read_write_delay,
    sr_voltage_window,
    sr_load_pattern,
    sr_pass_window,
    sr_pass_windows,
    sr_print_test_start,
    sr_print_test_stop,
    sr_print_scan_grid,
    sr_run_scan_cases,
    sr_window_center,
)

def Read_Train(context: TiContext,
            test_name:str,
            pattern_name:str,
            testflow_num:int=0,
            x_range:str='',
            y_range:str='',
            period:Time=Time.PS(100),
            voltage:Voltage=Voltage.MV(1200),
            trace_enable:bool=False,
            print_samples:bool=False,
            workers:int=1):

    # --- Inputs and scan axes ---
    XR = sr_parse_range(x_range, Time.PS)
    YR = sr_parse_range(y_range, Time.PS)
    pattern = sr_load_pattern(pattern_name)

    sr_print_test_start(test_name)

    RL = Period(35)
    WL = Period(35)
    Reg = pattern.Reg
    Reg.RL = RL
    Reg.WL = WL

    # --- Build independent DQS and DQ scan configurations ---
    x_cases = TiScanCases("dqs")
    for X in XR:
        session = pattern.ti_create_scan_session()
        session.ti_timing("TS0").prd = period
        # session.ti_timing("TS1").prd = period

        session.ti_timing("TS0").stb.variant("DQS").base = X
        session.ti_timing("TS0").stb.variant("DQ").close = True
        sr_read_write_delay(session, RL, WL)
        x_cases.append(session, X, trace_enable=trace_enable)

    y_cases = TiScanCases("dq")
    for Y in YR:
        session = pattern.ti_create_scan_session()
        session.ti_timing("TS0").prd = period
        session.ti_voltage("VS1").vdc = voltage
        # session.ti_timing("TS1").prd = period

        session.ti_timing("TS0").stb.variant("DQS").close = True
        session.ti_timing("TS0").stb.variant("DQ").base = Y
        sr_read_write_delay(session, RL, WL)
        y_cases.append(session, Y, trace_enable=trace_enable)

    # --- Execute scans ---
    x_results = sr_run_scan_cases(
        x_cases,
        testflow_num=testflow_num,
        workers=workers,
    )
    y_results = sr_run_scan_cases(
        y_cases,
        testflow_num=testflow_num,
        workers=workers,
    )

    # --- Analyze and persist training results ---
    X_PASS_WINDOW = sr_pass_window(XR, x_results)
    Y_PASS_WINDOW = sr_pass_window(YR, y_results)

    sr_print_scan_grid(
        x_results, XR, x_name="X"
    )
    print()
    sr_print_scan_grid(
        y_results, YR, x_name="Y"
    )
    print()

    context["READ_DQS_BASE"] = sr_window_center(X_PASS_WINDOW)
    context["READ_DQ_BASE"] = sr_window_center(Y_PASS_WINDOW)

    print(f"X = {context.ti_get('READ_DQS_BASE', Time.PS)} ")
    print(f"Y = {context.ti_get('READ_DQ_BASE', Time.PS)} \n")

    context.ti_export_vars("Python/pat/training/chip.py", "READ_DQS_BASE", "READ_DQ_BASE")

    sr_print_test_stop(test_name)


def Read_Eye(context: TiContext,
            test_name:str,
            pattern_name:str,
            testflow_num:int=0,
            x_range:str='',
            y_range:str='',
            period:Time=Time.PS(100),
            voltage:Voltage=Voltage.MV(1200),
            trace_enable:bool=False,
            print_samples:bool=False,
            workers:int=1):

    # --- Inputs and trained values ---
    context.ti_import_vars("Python/pat/training/chip.py")

    XR = sr_parse_range(x_range, Time.PS)
    YR = sr_parse_range(y_range, Voltage.MV)
    pattern = sr_load_pattern(pattern_name)

    READ_DQS_BASE = context.ti_get("READ_DQS_BASE", Time.PS)
    READ_DQ_BASE = context.ti_get("READ_DQ_BASE", Time.PS)

    sr_print_test_start(test_name)

    RL = Period(35)
    WL = Period(35)
    Reg = pattern.Reg
    Reg.RL = RL
    Reg.WL = WL

    # --- Build independent timing and voltage scan configurations ---
    cases = TiScanCases()
    for Y in YR:
        for X in XR:
            session = pattern.ti_create_scan_session()
            session.ti_timing("TS0").prd = period
            session.ti_voltage("VS1").vdc = voltage
            # Timing
            session.ti_timing("TS0").stb.variant("DQS").base = READ_DQS_BASE + X
            session.ti_timing("TS0").stb.variant("DQ").base = READ_DQ_BASE + X
            sr_read_write_delay(session, RL, WL)

            # Voltage
            VOL, VOH = sr_voltage_window(Y, Voltage.MV(50))
            session.ti_voltage("VS1").vout.variant("DQ").vol = VOL
            session.ti_voltage("VS1").vout.variant("DQ").voh = VOH
            session.ti_voltage("VS1").vout.variant("DQS").vol = VOL
            session.ti_voltage("VS1").vout.variant("DQS").voh = VOH

            cases.append(
                session,
                X,
                Y,
                trace_enable and X == Time.PS(0) and Y == Voltage.MV(600),
            )

    # --- Execute and report scan ---
    results = sr_run_scan_cases(
        cases,
        testflow_num=testflow_num,
        workers=workers,
    )
    sr_print_scan_grid(results, XR, YR)

    sr_print_test_stop(test_name)


def Read_Digital(context: TiContext,
            test_name:str,
            pattern_name:str,
            testflow_num:int=0,
            x_range:str='',
            y_range:str='',
            trace_enable:bool=False,
            print_samples:bool=False,
            workers:int=1):

    # --- Inputs and trained values ---
    context.ti_import_vars("Python/pat/training/chip.py")

    XR = sr_parse_range(x_range, Time.PS)
    YR = sr_parse_range(y_range, int)
    pattern = sr_load_pattern(pattern_name)

    READ_DQS_BASE = context.ti_get("READ_DQS_BASE", Time.PS)
    READ_DQ_BASE = context.ti_get("READ_DQ_BASE", Time.PS)

    sr_print_test_start(test_name)

    RL = Period(35)
    WL = Period(35)
    Reg = pattern.Reg
    Reg.RL = RL
    Reg.WL = WL

    # --- Build independent timing and voltage scan configurations ---
    cases = TiScanCases()
    for Y in YR:
        for X in XR:
            session = pattern.ti_create_scan_session()

            # Timing
            session.ti_timing("TS1").stb.variant("DQS").base = READ_DQS_BASE + X
            session.ti_timing("TS1").stb.variant("DQ").base = READ_DQ_BASE + X
            sr_read_write_delay(session, RL, WL)

            # Number
            cases.append(
                session,
                X,
                Y,
                trace_enable and X == Time.PS(0) and Y == 0,
            )

    # --- Execute and report scan ---
    results = sr_run_scan_cases(
        cases,
        testflow_num=testflow_num,
        workers=workers,
    )
    sr_print_scan_grid(results, XR, YR)

    sr_print_test_stop(test_name)

def Read_Sweep(context: TiContext,
            test_name:str,
            pattern_name:str,
            testflow_num:int=0,
            x_range:str='',
            y_range:str='',
            trace_enable:bool=False,
            print_samples:bool=False,
            workers:int=1):

    # --- Inputs and trained values ---
    context.ti_import_vars("Python/pat/training/chip.py")

    XR = sr_parse_range(x_range, Time.PS)
    YR = sr_parse_range(y_range, Voltage.MV)
    pattern = sr_load_pattern(pattern_name)

    READ_DQS_BASE = context.ti_get("READ_DQS_BASE", Time.PS)
    READ_DQ_BASE = context.ti_get("READ_DQ_BASE", Time.PS)

    sr_print_test_start(test_name)

    RL = Period(35)
    WL = Period(35)
    Reg = pattern.Reg
    Reg.RL = RL
    Reg.WL = WL

    # --- Build selected DQ or DQS sweep configurations ---
    cases = TiScanCases()
    for Y in YR:
        for X in XR:
            session = pattern.ti_create_scan_session()

            # Timing
            session.ti_timing("TS1").stb.variant("DQS").base = READ_DQS_BASE + X
            session.ti_timing("TS1").stb.variant("DQ").base = READ_DQ_BASE + X
            if test_name == "DQS_SWEEP":
                session.ti_timing("TS1").stb.variant("DQ").close = True
            elif test_name == "DQ_SWEEP":
                session.ti_timing("TS1").stb.variant("DQS").close = True
            sr_read_write_delay(session, RL, WL)

            # Voltage
            VOL, VOH = sr_voltage_window(Y, Voltage.MV(50))
            session.ti_voltage("VS1").vout.variant("DQ").vol = VOL
            session.ti_voltage("VS1").vout.variant("DQ").voh = VOH
            session.ti_voltage("VS1").vout.variant("DQS").vol = VOL
            session.ti_voltage("VS1").vout.variant("DQS").voh = VOH

            cases.append(
                session,
                X,
                Y,
                trace_enable and X == Time.PS(0) and Y == Voltage.MV(600),
            )

    # --- Execute and report scan ---
    results = sr_run_scan_cases(
        cases,
        testflow_num=testflow_num,
        workers=workers,
    )
    sr_print_scan_grid(results, XR, YR)


    sr_print_test_stop(test_name)


def Write_Train(context: TiContext,
            test_name:str,
            pattern_name:str,
            testflow_num:int=0,
            x_range:str='',
            y_range:str='',
            trace_enable:bool=False,
            print_samples:bool=False,
            workers:int=1):

    # --- Inputs and trained read timing ---
    context.ti_import_vars("Python/pat/training/chip.py")

    XR = sr_parse_range(x_range, Time.PS)
    YR = sr_parse_range(y_range, Period)
    pattern = sr_load_pattern(pattern_name)

    READ_DQS_BASE = context.ti_get("READ_DQS_BASE", Time.PS)
    READ_DQ_BASE = context.ti_get("READ_DQ_BASE", Time.PS)

    sr_print_test_start(test_name)

    RL = Period(35)
    WL = Period(35)
    Reg = pattern.Reg
    Reg.RL = RL
    Reg.WL = WL
    # --- Build write timing scan configurations ---
    cases = TiScanCases()
    for Y in YR:
        for X in XR:
            session = pattern.ti_create_scan_session()
            session.ti_timing("TS1").stb.variant("DQS").base = READ_DQS_BASE
            session.ti_timing("TS1").stb.variant("DQ").base = READ_DQ_BASE
            sr_read_write_delay(session, RL, WL)

            session.ti_timing("TS1").nrz.variant("DQS").base = Time.PS(0)
            session.ti_timing("TS1").nrz.variant("DQ").base = X
            session.ti_command("W").delay += Y
            session.ti_command("WDQSH").delay += Y
            session.ti_command("WDQSL").delay += Y

            cases.append(session, X, Y, trace_enable)

    # --- Execute scan ---
    results = sr_run_scan_cases(
        cases,
        testflow_num=testflow_num,
        workers=workers,
    )
    # --- Analyze and persist training results ---
    X_PASS_WINDOW, Y_PASS_WINDOW = sr_pass_windows(XR, YR, results)
    sr_print_scan_grid(results, XR, YR)

    print()

    context["DQ_TO_DQS_BASE"] = sr_window_center(X_PASS_WINDOW)
    context["WRITE_DQ_DQS_DELAY"] = sr_window_center(Y_PASS_WINDOW)

    print(f"X = {context.ti_get('DQ_TO_DQS_BASE', Time.PS)} phases\n")
    print(f"Y = {context.ti_get('WRITE_DQ_DQS_DELAY', Period)}\n")

    context.ti_export_vars("Python/pat/training/chip.py", "DQ_TO_DQS_BASE", "WRITE_DQ_DQS_DELAY")

    sr_print_test_stop(test_name)

def Write_Eye(context: TiContext,
            test_name:str,
            pattern_name:str,
            testflow_num:int=0,
            x_range:str='',
            y_range:str='',
            trace_enable:bool=False,
            print_samples:bool=False,
            workers:int=1):

    # --- Inputs and trained timing ---
    context.ti_import_vars("Python/pat/training/chip.py")

    XR = sr_parse_range(x_range, Time.PS)
    YR = sr_parse_range(y_range, int)

    pattern = sr_load_pattern(pattern_name)

    sr_print_test_start(test_name)

    RL = Period(35)
    WL = Period(35)
    Reg = pattern.Reg
    Reg.RL = RL
    Reg.WL = WL
    READ_DQS_BASE = context.ti_get("READ_DQS_BASE", Time.PS)
    READ_DQ_BASE = context.ti_get("READ_DQ_BASE", Time.PS)
    DQ_TO_DQS_BASE = context.ti_get("DQ_TO_DQS_BASE", Time.PS)
    WRITE_DQ_DQS_DELAY = context.ti_get("WRITE_DQ_DQS_DELAY", Period)

    # --- Build write-eye scan configurations ---
    cases = TiScanCases()
    for Y in YR:
        for X in XR:
            Reg.VREF = Y
            session = pattern.ti_create_scan_session()

            # Timing
            session.ti_timing("TS1").stb.variant("DQS").base = READ_DQS_BASE
            session.ti_timing("TS1").stb.variant("DQ").base = READ_DQ_BASE
            sr_read_write_delay(session, RL, WL)
            session.ti_timing("TS1").nrz.variant("DQS").base = Time.PS(0)
            session.ti_timing("TS1").nrz.variant("DQ").base = DQ_TO_DQS_BASE + X
            session.ti_command("W").delay += WRITE_DQ_DQS_DELAY
            session.ti_command("WDQSH").delay += WRITE_DQ_DQS_DELAY
            session.ti_command("WDQSL").delay += WRITE_DQ_DQS_DELAY

            cases.append(
                session,
                X,
                Y,
                trace_enable
                and X in (Time.PS(0), Time.PS(12), Time.PS(-12))
                and Y == 90,
            )

    # --- Execute and report scan ---
    results = sr_run_scan_cases(
        cases,
        testflow_num=testflow_num,
        workers=workers,
    )
    sr_print_scan_grid(
        results,
        XR,
        YR,
        y_name="VREF",
        print_samples=print_samples,
    )


    print()
    sr_print_test_stop(test_name)

def Write_Read(context: TiContext,
            test_name:str,
            pattern_name:str,
            testflow_num:int=0,
            x_range:str='',
            y_range:str='',
            trace_enable:bool=False,
            print_samples:bool=False):

    # --- Inputs and trained values ---
    context.ti_import_vars("Python/pat/training/chip.py")

    XR = sr_parse_range(x_range, Time.PS)
    pattern = sr_load_pattern(pattern_name)

    sr_print_test_start(test_name)

    RL = Period(35)
    WL = Period(35)
    Reg = pattern.Reg
    Reg.RL = RL
    Reg.WL = WL
    READ_DQS_BASE = context.ti_get("READ_DQS_BASE", Time.PS)
    READ_DQ_BASE = context.ti_get("READ_DQ_BASE", Time.PS)
    DQ_TO_DQS_BASE = context.ti_get("DQ_TO_DQS_BASE", Time.PS)
    WRITE_DQ_DQS_DELAY = context.ti_get("WRITE_DQ_DQS_DELAY", Period)

    # --- Create and configure one ATE session ---
    session = pattern.ti_create_session(
        wave_name=pattern.ti_wave_path(f"write_read.vcd"),
        trace_enable=trace_enable,
    )

    session.ti_timing("TS1").stb.variant("DQS").base = READ_DQS_BASE
    session.ti_timing("TS1").stb.variant("DQ").base = READ_DQ_BASE

    sr_read_write_delay(session, RL, WL)

    session.ti_timing("TS1").nrz.variant("DQS").base = Time.PS(0)   # fixed DQS
    session.ti_timing("TS1").nrz.variant("DQ").base = DQ_TO_DQS_BASE
    session.ti_command("W").delay += WRITE_DQ_DQS_DELAY
    session.ti_command("WDQSH").delay += WRITE_DQ_DQS_DELAY
    session.ti_command("WDQSL").delay += WRITE_DQ_DQS_DELAY

    # --- Execute and report ---
    compare_results = session.ti_run(testflow_num)

    session.ti_print_samples(print_samples)
    session.ti_print_compare_results()

    print()
    sr_print_test_stop(test_name)

def tWTR(context: TiContext,
            test_name:str,
            pattern_name:str,
            testflow_num:int=0,
            x_range:str='',
            y_range:str='',
            trace_enable:bool=False,
            print_samples:bool=False,
            workers:int=1):

    # --- Inputs and trained values ---
    context.ti_import_vars("Python/pat/training/chip.py")

    XR = sr_parse_range(x_range, Period)
    pattern = sr_load_pattern(pattern_name)

    sr_print_test_start(test_name)


    RL = Period(35)
    WL = Period(35)
    Reg = pattern.Reg
    Reg.RL = RL
    Reg.WL = WL
    READ_DQS_BASE = context.ti_get("READ_DQS_BASE", Time.PS)
    READ_DQ_BASE = context.ti_get("READ_DQ_BASE", Time.PS)
    DQ_TO_DQS_BASE = context.ti_get("DQ_TO_DQS_BASE", Time.PS)
    WRITE_DQ_DQS_DELAY = context.ti_get("WRITE_DQ_DQS_DELAY", Period)
    # --- Build tWTR scan configurations ---
    cases = TiScanCases()
    for X in XR:
        session = pattern.ti_create_scan_session()
        session.ti_timing("TS1").stb.variant("DQS").base = READ_DQS_BASE
        session.ti_timing("TS1").stb.variant("DQ").base = READ_DQ_BASE

        session.ti_command("RD").delay = X
        sr_read_write_delay(session, RL + X - Period(4), WL)

        session.ti_timing("TS1").nrz.variant("DQS").base = Time.PS(0)
        session.ti_timing("TS1").nrz.variant("DQ").base = DQ_TO_DQS_BASE
        session.ti_command("W").delay += WRITE_DQ_DQS_DELAY
        session.ti_command("WDQSH").delay += WRITE_DQ_DQS_DELAY
        session.ti_command("WDQSL").delay += WRITE_DQ_DQS_DELAY

        cases.append(session, X, trace_enable=trace_enable)
    # --- Execute and report scan ---
    results = sr_run_scan_cases(
        cases,
        testflow_num=testflow_num,
        workers=workers,
    )
    X_PASS_WINDOW = sr_pass_window(XR, results)
    sr_print_scan_grid(results, XR, x_name="X")

    print()
    print(X_PASS_WINDOW)
    sr_print_test_stop(test_name)

def Mrr2_Status(context: TiContext,
                test_name:str,
                pattern_name:str,
                testflow_num:int=0,
                x_range:str='',
                y_range:str='',
                trace_enable:bool=False,
                print_samples:bool=False,
    workers:int=1):
    """Sweep command delay while checking MR2 status behavior."""

    # --- Inputs and trained values ---
    XR = sr_parse_range(x_range, Period)

    pattern = sr_load_pattern(pattern_name)

    sr_print_test_start(test_name)
    context.ti_import_vars("Python/pat/training/chip.py")
    READ_DQS_BASE = context.ti_get("READ_DQS_BASE", Time.PS)
    READ_DQ_BASE = context.ti_get("READ_DQ_BASE", Time.PS)
    RL = Period(35)
    WL = Period(35)
    Reg = pattern.Reg
    Reg.RL = RL
    Reg.WL = WL

    # --- Build MR2 status scan configurations ---
    cases = TiScanCases(test_name)
    for X in XR:
        session = pattern.ti_create_scan_session()
        session.ti_timing("TS1").stb.variant("DQS").base = READ_DQS_BASE
        session.ti_timing("TS1").stb.variant("DQ").base = READ_DQ_BASE
        sr_read_write_delay(session, RL, WL)
        session.ti_command("R").delay += X
        session.ti_command("RDQSL").delay += X
        session.ti_command("RDQSH").delay += X
        session.ti_command("MRR").delay += X

        cases.append(session, X, trace_enable=trace_enable)
    # --- Execute scan ---
    results = sr_run_scan_cases(
        cases,
        testflow_num=testflow_num,
        workers=workers,
    )
    # --- Analyze status window ---
    X_PASS_WINDOW = sr_pass_window(XR, results)
    sr_print_scan_grid(results, XR, x_name="X")

    print()

    context["XT"] = sr_window_center(X_PASS_WINDOW).count

    print(f"X = {context.ti_get('XT', int)}\n")

    sr_print_test_stop(test_name)

def MRR(context: TiContext,
                test_name:str,
                pattern_name:str,
                testflow_num:int=0,
                x_range:str='',
                y_range:str='',
                trace_enable:bool=False,
                print_samples:bool=False,
    workers:int=1):
    """Sweep MRR timing and print each mode-register result window."""

    # --- Inputs and trained values ---
    context.ti_import_vars("Python/pat/training/chip.py")

    XR = sr_parse_range(x_range, Period)
    YR = sr_parse_range(y_range, int)

    pattern = sr_load_pattern(pattern_name)

    sr_print_test_start(test_name)
    READ_DQS_BASE = context.ti_get("READ_DQS_BASE", Time.PS)
    READ_DQ_BASE = context.ti_get("READ_DQ_BASE", Time.PS)

    RL = Period(35)
    WL = Period(35)
    Reg = pattern.Reg
    Reg.RL = RL
    Reg.WL = WL

    # --- Build MRR timing and register scan configurations ---
    cases = TiScanCases()
    for Y in YR:
        for X in XR:
            Reg.TEMP = Y
            session = pattern.ti_create_scan_session()
            session.ti_timing("TS1").stb.variant("DQS").close = True
            session.ti_timing("TS1").stb.variant("DQ").base = READ_DQ_BASE
            sr_read_write_delay(session, RL, WL)
            session.ti_command("R").delay += X

            cases.append(session, X, Y, trace_enable)

    # --- Execute and report scan ---
    results = sr_run_scan_cases(
        cases,
        testflow_num=testflow_num,
        workers=workers,
    )
    sr_print_scan_grid(
        results,
        XR,
        YR,
        y_name="MR",
        print_samples=print_samples,
    )

    sr_print_test_stop(test_name)

def MR3(context: TiContext,
                test_name:str,
                pattern_name:str,
                testflow_num:int=0,
                x_range:str='',
                y_range:str='',
                trace_enable:bool=False,
    print_samples:bool=False):
    """Validate the rotating MR3 payload with a precomputed DEQUE."""

    # --- Inputs and trained values ---
    context.ti_import_vars("Python/pat/training/chip.py")

    XR = sr_parse_range(x_range, int)
    YR = sr_parse_range(y_range, int)

    pattern = sr_load_pattern(pattern_name)

    sr_print_test_start(test_name)
    READ_DQS_BASE = context.ti_get("READ_DQS_BASE", Time.PS)
    READ_DQ_BASE = context.ti_get("READ_DQ_BASE", Time.PS)

    RL = Period(35)
    WL = Period(35)
    Reg = pattern.Reg
    Reg.RL = RL
    Reg.WL = WL

    # --- Prepare expected rotating payload ---
    deque = []
    payload = 0x5A
    for _ in range(32):
        deque.extend((payload >> bit) & 1 for bit in range(8))
        payload = sr_rotate_right8(payload)

    # --- Create and configure one ATE session ---
    session = pattern.ti_create_session(
        wave_name=pattern.ti_wave_path(f"MR3.vcd"),
        trace_enable=trace_enable
    )
    session.ti_timing("TS1").stb.variant("DQS").base = READ_DQS_BASE
    session.ti_timing("TS1").stb.variant("DQ").base = READ_DQ_BASE
    sr_read_write_delay(session, RL, WL)

    # --- Execute and report ---
    compare_results = session.ti_run(testflow_num, DEQUE=deque)

    session.ti_print_samples(print_samples)
    session.ti_print_compare_results()

    print()
    sr_print_test_stop(test_name)
