from __future__ import annotations
from pathlib import Path
from Python.pat.cls import *
from Python.pat.ir import *


def _def_map(def_list: list[DefCmd]) -> dict[str, DefCmd]:
    return {def_cmd.name: def_cmd for def_cmd in def_list}


def _validate_defs(def_list: list[DefCmd]) -> None:
    seen = set()
    for def_cmd in def_list:
        if def_cmd.name in seen:
            raise ValueError(f"Duplicate DEF {def_cmd.name}")
        seen.add(def_cmd.name)

        exp_roles = [role for role in def_cmd.roles if role.kind == "EXP"]
        dly_roles = [role for role in def_cmd.roles if role.kind == "DLY"]
        out_roles = [role for role in def_cmd.roles if role.kind == "O"]
        if len(exp_roles) > 1:
            raise ValueError(f"DEF {def_cmd.name} has more than one EXP")
        if len(dly_roles) > 1:
            raise ValueError(f"DEF {def_cmd.name} has more than one DLY")
        if exp_roles and not out_roles:
            raise ValueError(f"DEF {def_cmd.name} uses EXP without O field")


def _expected_arg_count(def_cmd: DefCmd) -> int:
    count = sum(1 for role in def_cmd.roles if role.kind == "I")
    if def_cmd.has_exp():
        count += 1
    if def_cmd.has_dly():
        count += 1
    return count


def _collect_vars(ir_list: list) -> list[str]:
    names = []
    default_names = ["X", "Y", "ADDR", "VAL", "TEMP"]
    for name in default_names:
        if name not in names:
            names.append(name)
    for ins in ir_list:
        if isinstance(ins, ASSIGN) and ins.name not in names:
            names.append(ins.name)
    return names


def _helper_params(def_cmd: DefCmd) -> list[str]:
    params = []
    input_idx = 0
    for role in def_cmd.roles:
        if role.kind == "I":
            params.append(f"v{input_idx}")
            input_idx += 1
    if def_cmd.has_exp():
        params.append("exp")
    if def_cmd.has_dly():
        params.append("dly")
    return params


def _emit_helper(lines: list[str], def_cmd: DefCmd) -> None:
    fn_name = f"_cmd_{def_cmd.name.lower()}"
    params = _helper_params(def_cmd)
    signature = ", ".join(["ate_obj"] + params)
    lines.append(f"def {fn_name}({signature}):")

    has_dly = def_cmd.has_dly()
    input_idx = 0
    output_role = None
    has_drive = False

    for role in def_cmd.roles:
        if role.kind == "E":
            if has_dly:
                lines.append(f"    ate_obj.stage_drive_pin({role.start}, True, delay=dly)")
            else:
                lines.append(f"    ate_obj.stage_drive_pin({role.start}, True)")
            has_drive = True
        elif role.kind == "I":
            width = role.width()
            arg = f"v{input_idx}"
            input_idx += 1
            if has_dly:
                lines.append(
                    f"    ate_obj.stage_drive_field({role.start}, {width}, {arg}, delay=dly)"
                )
            else:
                lines.append(
                    f"    ate_obj.stage_drive_field({role.start}, {width}, {arg})"
                )
            has_drive = True
        elif role.kind == "O":
            output_role = role

    if has_drive:
        lines.append("    ate_obj.pulse_drive()")

    if output_role is not None and def_cmd.has_exp():
        width = output_role.width()
        lines.append("    ate_obj.set_top_data(exp)")
        if has_dly:
            lines.append(
                f"    ate_obj.sample(ate.CompareSpec.field({output_role.start}, {width}, dly))"
            )
        else:
            lines.append(
                f"    ate_obj.sample(ate.CompareSpec.field({output_role.start}, {width}, 0))"
            )

    if not has_drive and output_role is None:
        lines.append("    pass")

    lines.append("")


def _emit_cmd_call(ins: CmdCall, defs: dict[str, DefCmd]) -> str:
    if ins.name not in defs:
        return f"# TODO unsupported CMD: {ins.name} has no DEF"
    def_cmd = defs[ins.name]
    expected = _expected_arg_count(def_cmd)
    if len(ins.args) != expected:
        return (
            f"# TODO unsupported CMD: {ins.name} expects {expected} args by DEF, "
            f"got {len(ins.args)} ({ins.args})"
        )

    args = ", ".join(str(arg) for arg in ins.args)
    if args:
        return f"_cmd_{ins.name.lower()}(ate_obj, {args})"
    return f"_cmd_{ins.name.lower()}(ate_obj)"


