from define import TiContext
from Python.pat.physical import Period, Time, Voltage
from macro import (
    MR3,
    MRR,
    Mrr2_Status,
    Read_Eye,
    Read_Digital,
    Read_Sweep,
    Read_Train,
    Write_Eye,
    Write_Train,
)

def main() -> None:
    ctx = TiContext()

    # Read_Digital(ctx, test_name="ReadDigital",
    #             pattern_name="Read_Train", testflow_num=0, x_range="-100PS:101PS:4PS", y_range="0:10:1",
    #             trace_enable=False, print_samples=False, workers=0)

    Read_Train(ctx, test_name="ReadTrain", period=Time.PS(200), voltage=Voltage.MV(1100),
                pattern_name="Read_Train", testflow_num=0, x_range="1700PS:2001PS:20PS", y_range="1300PS:1601PS:20PS",
                trace_enable=False, print_samples=False, workers=0)

    Read_Eye(ctx, test_name="ReadEye", period=Time.PS(200), voltage=Voltage.MV(1100),
                pattern_name="Read_Train", testflow_num=0, x_range="-200PS:201PS:8PS", y_range="50MV:1151MV:50MV",
                trace_enable=False, print_samples=False, workers=0)

# Read_Sweep(ctx, test_name="DQS_SWEEP",
#             pattern_name="Read_Train", testflow_num=1, x_range="-100PS:1001PS:10PS", y_range="50MV:1151MV:50MV",
#             trace_enable=False, print_samples=False)

# Read_Sweep(ctx, test_name="DQ_SWEEP",
#             pattern_name="Read_Train", testflow_num=1, x_range="-100PS:1001PS:10PS", y_range="50MV:1151MV:50MV",
#             trace_enable=False, print_samples=False)

    # Write_Train(ctx, test_name="WriteTrain",
    #             pattern_name="Write_Train", testflow_num=0, x_range="-175PS:-19PS:5PS", y_range="0PRD:101PRD:10PRD",
    #             trace_enable=False, print_samples=False, workers=0)

# MRR(ctx, test_name="MRR",
#             pattern_name="MRR", testflow_num=0, x_range="0PRD:8PRD:1PRD", y_range="0:5:1",
#             trace_enable=True, print_samples=False)

    # Write_Eye(ctx, test_name="WriteRead",
    #             pattern_name="Write_Read", testflow_num=0, x_range="-100PS:101PS:4PS", y_range="200:0:-10",
    #             trace_enable=False, print_samples=False, workers=0)

# MR3(ctx, test_name="MR3",
#             pattern_name="MR3", testflow_num=0, x_range="", y_range="",
#             trace_enable=True, print_samples=False)
# Mrr2_Status(ctx, test_name="Mrr2_Bit5_Status",
#             pattern_name="MR2", testflow_num=0, x_range="25PRD:46PRD:1PRD", y_range="",
#             trace_enable=True, print_samples=False)

    # Mrr2_Status(ctx, test_name="Mrr2_Bit1_Status",
    #             pattern_name="MR2", testflow_num=1, x_range="1PRD:15PRD:1PRD", y_range="",
    #             trace_enable=True, print_samples=False)


if __name__ == "__main__":
    main()
