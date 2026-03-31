cmake_minimum_required(VERSION 3.20)
project(ate LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

set(CMAKE_POSITION_INDEPENDENT_CODE ON)
set(PROJECT_ROOT "${CMAKE_CURRENT_SOURCE_DIR}/..")
set(OBJ_DIR "${CMAKE_CURRENT_SOURCE_DIR}/obj_dir")
set(PYTHON_LIB_DIR "${PROJECT_ROOT}/Python/libs")

find_package(Python3 REQUIRED COMPONENTS Interpreter Development.Module)

# Prefer the pybind11 config that belongs to the active Python if CMake cannot
# already locate it through the normal package search path.
execute_process(
    COMMAND "${Python3_EXECUTABLE}" -m pybind11 --cmakedir
    OUTPUT_VARIABLE PYBIND11_CMAKE_DIR
    OUTPUT_STRIP_TRAILING_WHITESPACE
    ERROR_QUIET
)
if(PYBIND11_CMAKE_DIR)
    list(APPEND CMAKE_PREFIX_PATH "${PYBIND11_CMAKE_DIR}")
endif()

if(NOT PYBIND11_CMAKE_DIR)
    file(GLOB LOCAL_PYBIND11_CONFIG
        "${PROJECT_ROOT}/.venv/lib/python*/site-packages/pybind11/share/cmake/pybind11"
    )
    if(LOCAL_PYBIND11_CONFIG)
        list(APPEND CMAKE_PREFIX_PATH ${LOCAL_PYBIND11_CONFIG})
    endif()
endif()

find_package(pybind11 CONFIG REQUIRED)

if(NOT EXISTS "${OBJ_DIR}/VSocket.h" OR NOT EXISTS "${OBJ_DIR}/VSocket__ALL.a")
    message(FATAL_ERROR
        "Missing Verilator generated files in ${OBJ_DIR}. "
        "Run the Verilator build first so VSocket headers and library exist."
    )
endif()

find_program(VERILATOR_EXECUTABLE verilator)

set(VERILATOR_INCLUDE_DIR "")
if(DEFINED ENV{VERILATOR_ROOT} AND EXISTS "$ENV{VERILATOR_ROOT}/include/verilated.h")
    set(VERILATOR_INCLUDE_DIR "$ENV{VERILATOR_ROOT}/include")
elseif(VERILATOR_EXECUTABLE)
    execute_process(
        COMMAND brew --prefix verilator
        OUTPUT_VARIABLE HOMEBREW_VERILATOR_PREFIX
        OUTPUT_STRIP_TRAILING_WHITESPACE
        ERROR_QUIET
    )
    if(HOMEBREW_VERILATOR_PREFIX AND EXISTS "${HOMEBREW_VERILATOR_PREFIX}/share/verilator/include/verilated.h")
        set(VERILATOR_INCLUDE_DIR "${HOMEBREW_VERILATOR_PREFIX}/share/verilator/include")
    endif()
endif()

if(NOT VERILATOR_INCLUDE_DIR)
    find_path(
        VERILATOR_INCLUDE_DIR
        NAMES verilated.h
        HINTS
            "/opt/homebrew/share/verilator/include"
            "/usr/local/share/verilator/include"
        PATH_SUFFIXES
            include
            share/verilator/include
    )
endif()

if(NOT VERILATOR_INCLUDE_DIR)
    message(FATAL_ERROR
        "Could not locate Verilator headers. Set VERILATOR_ROOT or install Verilator."
    )
endif()

pybind11_add_module(ate
    "${CMAKE_CURRENT_SOURCE_DIR}/src/Ate.cpp"
)

target_compile_definitions(ate PRIVATE ATE_PYBIND)

target_include_directories(ate PRIVATE
    "${CMAKE_CURRENT_SOURCE_DIR}/include"
    "${OBJ_DIR}"
    "${VERILATOR_INCLUDE_DIR}"
)

target_sources(ate PRIVATE
    "${VERILATOR_INCLUDE_DIR}/verilated.cpp"
    "${VERILATOR_INCLUDE_DIR}/verilated_threads.cpp"
    "${VERILATOR_INCLUDE_DIR}/verilated_vcd_c.cpp"
)

target_link_libraries(ate PRIVATE
    Python3::Module
    "${OBJ_DIR}/VSocket__ALL.a"
)

set_target_properties(ate PROPERTIES
    LIBRARY_OUTPUT_DIRECTORY "${PYTHON_LIB_DIR}"
)