def get_label_dict(ir_list:list):    
    key_ctrl_count = 0
    label_dict = {}
    # print(ir_list)
    for ins in ir_list:
        # print(ins)
        if isinstance(ins, CTRL) and not isinstance(ins, NO_CTRL):
            if ins.label != "NO_LABEL":
                # print(ins.label)
                # print(label_dict.keys())
                # if ins.label in label_dict.keys():
                #     raise LabelError(f"{ins.label} is duplicate, wrong label line number is {key_ctrl_count * 4}.")
                label_dict[ins.label] = 12 * key_ctrl_count  # The reason for using 12 is that there are 12 valid statements in each CTRL block.
            key_ctrl_count += 1
    return label_dict


def find_duplicate_labels(label_dict_list: list[dict[str, int]]) -> list[str]:
    seen: set[str] = set()
    duplicates: list[str] = []
    duplicate_set: set[str] = set()

    for label_dict in label_dict_list:
        for label in label_dict:
            if label in seen:
                if label not in duplicate_set:
                    duplicates.append(label)
                    duplicate_set.add(label)
                continue
            seen.add(label)
    return duplicates


def split_ir_list(ir_list:list):
    """ 
        Split the ir list according to RTN
    """
    pointer = 0
    pointer_list = [0]
    spliting_ir_list = []
    for ins in ir_list:
        pointer += 1
        if isinstance(ins, RTN):
            pointer_list.append(pointer + 11)
    for i in range(len(pointer_list)-1):
        spliting_ir_list.append(ir_list[pointer_list[i]:pointer_list[i+1]])
    if not spliting_ir_list:
        raise RtnError("No RTN block in Pattern.")
    return spliting_ir_list

def emit_python(testflow_list:list[Row], def_list:list[DefCmd], ir_list:list, out_path: str | Path, func_name: str = "run") -> None:
    """
    Convert testflow and ir list to python script
    Supported:
        TICK -> ate.tick()
        MRW  -> ate.mr_write()
    """
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    defs = _def_map(def_list)
    _validate_defs(def_list)

    lines: list[str] = []
    lines.append("# Auto-generated. DO NOT EDIT.")
    lines.append("")
    # lines.append("from ate import ATE")
    lines.append("import ate")
    lines.append("")

    for def_cmd in def_list:
        _emit_helper(lines, def_cmd)

    vars_ = _collect_vars(ir_list)
    defaults = ", ".join(f"{name}=0" for name in vars_)
    lines.append(f"def {func_name}(ate_obj: ate.ATE, TESTFLOW=1, {defaults}):")
    lines.append("    T = 1")
    lines.append("    F = 0")

    # all_label_list and spliting_ir_list one by one
    spliting_label_list = []
    # print(ir_list)
    spliting_ir_list = split_ir_list(ir_list)
    # print(spliting_ir_list)
    for spliting_ir in spliting_ir_list:
        spliting_label_list.append(get_label_dict(spliting_ir))
    duplicate_labels = find_duplicate_labels(spliting_label_list)
    if duplicate_labels != []:
        raise LabelError(f"{", ".join(duplicate_labels)} is duplicate.")
        
    # for i in range(len(all_label_list)):
    #     trans_line(lines=lines, ir_list=spliting_ir_list[i], label_dict=all_label_list[i])

    testflow_num = []
    for testflow in testflow_list:
        # 第一层循环：外部传入testflow num来控制执行
        if testflow.reg in testflow_num:
            raise TestflowNumError(f"Testflow number {testflow.reg} is duplicated")
        lines.append(f"    if TESTFLOW == {testflow.reg}:")
        for testflow_label in testflow.cmd2.split(','):
            # 第二层循环： 该条testflow的所有label
            testflow_label_use_num = 0
            for i, label in enumerate(spliting_label_list):
                # 第三层循环： 判断tf_label是否存在于spliting_label_list中，并获取label的pc以及对应的ir_list
                if testflow_label in label.keys():
                    testflow_label_use_num += 1
                    pc_init = label[testflow_label]
                    trans_line(pc_init, lines=lines, ir_list=spliting_ir_list[i], label_dict=label, defs=defs)
                else:
                    continue
            if testflow_label_use_num == 0:
                raise UnknownTestflowLabelError(f"{testflow_label} cannot be found in testflow")
        testflow_num.append(testflow.reg)

    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

