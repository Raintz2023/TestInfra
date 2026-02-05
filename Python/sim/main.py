import ate

for y in range(-10, 11, 1):

    for x in range(0, 11, 1): 
        ################# Macro #########################################
        wave_name = f"/root/Code/TestInfra/Python/wave/wave_{x}_{y}.vcd"

        top_data = 0xF0     
        
        a = ate.ATE(wave_name=wave_name, trave_enable=True, top_data_init=top_data)     

        ################# Pattern ######################################### 
        a.mr_write(addr=0, mr_data=56) 
        a.mr_write(addr=1, mr_data=54)

        for j in range(10):
            a.tick()

        addr = 0 
        a.write(addr)

        for j in range(40):
            a.tick()

        a.drive(offset=x, inverted=False)
        a.drive(offset=x, inverted=True)
        a.drive(offset=x, inverted=False)
        a.drive(offset=x, inverted=True)

        for j in range(10):
            a.tick()

        addr = 0 
        a.read(addr)

        for j in range(50):
            a.tick()

        a.sample(offset=y, inverted=False)
        a.sample(offset=y, inverted=True)
        a.sample(offset=y, inverted=False)
        a.sample(offset=y, inverted=True)

        for j in range(50):
            a.tick()

        a.compare()

        for j in range(10):
            a.tick()

        ################# Pattern ######################################### 
    print("\n")

print("\n")
