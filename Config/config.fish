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