from constant import PatContext
from macro import JustTestOnce, Train, TrainBase

ctx = PatContext()

# Train(ctx, pattern_name="Simple", testflow_num=0, top_data=255, x_range="10:35:1", y_range="20:40:1", timing_name="TS0", trace_enable=True)

# TrainBase(ctx, test_name="TrainReadWrite",
#             pattern_name="Base", testflow_num=0, top_data=255, x_range="100:350:10", y_range="200:400:10", 
#             timing_name="TS0", trace_enable=True, print_samples=False)

Train(ctx, test_name="TrainOneWriteRead",
            pattern_name="Serial", testflow_num=0, top_data=0, x_range="10:40:1", y_range="30:60:1", 
            timing_name="TS0", trace_enable=False, print_samples=False)
JustTestOnce(ctx, test_name="OneWriteRead",
            pattern_name="Serial", testflow_num=1, top_data=0, x_range="-200:200:10", y_range="-200:200:10", 
            timing_name="TS0", trace_enable=True, print_samples=False)
