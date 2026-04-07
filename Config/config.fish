############################USER############################
oh-my-posh init fish --config ~/montys.omp.json | source
alias ff="fastfetch"
alias cl="clear"
if status is-interactive
    alias ls='eza --icons'
    alias ll='eza -l --icons --git'
    alias la='eza -a --icons'
end

############################BUILD############################
# -------- Project --------
set -l _ti_os (uname -s)
set -l _ti_root_mac /Users/lichenyu/Code/TestInfra
set -l _ti_root_linux /home/seagull/Code/TestInfra

if test "$_ti_os" = "Darwin"
    set -gx TI $_ti_root_mac
else if test "$_ti_os" = "Linux"
    if test -r /proc/version; and string match -qi "*microsoft*" -- (cat /proc/version)
        # WSL still uses the Linux filesystem path inside the distro.
        set -gx TI $_ti_root_linux
    else
        set -gx TI $_ti_root_linux
    end
else
    # Fallback for unexpected systems: prefer the local mac path.
    set -gx TI $_ti_root_mac
end

# -------- System --------
set -gx LD_LIBRARY_PATH /usr/lib64 $LD_LIBRARY_PATH

# -------- Verilog --------
set -gx VERILOG $TI/Verilog
set -gx VERILOG_RTL $VERILOG/rtl
set -gx VERILOG_ATE $VERILOG/ate
set -gx VERILOG_DUT $VERILOG/dut
set -gx VERILOG_PIN $VERILOG/pin
set -gx VERILOG_PINMAP $VERILOG/pinmap
set -gx VERILOG_INC $VERILOG/include
set -gx VERILOG_SRC $VERILOG/src
set -gx VERILOG_SIM $VERILOG/sim

# -------- C++ --------
set -gx CPP $TI/C++
set -gx CPP_INC $CPP/include
set -gx CPP_SRC $CPP/src
set -gx CPP_SIM $CPP/sim
set -gx CPP_BUILD $CPP/build
set -gx CPP_WAVE $CPP/wave

# -------- Python --------
set -gx PYTHON $TI/Python
set -gx TI_VENV $TI/.venv
set -gx TI_PYTHON_BIN $TI_VENV/bin/python3
set -gx PYTHON_LIBS $PYTHON/libs
set -gx PYTHON_PAT_PATTERN $PYTHON/pat/pattern
set -gx PYTHON_PAT_GEN $PYTHON/pat/generated
set -gx PYTHON_SIM $PYTHON/sim
set -gx PYTHON_STUBS $PYTHON/stubs
set -gx PYTHON_WAVE $PYTHON/wave

# Python path
set -gx PYTHONPATH $PYTHON_LIBS $PYTHONPATH


