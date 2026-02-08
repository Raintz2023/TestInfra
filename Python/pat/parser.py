from pathlib import Path
from lark import Lark

BASE_DIR = Path(__file__).parent
GRAMMAR_DIR = BASE_DIR / "grammar"

_CMD_PARSER = Lark(
    (GRAMMAR_DIR / "cmd_grammar.lark").read_text(encoding="utf-8"),
    parser="lalr"
)

_REG_PARSER = Lark(
    (GRAMMAR_DIR / "reg_grammar.lark").read_text(encoding="utf-8"),
    parser="lalr"
)

_CTRL_PARSER = Lark(
    (GRAMMAR_DIR / "ctrl_grammar.lark").read_text(encoding="utf-8"),
    parser="lalr"
)

def parse_cmd(cmd_text: str):
    return _CMD_PARSER.parse(cmd_text)

def parse_reg(reg_text: str):
    return _REG_PARSER.parse(reg_text)

def parse_ctrl(reg_text: str):
    return _CTRL_PARSER.parse(reg_text)

if __name__ == "__main__":
    print(Path(__file__))