def ctrl_counter(pc, ctrl_count):
    if ctrl_count != 0:
        raise CtrlError(f"{int((pc-1)/3)} line's CTRL block is not conform to the standard (4 Way).")
    else:
        ctrl_count += 3
    return ctrl_count

def trans_line(pc_init:int, lines:list, ir_list:list, label_dict:dict, defs:dict[str, DefCmd]):
    pc = pc_init
    ir_list_len = len(ir_list)
    cmd_count = 0
    ctrl_count = 0
    goto_count = 0
    rtn_count = 0
    goto_target = ""
    compare_count = 0
    while True:
        ins = ir_list[pc]
        pc += 1
        if pc == ir_list_len:
            break
        #########################CMD#########################
        if isinstance(ins, TICK):
            lines.append(f"{indent}ate_obj.tick()")
            lines.append(f"{indent}ate_obj.tick()")
            cmd_count += 1

        elif isinstance(ins, CmdCall):
            lines.append(f"{indent}{_emit_cmd_call(ins, defs)}")
            cmd_count += 1

        elif isinstance(ins, CPA):
            compare_count += 1
            lines.append(f"{indent}compare_result = ate_obj.compare_all()")
            cmd_count += 1

        elif isinstance(ins, CPL):
            compare_count += 1
            lines.append(f"{indent}compare_result = ate_obj.compare_last()")
            cmd_count += 1

        elif isinstance(ins, CCR):
            compare_count = 0
            lines.append(f"{indent}ate_obj.clear_compare_results()")
            cmd_count += 1

        elif isinstance(ins, RST):
            lines.append(f"{indent}ate_obj.reset()")
            cmd_count += 1
    
        #########################REG#########################
        elif isinstance(ins, NO_REG):
            pass

        elif isinstance(ins, ASSIGN):
            lines.append(f"{indent}{ins.name} = {ins.value}")

        #########################CTRL#########################
        elif isinstance(ins, NO_CTRL):
            ctrl_count -= 1
            if ctrl_count < 0:
                raise CtrlError(f"{int((pc-1)/3)} line's CTRL block is not conform to the standard (4 Way).")
            
            if goto_count > 1:
                goto_count -= 1
            elif goto_count == 1:
                pc = label_dict[goto_target]
                goto_count -= 1

            if rtn_count > 1:
                rtn_count -= 1
            elif rtn_count == 1:
                rtn_count -= 1
                break  ### RTN终止当前翻译ir，结束

        elif isinstance(ins, NOP):
            indent  = '        ' 
            ctrl_count = ctrl_counter(pc, ctrl_count)

        elif isinstance(ins, RTN):
            indent  = '        ' 
            ctrl_count = ctrl_counter(pc, ctrl_count)
            rtn_count = 3   # Complete the current RTN block

        elif isinstance(ins, FOR):
            indent  = '            '
            ctrl_count = ctrl_counter(pc, ctrl_count)
            lines.append(f"        for i in range({ins.times}):")

        elif isinstance(ins, GOTO):
            indent  = '        '    
            ctrl_count = ctrl_counter(pc, ctrl_count)
            goto_target = ins.target
            times = ins.times
            if times > 0:
                if goto_target in list(label_dict.keys()):
                    goto_count = 3   # Complete the current GOTO block
                    ir_list[pc - 1] = ins.reduce_times()  # The count of current GOTO block reduce one

        else:
            lines.append(f"    # TODO unsupported IR: {ins!r}")

    if ctrl_count != 0:
        raise CtrlError(f"{int((pc-1)/3)} line's CTRL block is not conform to the standard (4 Way).")

    if cmd_count == 0:
        # 避免空函数语法错误
        lines.append("        pass")

    if compare_count != 0:
        lines.append("        return compare_result")
