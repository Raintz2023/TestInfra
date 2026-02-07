from pathlib import Path
from lark import Lark

GRAMMAR_PATH = Path(__file__).with_name("cmd_grammar.lark")
_PARSER = Lark(GRAMMAR_PATH.read_text(encoding="utf-8"), parser="lalr")

def parse_cmd(cmd_text: str):
    return _PARSER.parse(cmd_text)

