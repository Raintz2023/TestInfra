TOP = Socket

all:
	verilator -cc ../pin/Socket.v \
		../pin/PinIn.v \
		../pin/PinOut.v \
		../pin/Encoder.v \
		../pin/PinInDriver.v \
		../pin/PinInRegister.v \
		../pin/PinOutSampler.v \
		../pin/PinOutRegister.v \
		--exe main.cpp \
		--trace

	make -C obj_dir -f V$(TOP).mk

	./obj_dir/V$(TOP)
