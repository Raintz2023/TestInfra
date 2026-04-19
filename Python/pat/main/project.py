from constant import PatContext
from macro import JustTestOnce, Train

ctx = PatContext()

Train(ctx, pattern_name="Simple", testflow_num=1, top_data=255, x_range="0:20:1", y_range="0:20:1", timing_name="TS0")

JustTestOnce(ctx, pattern_name="Simple", testflow_num=0, top_data=255)
