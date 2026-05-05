from constant import PatContext
from macro import JustTestOnce, Train, TrainBase

ctx = PatContext()

# Train(ctx, pattern_name="Simple", testflow_num=0, top_data=255, x_range="10:35:1", y_range="20:40:1", timing_name="TS0", trace_enable=True)
TrainBase(ctx, pattern_name="Base", testflow_num=0, top_data=255, x_range="10:35:1", y_range="200:400:10", timing_name="TS0", trace_enable=True)

JustTestOnce(ctx, pattern_name="Base", testflow_num=0, top_data=255)
