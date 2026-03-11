from __future__ import annotations
from pathlib import Path
from Python.pat.cls import *
from typing import Iterable

from Python.pat.ir import *
def get_label_dict(ir_list:list):    # TODO:重复的label
    key_ctrl_count = 0
    label_dict = {}
    for ins in ir_list:
        if isinstance(ins, CTRL) and not isinstance(ins, NO_CTRL):
            if ins.label != "NO_LABEL":
                label_dict[ins.label] = 12 * key_ctrl_count  # The reason for using 12 is that there are 12 valid statements in each CTRL block.
            key_ctrl_count += 1

    return label_dict

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

    return spliting_ir_list

def emit_python(testflow_list:list[Row], ir_list:list, out_path: str | Path, func_name: str = "run") -> None:
    """
    Convert testflow and ir list to python script
    Supported:
        TICK -> ate.tick()
        MRW  -> ate.mr_write()
    """
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    lines: list[str] = []
    lines.append("# Auto-generated. DO NOT EDIT.")
    lines.append("")
    lines.append("from ate import ATE")
    lines.append("")
    lines.append(f"def {func_name}(ate: ATE, TESTFLOW=1, X=0, Y=0, ADDR=0, VAL=0, TEMP=0):")

    # all_label_list and spliting_ir_list one by one
    spliting_label_list = []
    spliting_ir_list = split_ir_list(ir_list)
    for spliting_ir in spliting_ir_list:
        spliting_label_list.append(get_label_dict(spliting_ir))
    # print(all_label_list)
    # for i in range(len(all_label_list)):
    #     trans_line(lines=lines, ir_list=spliting_ir_list[i], label_dict=all_label_list[i])

    for testflow in testflow_list:
        # 第一层循环：外部传入testflow num来控制执行
        lines.append(f"    if TESTFLOW == {testflow.reg}:")
        for testflow_label in testflow.cmd2.split(','):
            # 第二层循环： 该条testflow的所有label
            for i, label in enumerate(spliting_label_list):
                # 第三层循环： 判断tf_label是否存在于spliting_label_list中，并获取label的pc以及对应的ir_list
                if testflow_label in label.keys():
                    pc_init = label[testflow_label]
                    trans_line(pc_init ,lines=lines, ir_list=spliting_ir_list[i], label_dict=label)

    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def trans_line(pc_init:int, lines:list, ir_list:list, label_dict:dict):
    pc = pc_init
    ir_list_len = len(ir_list)
    cmd_count = 0
    ctrl_count = 0
    goto_count = 0
    rtn_count = 0
    goto_target = ""

    while True:
        ins = ir_list[pc]
        pc += 1
        if pc == ir_list_len:
            break
        #########################CMD#########################
        if isinstance(ins, TICK):
            lines.append(f"{indent}ate.tick()")
            lines.append(f"{indent}ate.tick()")
            cmd_count += 1

        elif isinstance(ins, MRW):
            lines.append(f"{indent}ate.mr_write({ins.addr}, {ins.data})")
            cmd_count += 1

        elif isinstance(ins, WR):
            lines.append(f"{indent}ate.write({ins.addr})")
            cmd_count += 1

        elif isinstance(ins, RD):
            lines.append(f"{indent}ate.read({ins.addr})")
            cmd_count += 1
            
        elif isinstance(ins, DRV):
            if ins.bool_ == "T":
                lines.append(f"{indent}ate.drive({ins.shift}, True)")
            else:
                lines.append(f"{indent}ate.drive({ins.shift}, False)")
            cmd_count += 1
        
        elif isinstance(ins, SMP):
            if ins.bool_ == "T":
                lines.append(f"{indent}ate.sample({ins.shift}, True)")
            else:
                lines.append(f"{indent}ate.sample({ins.shift}, False)")
            cmd_count += 1

        elif isinstance(ins, RST):
            lines.append(f"{indent}ate.reset()")
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
                raise Exception("4 Way pattern")
            
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
            if ctrl_count != 0:
                raise Exception("4 Way pattern")
            else:
                ctrl_count += 3

        elif isinstance(ins, RTN):
            print('RTN')
            indent  = '        ' 
            if ctrl_count != 0:
                raise Exception("4 Way pattern")
            else:
                ctrl_count += 3
            rtn_count = 3   # Complete the current RTN block

        elif isinstance(ins, FOR):
            indent  = '            '
            if ctrl_count != 0:
                raise Exception("4 Way pattern")
            else:
                ctrl_count += 3
            lines.append(f"        for i in range({ins.times}):")

        elif isinstance(ins, GOTO):
            indent  = '        '    
            if ctrl_count != 0:
                raise Exception("4 Way pattern")
            else:
                ctrl_count += 3
            goto_target = ins.target
            times = ins.times
            if times > 0:
                if goto_target in list(label_dict.keys()):
                    goto_count = 3   # Complete the current GOTO block
                    ir_list[pc - 1] = ins.reduce_times()  # The count of current GOTO block reduce one

        else:
            lines.append(f"    # TODO unsupported IR: {ins!r}")

    if ctrl_count != 0:
        raise Exception("4 Way pattern")

    if cmd_count == 0:
        # 避免空函数语法错误
        lines.append("        pass")