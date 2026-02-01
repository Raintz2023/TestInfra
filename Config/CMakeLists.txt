cmake_minimum_required(VERSION 3.20)
project(ate LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(VERILATOR_INC /usr/share/verilator/include)
set(OBJDIR /root/Code/TestInfra/Verilog/obj_dir)

# Python
find_package(Python3 REQUIRED COMPONENTS Interpreter Development)

# pybind11
find_package(pybind11 CONFIG REQUIRED)

# 你的绑定模块
pybind11_add_module(ate ./src/Ate.cpp)

# 你自己的头文件目录
target_include_directories(ate PRIVATE
    ${CMAKE_CURRENT_SOURCE_DIR}/include
)

# Verilator headers + Verilator 生成的 obj_dir（VAte.h 在这里）
target_include_directories(ate PRIVATE
    ${OBJDIR}
    ${VERILATOR_INC}
)

target_sources(ate PRIVATE
  ${VERILATOR_INC}/verilated.cpp
  ${VERILATOR_INC}/verilated_threads.cpp
  ${VERILATOR_INC}/verilated_vcd_c.cpp
  ${OBJDIR}/VAte__ALL.cpp
)

# target_link_libraries(ate PRIVATE
#   ${OBJDIR}/VAte__ALL.a
#   pthread
# )

# # 如果你的 Ate.cpp 里直接用到了 Verilator 的实现文件/库，可能还需要链接 pthread 等
target_link_libraries(ate PRIVATE Python3::Python)

# 输出目录
set_target_properties(ate PROPERTIES
    LIBRARY_OUTPUT_DIRECTORY "/root/Code/TestInfra/Python/libs"
)

# 增加编译选项
target_compile_definitions(ate PRIVATE ATE_PYBIND)