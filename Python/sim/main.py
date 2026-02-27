from ate import ATE
from Python.pat.generated.OneWriteRead import run
################# Macro #########################################
print("--- ATE Test Start ---")
for y in range(-10, 10, 1):
    for x in range(0, 10, 1): 
        wave_name = f"/home/seagull/Code/TestInfra/Python/wave/wave_{x}_{y}.vcd"

        top_data = y & 0xFF    
        
        ate = ATE(wave_name=wave_name, trace_enable=False, top_data_init=top_data)     

        ################# Pattern ######################################### 
        run(ate, x, y)
        ################# Pattern ######################################### 

        ate.compare()

    print("\n")

print("\n")
