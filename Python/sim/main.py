import ate

for i in range(-10, 11, 1):
    ################# Macro #########################################
    wave_name = f"/root/Code/TestInfra/Python/wave/wave_{i}.vcd"  

    top_data = 0xFF     

    a = ate.ATE(wave_name=wave_name, trave_enable=True, top_data_init=top_data)     

    ################# Pattern ######################################### 
    a.mr_write(addr=0, mr_data=56) 

    a.tick() 

    addr = 0 
    a.write(addr) 

    addr += 1
    a.reverse_top_data()
    a.write(addr)

    addr += 1
    a.reverse_top_data()
    a.write(addr)

    addr += 1
    a.reverse_top_data()
    a.write(addr)

    a.reverse_top_data()

    addr = 0
    a.read(addr)
    addr += 1
    # a.tick()
    a.read(addr)
    addr += 1
    # a.tick()
    a.read(addr)
    addr += 1
    # a.tick()
    a.read(addr)
    addr += 1

    for j in range(50):
        a.tick()

    a.sample(i)

    a.reverse_top_data()
    a.sample(i)

    a.reverse_top_data()
    a.sample(i)

    a.reverse_top_data()
    a.sample(i)

    for j in range(40):
        a.tick()

    ################# Macro ######################################### 
    a.compare()

a.print('\n')