from __future__ import annotations

from lark import Transformer, v_args

from Python.pat.compiler.definitions import SingleEdgeTimingDef, TimingDef, TwoEdgeTimingDef


def _field_dict(name: str, fields) -> dict[str, int]:
    result: dict[str, int] = {}
    for key, value in fields:
        if key in result:
            raise RuntimeError(f"Duplicate {name} timing field {key}")
        result[key] = value
    return result


def _require(block_name: str, fields: dict[str, int], key: str) -> int:
    if key not in fields:
        raise RuntimeError(f"{block_name} timing block requires {key}")
    return fields[key]


def _single_edge_def(block_name: str, fields: dict[str, int]) -> SingleEdgeTimingDef:
    return SingleEdgeTimingDef(
        edge=_require(block_name, fields, "edge"),
        base=fields.get("base", 0),
        open=fields.get("open", 1),
    )


def _two_edge_def(block_name: str, fields: dict[str, int]) -> TwoEdgeTimingDef:
    return TwoEdgeTimingDef(
        edge_1=_require(block_name, fields, "edge_1"),
        edge_2=_require(block_name, fields, "edge_2"),
        base=fields.get("base", 0),
        open=fields.get("open", 1),
    )


def _variant_dict(name: str, variants) -> dict[str, dict[str, int]]:
    result: dict[str, dict[str, int]] = {}
    for variant_name, fields in variants:
        if variant_name in result:
            raise RuntimeError(f"Duplicate {name} timing variant @{variant_name}")
        result[variant_name] = fields
    return result


@v_args(inline=True)
class TimToIR(Transformer):
    def NAME(self, token): return token.value
    def VARIANT_NAME(self, token): return token.value[1:]
    def UINT(self, token): return int(token)
    def SINT(self, token): return int(token)

    def period_spec(self, prd):
        return ("prd", int(prd))

    def edge_spec(self, edge):
        return ("edge", int(edge))

    def edge_1_spec(self, edge):
        return ("edge_1", int(edge))

    def edge_2_spec(self, edge):
        return ("edge_2", int(edge))

    def base_spec(self, base):
        return ("base", int(base))

    def open_spec(self, open_value):
        value = int(open_value)
        if value not in (0, 1):
            raise RuntimeError("timing OPEN must be 0 or 1")
        return ("open", value)

    def single_edge_field_list(self, *fields):
        return _field_dict("single-edge", fields)

    def two_edge_field_list(self, *fields):
        return _field_dict("two-edge", fields)

    def single_edge_variant(self, variant_name, fields):
        return (str(variant_name), fields)

    def two_edge_variant(self, variant_name, fields):
        return (str(variant_name), fields)

    def nrz_variant_list(self, *variants):
        return _variant_dict("NRZ", variants)

    def stb_variant_list(self, *variants):
        return _variant_dict("STB", variants)

    def rz_variant_list(self, *variants):
        return _variant_dict("RZ", variants)

    def rzz_variant_list(self, *variants):
        return _variant_dict("RZZ", variants)

    def nrz_block(self, content):
        variants = content if _is_variant_map(content) else {"default": content}
        return ("nrz", {name: _single_edge_def(f"NRZ@{name}", fields) for name, fields in variants.items()})

    def rz_block(self, content):
        variants = content if _is_variant_map(content) else {"default": content}
        return ("rz", {name: _two_edge_def(f"RZ@{name}", fields) for name, fields in variants.items()})

    def rzz_block(self, content):
        variants = content if _is_variant_map(content) else {"default": content}
        return ("rzz", {name: _two_edge_def(f"RZZ@{name}", fields) for name, fields in variants.items()})

    def stb_block(self, content):
        variants = content if _is_variant_map(content) else {"default": content}
        return ("stb", {name: _single_edge_def(f"STB@{name}", fields) for name, fields in variants.items()})

    def timing_set(self, name, *items):
        fields: dict[str, int | dict] = {}
        for key, value in items:
            if key in fields:
                raise RuntimeError(f"Duplicate timing item {key} in {name}")
            fields[key] = value

        prd = fields.get("prd")
        nrz = fields.get("nrz")
        rz = fields.get("rz")
        rzz = fields.get("rzz")
        stb = fields.get("stb")
        if not isinstance(prd, int):
            raise RuntimeError(f"Timing {name} requires PRD")
        if not isinstance(nrz, dict):
            raise RuntimeError(f"Timing {name} requires NRZ block")
        if not isinstance(rz, dict):
            raise RuntimeError(f"Timing {name} requires RZ block")
        if not isinstance(rzz, dict):
            raise RuntimeError(f"Timing {name} requires RZZ block")
        if not isinstance(stb, dict):
            raise RuntimeError(f"Timing {name} requires STB block")

        return TimingDef(
            name=str(name),
            prd=prd,
            nrz=nrz,
            rz=rz,
            rzz=rzz,
            stb=stb,
        )

    def timing_block(self, *timings):
        return list(timings)


def _is_variant_map(content) -> bool:
    return isinstance(content, dict) and all(isinstance(value, dict) for value in content.values())
