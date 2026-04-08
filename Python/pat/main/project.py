from constant import PatContext
from macro import JustTestOnce, Train

ctx = PatContext()

Train(ctx, pattern_name="OneWriteRead", testflow_num=1, top_data=255, x_range="0:30:1", y_range="0:30:1")

JustTestOnce(ctx, pattern_name="Simple", testflow_num=0, top_data=255)
