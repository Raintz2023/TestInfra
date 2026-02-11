from ate import ATE
from Python.pat.generated._one_write_read_gen import run
################# Macro #########################################
for y in range(0, 200, 10):
    for x in range(0, 128, 4): 
        wave_name = f"/root/Code/TestInfra/Python/wave/wave_{x}_{y}.vcd"

        top_data = y & 0xFF    
        
        ate = ATE(wave_name=wave_name, trace_enable=False, top_data_init=top_data)     

        ################# Pattern ######################################### 
        run(ate, x, y)
        ################# Pattern ######################################### 

        ate.compare()

    print("\n")

print("\n")
