#!/usr/bin/env fish

set RTL /root/Code/TestInfra/Verilog/rtl
set CPP_INC /root/Code/TestInfra/C++/include
set CPP_SRC /root/Code/TestInfra/C++/src
set CPP_SIM /root/Code/TestInfra/C++/sim

verilator -Wall --cc \
  $RTL/Ate.v \
  $RTL/Dram.v \
  $RTL/Sampler.v \
  $RTL/Driver.v \
  $RTL/Out_Register.v \
  --exe $CPP_SIM/main.cpp  $CPP_SRC/Ate.cpp\
  --trace \
  --build \
  --top-module Ate \
  -CFLAGS "-std=c++20 -I$CPP_INC -fPIC" 

