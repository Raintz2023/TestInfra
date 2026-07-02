from constant import PatternContext
from macro import Read_Train, Write_Train, Write_Read, Mrr2_Status, MRR, MR3

ctx = PatternContext()

# Train(ctx, pattern_name="Simple", testflow_num=0, x_range="10:35:1", y_range="20:40:1", trace_enable=True)

# TrainBase(ctx, test_name="TrainReadWrite",
#             pattern_name="Base", testflow_num=0, x_range="100:350:10", y_range="200:400:10", 
#             trace_enable=True, print_samples=False)

# Train(ctx, test_name="TrainOneWriteRead",
#             pattern_name="Serial", testflow_num=1, x_range="20:41:1", y_range="30:41:1", 
#             trace_enable=True, print_samples=False)
# JustTestOnce(ctx, test_name="OneWriteRead",
#             pattern_name="Serial", testflow_num=1, x_range="-10:11:1", y_range="-10:11:1", 
#             trace_enable=True, print_samples=False)

# Read_Train(ctx, test_name="ReadTrain",
#             pattern_name="Read_Train", testflow_num=0, x_range="170:201:1", y_range="130:161:1",
#             trace_enable=True, print_samples=False)

# Write_Train(ctx, test_name="WriteTrain",
#             pattern_name="Write_Train", testflow_num=0, x_range="-35:-4:1", y_range="0:6:1",
#             trace_enable=True, print_samples=False)

# MRR(ctx, test_name="MRR",
#             pattern_name="MRR", testflow_num=0, x_range="0:8:1", y_range="0:5:1",
#             trace_enable=True, print_samples=False)

# Write_Read(ctx, test_name="WriteRead",
#             pattern_name="Write_Read", testflow_num=0, x_range="0:31:1", y_range="",
#             trace_enable=True, print_samples=False)

MR3(ctx, test_name="MR3",
            pattern_name="MR3", testflow_num=0, x_range="", y_range="",
            trace_enable=True, print_samples=False)
# Mrr2_Status(ctx, test_name="Mrr2_Bit5_Status",
#             pattern_name="MR2", testflow_num=0, x_range="25:46:1", y_range="",
#             trace_enable=True, print_samples=False)

# Mrr2_Status(ctx, test_name="Mrr2_Bit1_Status",
#             pattern_name="MR2", testflow_num=1, x_range="1:15:1", y_range="",
#             trace_enable=True, print_samples=False)