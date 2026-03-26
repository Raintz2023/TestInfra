TOP = Socket
INCLUDE_DIR = /home/seagull/Code/TestInfra/Verilog/include

all:
	verilator -cc ../ate/Socket.v \
		../ate/DUT.v \
		../pin/PinIn.v \
		../pin/PinOut.v \
		../pin/PinInAdapter.v \
		../pin/PinOutAdapter.v \
		../pin/Comparer.v \
		../dut/*.v \
		../pin/PinInDriver.v \
		../pin/PinInRegister.v \
		../pin/PinOutSampler.v \
		../pin/PinOutRegister.v \
		--exe main.cpp ../src/Ate.cpp \
		--top-module $(TOP) \
		-CFLAGS -I$(INCLUDE_DIR) \
		--trace

	make -C obj_dir -f V$(TOP).mk

	./obj_dir/V$(TOP)
