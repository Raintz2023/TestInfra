############################USER############################
oh-my-posh init fish --config ~/montys.omp.json | source
alias ff="fastfetch"
alias cl="clear"
if status is-interactive
    alias ls='eza --icons'
    alias ll='eza -l --icons --git'
    alias la='eza -a --icons'
end
set -x LD_LIBRARY_PATH /usr/lib64 $LD_LIBRARY_PATH
set -x PYTHONPATH /root/Code/TestInfra/Python/libs $PYTHONPATH

############################BUILD############################
set -x TI /root/Code/TestInfra

set -x VERILOG /root/Code/TestInfra/Verilog
set -x VERILOG_RTL /root/Code/TestInfra/Verilog/rtl

set -x CPP /root/Code/TestInfra/C++
set -x CPP_INC /root/Code/TestInfra/C++/include
set -x CPP_SRC /root/Code/TestInfra/C++/src
set -x CPP_SIM /root/Code/TestInfra/C++/sim
set -x CPP_BUILD /root/Code/TestInfra/C++/build
set -x CPP_WAVE /root/Code/TestInfra/C++/wave

set -x PYTHON /root/Code/TestInfra/Python
set -x PYTHON_LIBS /root/Code/TestInfra/Python/libs
set -x PYTHON_PAT_PATTERN /root/Code/TestInfra/Python/pat/pattern
set -x PYTHON_PAT_GEN /root/Code/TestInfra/Python/pat/pattern/generated
set -x PYTHON_SIM /root/Code/TestInfra/Python/sim
set -x PYTHON_STUBS /root/Code/TestInfra/Python/stubs
set -x PYTHON_WAVE /root/Code/TestInfra/Python/wave


function vbuild --description "Build Verilog sim with Verilator (TestInfra)"
    set -l proj /root/Code/TestInfra
    set -l cdir $proj/C++

    # 必要环境变量检查
    for v in VERILOG_RTL CPP_SIM CPP_SRC CPP_INC
        if not set -q $v
            echo "vbuild: missing env var '$v' (e.g. set -x $v /path/to/...)" >&2
            return 2
        end
    end

    if not test -d $cdir
        echo "vbuild: directory not found: $cdir" >&2
        return 2
    end

    pushd $cdir >/dev/null

    command verilator -Wall --cc \
        $VERILOG_RTL/Ate.v \
        $VERILOG_RTL/Dram.v \
        $VERILOG_RTL/Sampler.v \
        $VERILOG_RTL/Driver.v \
        $VERILOG_RTL/Out_Register.v \
        --exe $CPP_SIM/main.cpp $CPP_SRC/Ate.cpp \
        --trace --trace-max-array 256 --trace-max-width 256 \
        --build \
        --top-module Ate \
        -CFLAGS "-std=c++20 -I$CPP_INC -fPIC"

    set -l rc $status
    popd >/dev/null
    return $rc
end

function cbuild --description "Build Cpp sim with pybind11 using CMake (TestInfra)"
    # 必要环境变量检查
    for v in CPP CPP_SIM CPP_SRC CPP_INC CPP_BUILD
        if not set -q $v
            echo "cbuild: missing env var '$v' (e.g. set -x $v /path/to/...)" >&2
            return 2
        end
    end

    pushd $CPP_BUILD >/dev/null
    command cmake ..
    command make
    set -l rc $status
    popd >/dev/null
    return $rc
end

function pbuild --description "Build Python sim with pattern using lark (TestInfra)"
    # ---- 必要环境变量检查（按实际使用列出来）----
    for v in TI PYTHON_LIBS PYTHON_PAT_PATTERN PYTHON_PAT_GEN PYTHON_STUBS
        if not set -q $v
            echo "pbuild: missing env var '$v' (e.g. set -Ux $v /path/to/...)" >&2
            return 2
        end
    end

    # ---- 参数检查 ----
    if test (count $argv) -lt 1
        echo "Usage: pbuild <name|name.pat|/full/path/to/file.pat>" >&2
        return 2
    end

    # ---- 解析输入：允许 name / name.pat / /path/name.pat ----
    set -l in_arg $argv[1]
    set -l in_file ""
    set -l stem ""

    if string match -q -- "*.pat" $in_arg
        # 传了 .pat
        if test -f $in_arg
            # 传的是完整/相对路径文件
            set in_file $in_arg
        else
            # 只传了文件名（带 .pat），在默认 pattern 目录下找
            set in_file "$PYTHON_PAT_PATTERN/$in_arg"
        end
        set stem (basename $in_arg .pat)
    else
        # 没传 .pat，当成名字
        set stem $in_arg
        set in_file "$PYTHON_PAT_PATTERN/$stem.pat"
    end

    if not test -f $in_file
        echo "pbuild: input .pat not found: $in_file" >&2
        return 2
    end

    # ---- 输出文件：永远生成 <stem>.py ----
    command mkdir -p $PYTHON_PAT_GEN
    set -l out_file "$PYTHON_PAT_GEN/$stem.py"

    # ---- Step 1: 生成 pybind11 stubs ----
    pushd $PYTHON_LIBS >/dev/null
    command python3 -m pybind11_stubgen ate -o $PYTHON_STUBS
    or begin
        set -l rc $status
        popd >/dev/null
        echo "pbuild: stubgen failed (rc=$rc)" >&2
        return $rc
    end
    popd >/dev/null

    # ---- Step 2: 生成 pattern Python ----
    pushd $TI >/dev/null
    command python3 -m Python.pat.cli --in "$in_file" --out "$out_file"
    or begin
        set -l rc $status
        popd >/dev/null
        echo "pbuild: pattern compile failed (rc=$rc)" >&2
        return $rc
    end
    popd >/dev/null

    return 0
end

alias cate="$CPP/obj_dir/VAte"

function pate
    pushd $TI >/dev/null
    command python -m Python.sim.main
    set -l rc $status
    popd >/dev/null
    return $rc
end

function pwave --description "Open TestInfra VCD in GTKWave"
    if not set -q PYTHON
        echo "wave: missing env var PYTHON (e.g. set -Ux PYTHON /root/Code/TestInfra/Python)" >&2
        return 2
    end

    set -l n (count $argv)
    if test $n -lt 1 -o $n -gt 2
        echo "Usage: wave <a> [b]" >&2
        return 2
    end

    set -l base "wave_$argv[1]"
    if test $n -eq 2
        set base "wave_$argv[1]_$argv[2]"
    end

    set -l vcd "$PYTHON/wave/$base.vcd"

    if not test -f $vcd
        echo "wave: file not found: $vcd" >&2
        return 1
    end

    command gtkwave $vcd
end

function cwave --description "Open TestInfra VCD in GTKWave"
    if not set -q CPP
        echo "wave: missing env var CPP (e.g. set -Ux CPP /root/Code/TestInfra/C++)" >&2
        return 2
    end

    set -l n (count $argv)
    if test $n -lt 1 -o $n -gt 2
        echo "Usage: wave <a> [b]" >&2
        return 2
    end

    set -l base "wave_$argv[1]"
    if test $n -eq 2
        set base "wave_$argv[1]_$argv[2]"
    end

    set -l vcd "$CPP/wave/$base.vcd"

    if not test -f $vcd
        echo "wave: file not found: $vcd" >&2
        return 1
    end

    command gtkwave $vcd
end