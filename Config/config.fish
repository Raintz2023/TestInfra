############################USER############################
oh-my-posh init fish --config /opt/homebrew/opt/oh-my-posh/themes/montys.omp.json | source
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
set -gx CPP_GEN $CPP/generated
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

    set -l fast 0
    set -l build_args
    for arg in $argv
        switch $arg
            case --fast -f
                set fast 1
            case '*'
                set -a build_args $arg
        end
    end

    # Build the Verilator sim directly from the current C++ workspace layout.
    for v in VERILOG_ATE VERILOG_DUT VERILOG_PIN CPP CPP_INC CPP_GEN CPP_SRC CPP_SIM
        if not set -q $v
            echo "vbuild: missing env var '$v' (e.g. set -x $v /path/to/...)" >&2
            return 2
        end
    end

    for d in $VERILOG_ATE $VERILOG_DUT $VERILOG_PIN $CPP $CPP_INC $CPP_GEN $CPP_SRC $CPP_SIM
        if not test -d $d
            echo "vbuild: directory not found: $d" >&2
            return 2
        end
    end

    set -l trace_args --trace --trace-structs
    set -l cflags "-std=c++20 -I$CPP_INC -I$CPP_GEN -fPIC -O3 -DNDEBUG -DATE_ENABLE_TRACE"
    if test $fast -eq 1
        set trace_args
        set cflags "-std=c++20 -I$CPP_INC -I$CPP_GEN -fPIC -O3 -DNDEBUG -DVL_DEBUG=0"
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
        --exe \
        $CPP_SIM/main.cpp \
        $CPP_SRC/Ate.cpp \
        $CPP_SRC/Timing.cpp \
        $CPP_SRC/Waveform.cpp \
        --trace --trace-structs --trace-max-array 256 --trace-max-width 4096 \
        --build \
        --top-module Socket \
        -CFLAGS "-std=c++20 -I$CPP_INC -I$CPP_GEN -fPIC"

    set -l rc $status
    popd >/dev/null
    return $rc
end

function vbuild-fast --description "Build non-tracing Verilator sim for faster TestInfra runs"
    vbuild --fast $argv
end

function cbuild --description "Build Cpp sim with pybind11 using CMake (TestInfra)"
    set -l fast 0
    set -l cmake_args
    for arg in $argv
        switch $arg
            case --fast -f
                set fast 1
            case '*'
                set -a cmake_args $arg
        end
    end

    # 必要环境变量检查
    for v in CPP CPP_SIM CPP_SRC CPP_INC CPP_GEN CPP_BUILD TI_PYTHON_BIN
        if not set -q $v
            echo "cbuild: missing env var '$v' (e.g. set -x $v /path/to/...)" >&2
            return 2
        end
    end

    if not test -x $TI_PYTHON_BIN
        echo "cbuild: python not found or not executable: $TI_PYTHON_BIN" >&2
        return 2
    end

    set -l trace_opt ON
    set -l build_type RelWithDebInfo
    if test $fast -eq 1
        set trace_opt OFF
        set build_type Release
    end

    pushd $CPP_BUILD >/dev/null
    command cmake -DPython3_EXECUTABLE=$TI_PYTHON_BIN -DATE_ENABLE_TRACE=$trace_opt -DCMAKE_BUILD_TYPE=$build_type $cmake_args ..
    command make
    set -l rc $status
    popd >/dev/null
    return $rc
end

function cbuild-fast --description "Build non-tracing pybind ATE module for faster TestInfra runs"
    cbuild --fast $argv
end

