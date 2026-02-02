if status is-interactive
    # Commands to run in interactive sessions can go here
end
oh-my-posh init fish --config ~/montys.omp.json | source
alias nf="fastfetch"
alias cl="clear"
# export LD_LIBRARY_PATH=/usr/lib64:$LD_LIBRARY_PATH
set -x LD_LIBRARY_PATH /usr/lib64 $LD_LIBRARY_PATH
set -x PYTHONPATH /root/Code/TestInfra/Python/libs $PYTHONPATH

set VERILOG /root/Code/TestInfra/Verilog

alias ver="$VERILOG/ver.fish"
alias ate="$VERILOG/obj_dir/VAte"
alias stubgen="python3.13 -m pybind11_stubgen ate -o /root/Code/TestInfra/Python/stubs"

function wave
    gtkwave "$VERILOG/wave/wave_$argv[1].vcd"
end

if status is-interactive
    alias ls='eza --icons'
    alias ll='eza -l --icons --git'
    alias la='eza -a --icons'
end