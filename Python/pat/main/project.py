from constant import PatternContext
from macro import Read_Train, Write_Train, Write_Read

ctx = PatternContext()

# Train(ctx, pattern_name="Simple", testflow_num=0, top_data=255, x_range="10:35:1", y_range="20:40:1", trace_enable=True)

# TrainBase(ctx, test_name="TrainReadWrite",
#             pattern_name="Base", testflow_num=0, top_data=255, x_range="100:350:10", y_range="200:400:10", 
#             trace_enable=True, print_samples=False)

# Train(ctx, test_name="TrainOneWriteRead",
#             pattern_name="Serial", testflow_num=1, top_data=0, x_range="20:41:1", y_range="30:41:1", 
#             trace_enable=True, print_samples=False)
# JustTestOnce(ctx, test_name="OneWriteRead",
#             pattern_name="Serial", testflow_num=1, top_data=0, x_range="-10:11:1", y_range="-10:11:1", 
#             trace_enable=True, print_samples=False)
Read_Train(ctx, test_name="ReadTrain",
            pattern_name="Serial", testflow_num=0, top_data=0, x_range="30:60:2", y_range="", 
            trace_enable=True, print_samples=False)

Write_Train(ctx, test_name="WriteTrain",
            pattern_name="Serial", testflow_num=1, top_data=0, x_range="", y_range="20:41:1", 
            trace_enable=True, print_samples=False)

Write_Read(ctx, test_name="WriteRead",
            pattern_name="Serial", testflow_num=2, top_data=0, x_range="", y_range="", 
            trace_enable=True, print_samples=False)
