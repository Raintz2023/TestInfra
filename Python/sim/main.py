from ate import ATE
################# Macro #########################################
for y in range(-10, 11, 1):
    for x in range(0, 11, 1): 
        wave_name = f"/root/Code/TestInfra/Python/wave/wave_{x}_{y}.vcd"

        top_data = 0xF0     
        
        ate = ATE(wave_name=wave_name, trave_enable=True, top_data_init=top_data)     

        ################# Pattern ######################################### 
        ate.mr_write(addr=0, mr_data=56) 
        ate.tick()
        ate.mr_write(addr=1, mr_data=54)

        for j in range(16):
            ate.tick()

        addr = 0 
        ate.write(addr)

        for j in range(40):
            ate.tick()

        ate.drive(offset=x, inverted=False)
        ate.drive(offset=x, inverted=True)
        ate.drive(offset=x, inverted=False)
        ate.drive(offset=x, inverted=True)

        for j in range(16):
            ate.tick()

        addr = 0 
        ate.read(addr)

        for j in range(50):
            ate.tick()

        ate.sample(offset=y, inverted=False)
        ate.sample(offset=y, inverted=True)
        ate.sample(offset=y, inverted=False)
        ate.sample(offset=y, inverted=True)

        for j in range(50):
            ate.tick()

        ################# Pattern ######################################### 

        ate.compare()

    print("\n")

print("\n")