function vbuild --description "Build Verilog sim with Verilator (TestInfra)"

    # Build the Verilator sim directly from the current C++ workspace layout.
    for v in VERILOG_ATE VERILOG_DUT VERILOG_PIN CPP CPP_INC CPP_SRC CPP_SIM
        if not set -q $v
            echo "vbuild: missing env var '$v' (e.g. set -x $v /path/to/...)" >&2
            return 2
        end
    end

    for d in $VERILOG_ATE $VERILOG_DUT $VERILOG_PIN $CPP $CPP_INC $CPP_SRC $CPP_SIM
        if not test -d $d
            echo "vbuild: directory not found: $d" >&2
            return 2
        end
    end

    pushd $CPP >/dev/null

    command verilator -Wall --cc \
        $VERILOG_ATE/Socket.v \
        $VERILOG_ATE/DUT.v \
        $VERILOG_PIN/PinIn.v \
        $VERILOG_PIN/PinOut.v \
        $VERILOG_PIN/PinInAdapter.v \
        $VERILOG_PIN/PinOutAdapter.v \
        $VERILOG_DUT/*.v \
        $VERILOG_PIN/PinInDriver.v \
        $VERILOG_PIN/PinInRegister.v \
        $VERILOG_PIN/PinOutSampler.v \
        $VERILOG_PIN/PinOutRegister.v \
        --exe $CPP_SIM/main.cpp $CPP_SRC/Ate.cpp \
        --trace --trace-structs --trace-max-array 256 --trace-max-width 4096 \
        --build \
        --top-module Socket \
        -CFLAGS "-std=c++20 -I$CPP_INC -fPIC"

    set -l rc $status
    popd >/dev/null
    return $rc
end

function cbuild --description "Build Cpp sim with pybind11 using CMake (TestInfra)"
    # 必要环境变量检查
    for v in CPP CPP_SIM CPP_SRC CPP_INC CPP_BUILD TI_PYTHON_BIN
        if not set -q $v
            echo "cbuild: missing env var '$v' (e.g. set -x $v /path/to/...)" >&2
            return 2
        end
    end

    if not test -x $TI_PYTHON_BIN
        echo "cbuild: python not found or not executable: $TI_PYTHON_BIN" >&2
        return 2
    end

    pushd $CPP_BUILD >/dev/null
    command cmake -DPython3_EXECUTABLE=$TI_PYTHON_BIN ..
    command make
    set -l rc $status
    popd >/dev/null
    return $rc
end

function pbuild --description "Build Python sim with pattern using lark (TestInfra)"
    # ---- 必要环境变量检查（按实际使用列出来）----
    for v in TI TI_PYTHON_BIN PYTHON_LIBS PYTHON_PAT_PATTERN PYTHON_PAT_GEN PYTHON_STUBS
        if not set -q $v
            echo "pbuild: missing env var '$v' (e.g. set -Ux $v /path/to/...)" >&2
            return 2
        end
    end

    if not test -x $TI_PYTHON_BIN
        echo "pbuild: python not found or not executable: $TI_PYTHON_BIN" >&2
        return 2
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
    command $TI_PYTHON_BIN -m pybind11_stubgen ate -o $PYTHON_STUBS
    or begin
        set -l rc $status
        popd >/dev/null
        echo "pbuild: stubgen failed (rc=$rc)" >&2
        return $rc
    end
    popd >/dev/null

    # ---- Step 2: 生成 pattern Python ----
    pushd $TI >/dev/null
    command $TI_PYTHON_BIN -m Python.pat.cli --in "$in_file" --out "$out_file"
    or begin
        set -l rc $status
        popd >/dev/null
        echo "pbuild: pattern compile failed (rc=$rc)" >&2
        return $rc
    end
    popd >/dev/null

    return 0
end

function pingen --description "Generate Verilog pin adapters and DUT wrapper from pinmap (TestInfra)"
    for v in VERILOG TI TI_PYTHON_BIN
        if not set -q $v
            echo "pingen: missing env var '$v'" >&2
            return 2
        end
    end

    if not test -x $TI_PYTHON_BIN
        echo "pingen: python not found or not executable: $TI_PYTHON_BIN" >&2
        return 2
    end

    if test (count $argv) -ne 1
        echo "Usage: pingen <dut-name>" >&2
        echo "Example: pingen Dram" >&2
        return 2
    end

    pushd $TI >/dev/null
    command $TI_PYTHON_BIN $VERILOG/script/gen_pin_adapter.py $argv[1]
    set -l rc $status
    popd >/dev/null
    return $rc
end

alias cate="$CPP/obj_dir/VSocket"

function pate
    if not test -x $TI_PYTHON_BIN
        echo "pate: python not found or not executable: $TI_PYTHON_BIN" >&2
        return 2
    end

    pushd $TI >/dev/null
    command $TI_PYTHON_BIN -m Python.sim.main $argv
    set -l rc $status
    popd >/dev/null
    return $rc
end

function pwave --description "Open TestInfra VCD in GTKWave"
    if not set -q PYTHON
        echo "wave: missing env var PYTHON (e.g. set -Ux PYTHON $TI/Python)" >&2
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
        echo "wave: missing env var CPP (e.g. set -Ux CPP $TI/C++)" >&2
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

function venv --description "Activate local Python virtual environment in current directory"
    set -l venv_dir ./.venv
    set -l activate_script $venv_dir/bin/activate.fish
    set -l python_bootstrap /usr/sbin/python3.13

    if test -d $venv_dir
        echo "[venv] Found an existing virtual environment in the current directory: $venv_dir"
    else
        read -l -P "[venv] No virtual environment found in the current directory. Create $venv_dir? [y/N] " confirm_create
        if not string match -rq '^[Yy]$' -- $confirm_create
            echo "[venv] Virtual environment creation cancelled"
            return 1
        end

        echo "[venv] Creating virtual environment: $venv_dir"
        command $python_bootstrap -m venv --system-site-packages $venv_dir
        or begin
            set -l rc $status
            echo "[venv] Failed to create virtual environment, $python_bootstrap -m venv exit code: $rc" >&2
            return $rc
        end
        echo "[venv] Virtual environment created successfully"
    end

    if not test -f $activate_script
        echo "[venv] Activation script not found: $activate_script" >&2
        return 1
    end

    source $activate_script
    set -l rc $status

    if test $rc -eq 0
        echo "[venv] Activated virtual environment: $venv_dir"
    else
        echo "[venv] Failed to activate virtual environment, exit code: $rc" >&2
    end

    return $rc
end