function pbuild --description "Build Python sim with pattern using lark (TestInfra)"
    # ---- 必要环境变量检查（按实际使用列出来）----
    for v in TI PYTHON TI_PYTHON_BIN PYTHON_LIBS PYTHON_PAT_PATTERN PYTHON_PAT_GEN PYTHON_STUBS
        if not set -q $v
            echo "pbuild: missing env var '$v' (e.g. set -Ux $v /path/to/...)" >&2
            return 2
        end
    end

    if not test -x $TI_PYTHON_BIN
        echo "pbuild: python not found or not executable: $TI_PYTHON_BIN" >&2
        return 2
    end

    command mkdir -p $PYTHON_PAT_GEN/run

    set -l pattern_args
    set -l pattern_path "$PYTHON_PAT_PATTERN"
    set -l use_paths
    set -l include_paths
    set -l i 1
    while test $i -le (count $argv)
        set -l arg $argv[$i]
        switch $arg
            case -U --use-path
                set i (math $i + 1)
                if test $i -gt (count $argv)
                    echo "pbuild: $arg requires a path" >&2
                    return 2
                end
                set -a use_paths $argv[$i]
            case '--use-path=*'
                set -a use_paths (string replace -- "--use-path=" "" $arg)
            case '-U=*'
                set -a use_paths (string replace -- "-U=" "" $arg)
            case -I --include-path
                set i (math $i + 1)
                if test $i -gt (count $argv)
                    echo "pbuild: $arg requires a path" >&2
                    return 2
                end
                set -a include_paths $argv[$i]
            case '--include-path=*'
                set -a include_paths (string replace -- "--include-path=" "" $arg)
            case '-I=*'
                set -a include_paths (string replace -- "-I=" "" $arg)
            case -P --pattern-path
                set i (math $i + 1)
                if test $i -gt (count $argv)
                    echo "pbuild: $arg requires a path" >&2
                    return 2
                end
                set pattern_path $argv[$i]
            case '--pattern-path=*'
                set pattern_path (string replace -- "--pattern-path=" "" $arg)
            case '-P=*'
                set pattern_path (string replace -- "-P=" "" $arg)
            case --help -h
                echo "Usage: pbuild [-P PATTERN_PATH] [-U USE_PATH] [-I INCLUDE_PATH] [pattern]"
                echo "Example: pbuild -P \$PYTHON/pat/handshakeecho HandshakeEcho"
                echo "Example: pbuild -U \$PYTHON/pat -I \$PYTHON_PAT_PATTERN Base"
                return 0
            case '-*'
                echo "pbuild: unknown option: $arg" >&2
                return 2
            case '*'
                set -a pattern_args $arg
        end
        set i (math $i + 1)
    end

    if test (count $pattern_args) -gt 1
        echo "pbuild: expected at most one pattern argument" >&2
        return 2
    end

    if test (count $use_paths) -eq 0
        set -a use_paths "$PYTHON/pat"
    end
    if test (count $include_paths) -eq 0
        set -a include_paths "$pattern_path"
    end

    set -l pbuild_path_args
    for path in $use_paths
        set -a pbuild_path_args -U "$path"
    end
    for path in $include_paths
        set -a pbuild_path_args -I "$path"
    end

    function __pbuild_compile_one --no-scope-shadowing
        set -l in_file $argv[1]
        set -l stem $argv[2]
        set -l out_file "$PYTHON_PAT_GEN/run/$stem.py"

        pushd $TI >/dev/null
        command $TI_PYTHON_BIN -m Python.pat.compiler.cli $pbuild_path_args --in "$in_file" --out "$out_file"
        set -l rc $status
        popd >/dev/null

        if test $rc -ne 0
            echo "pbuild: pattern compile failed: $in_file (rc=$rc)" >&2
            return $rc
        end

        return 0
    end

    # ---- Step 1: 生成 pybind11 stubs ----
    pushd $PYTHON_LIBS >/dev/null
    command $TI_PYTHON_BIN -m pybind11_stubgen ate -o $PYTHON_STUBS
    or begin
        set -l rc $status
        popd >/dev/null
        functions -e __pbuild_compile_one
        echo "pbuild: stubgen failed (rc=$rc)" >&2
        return $rc
    end
    popd >/dev/null

    # ---- 无参数：遍历编译 pattern 目录 ----
    if test (count $pattern_args) -eq 0
        set -l compiled 0
        for in_file in $pattern_path/*.pat
            if not test -f $in_file
                continue
            end

            set -l stem (basename $in_file .pat)
            __pbuild_compile_one "$in_file" "$stem"
            or begin
                set -l rc $status
                functions -e __pbuild_compile_one
                return $rc
            end
            set compiled (math $compiled + 1)
        end

        functions -e __pbuild_compile_one
        echo "pbuild: compiled $compiled pattern file(s) from $pattern_path"
        return 0
    end

    # ---- 有参数：允许 name / name.pat / /path/name.pat ----
    set -l in_arg $pattern_args[1]
    set -l in_file ""
    set -l stem ""

    if string match -q -- "*.pat" $in_arg
        if test -f $in_arg
            set in_file $in_arg
        else
            set in_file "$pattern_path/$in_arg"
        end
        set stem (basename $in_arg .pat)
    else
        set stem $in_arg
        set in_file "$pattern_path/$stem.pat"
    end

    if not test -f $in_file
        functions -e __pbuild_compile_one
        echo "pbuild: input .pat not found: $in_file" >&2
        return 2
    end

    __pbuild_compile_one "$in_file" "$stem"
    set -l rc $status
    functions -e __pbuild_compile_one
    return $rc
end

function pingen --description "Generate schema, Verilog pin adapters, and DUT wrapper from RTL port order (TestInfra)"
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

    set -l force_args
    set -l dut_args
    for arg in $argv
        switch $arg
            case --force -f
                set -a force_args --force
            case --help -h
                echo "Usage: pingen [--force] <dut-name>" >&2
                echo "Example: pingen Dram" >&2
                echo "Example: pingen --force Chip" >&2
                return 0
            case '-*'
                echo "pingen: unknown option: $arg" >&2
                return 2
            case '*'
                set -a dut_args $arg
        end
    end

    if test (count $dut_args) -ne 1
        echo "Usage: pingen [--force] <dut-name>" >&2
        echo "Example: pingen Dram" >&2
        return 2
    end

    set -l dut_name $dut_args[1]

    pushd $TI >/dev/null
    command $TI_PYTHON_BIN $VERILOG/script/gen_dut_scaffold.py $force_args $dut_name
    or begin
        set -l rc $status
        popd >/dev/null
        return $rc
    end

    command $TI_PYTHON_BIN $VERILOG/script/gen_pin_adapter.py $dut_name
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


# OSS CAD Suite
if test -d /Users/lichenyu/Code/Learning/oss-cad-suite/bin
    set -gx PATH /Users/lichenyu/Code/Learning/oss-cad-suite/bin $PATH
end

set -x ANTHROPIC_BASE_URL https://api.deepseek.com/anthropic
set -x ANTHROPIC_AUTH_TOKEN sk-e05e73df1dd046ba81c8ebb4b1058fd9
set -x ANTHROPIC_MODEL deepseek-v4-pro[1m]
set -x ANTHROPIC_DEFAULT_OPUS_MODEL deepseek-v4-pro[1m]
set -x ANTHROPIC_DEFAULT_SONNET_MODEL deepseek-v4-pro[1m]
set -x ANTHROPIC_DEFAULT_HAIKU_MODEL deepseek-v4-flash
set -x CLAUDE_CODE_SUBAGENT_MODEL deepseek-v4-flash
set -x CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC 1
set -x CLAUDE_CODE_EFFORT_LEVEL max
