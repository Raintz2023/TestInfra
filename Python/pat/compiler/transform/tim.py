from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction

from lark import Transformer, v_args

from Python.pat.compiler.definitions import SingleEdgeTimingDef, TimingDef, TwoEdgeTimingDef
from Python.pat.physical import TIME, Time, parse_time_literal


@dataclass(frozen=True)
class _PeriodRatio:
    value: Fraction


@dataclass(frozen=True)
class _SingleEdgeRaw:
    edge: Time | _PeriodRatio
    base: Time | _PeriodRatio


@dataclass(frozen=True)
class _TwoEdgeRaw:
    edge_1: Time | _PeriodRatio
    edge_2: Time | _PeriodRatio
    base: Time | _PeriodRatio


_TimingValue = Time | _PeriodRatio


def _field_dict(name: str, fields) -> dict[str, _TimingValue]:
    result: dict[str, _TimingValue] = {}
    for key, value in fields:
        if key in result:
            raise RuntimeError(f"Duplicate {name} timing field {key}")
        result[key] = value
    return result


def _require(
    block_name: str,
    fields: dict[str, _TimingValue],
    key: str,
) -> _TimingValue:
    if key not in fields:
        raise RuntimeError(f"{block_name} timing block requires {key}")
    return fields[key]


def _single_edge_raw(block_name: str, fields: dict[str, _TimingValue]) -> _SingleEdgeRaw:
    return _SingleEdgeRaw(
        edge=_require(block_name, fields, "edge"),
        base=fields.get("base", TIME.PS(0)),
    )


def _two_edge_raw(block_name: str, fields: dict[str, _TimingValue]) -> _TwoEdgeRaw:
    return _TwoEdgeRaw(
        edge_1=_require(block_name, fields, "edge_1"),
        edge_2=_require(block_name, fields, "edge_2"),
        base=fields.get("base", TIME.PS(0)),
    )


def _variant_dict(name: str, variants) -> dict[str, dict[str, _TimingValue]]:
    result: dict[str, dict[str, _TimingValue]] = {}
    for variant_name, fields in variants:
        if variant_name in result:
            raise RuntimeError(f"Duplicate {name} timing variant @{variant_name}")
        result[variant_name] = fields
    return result


@v_args(inline=True)
class TimToIR(Transformer):
    def NAME(self, token): return token.value
    def VARIANT_NAME(self, token): return token.value[1:]
    def TIME_UINT(self, token): return parse_time_literal(str(token))
    def TIME_SINT(self, token): return parse_time_literal(str(token))
    def RATIO_UINT(self, token): return _PeriodRatio(Fraction(str(token)))
    def RATIO_SINT(self, token): return _PeriodRatio(Fraction(str(token)))

    def absolute_time(self, value):
        return value

    def period_ratio(self, value):
        return value

    def period_spec(self, prd):
        return ("prd", prd)

    def edge_spec(self, edge):
        return ("edge", edge)

    def edge_1_spec(self, edge):
        return ("edge_1", edge)

    def edge_2_spec(self, edge):
        return ("edge_2", edge)

    def base_spec(self, base):
        return ("base", base)

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
        return ("nrz", {name: _single_edge_raw(f"NRZ@{name}", fields) for name, fields in variants.items()})

    def rz_block(self, content):
        variants = content if _is_variant_map(content) else {"default": content}
        return ("rz", {name: _two_edge_raw(f"RZ@{name}", fields) for name, fields in variants.items()})

    def rzz_block(self, content):
        variants = content if _is_variant_map(content) else {"default": content}
        return ("rzz", {name: _two_edge_raw(f"RZZ@{name}", fields) for name, fields in variants.items()})

    def stb_block(self, content):
        variants = content if _is_variant_map(content) else {"default": content}
        return ("stb", {name: _single_edge_raw(f"STB@{name}", fields) for name, fields in variants.items()})

    def timing_set(self, name, *items):
        fields: dict[str, Time | dict] = {}
        for key, value in items:
            if key in fields:
                raise RuntimeError(f"Duplicate timing item {key} in {name}")
            fields[key] = value

        prd = fields.get("prd")
        nrz = fields.get("nrz")
        rz = fields.get("rz")
        rzz = fields.get("rzz")
        stb = fields.get("stb")
        if not isinstance(prd, Time):
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
            nrz=_resolve_single_variants(nrz, prd),
            rz=_resolve_two_variants(rz, prd),
            rzz=_resolve_two_variants(rzz, prd),
            stb=_resolve_single_variants(stb, prd),
        )

    def timing_block(self, *timings):
        return list(timings)


def _is_variant_map(content) -> bool:
    return isinstance(content, dict) and all(isinstance(value, dict) for value in content.values())


def _resolve_value(value: _TimingValue, prd: Time) -> Time:
    if isinstance(value, Time):
        return value
    scaled_ps = Fraction(prd.as_ps()) * value.value
    return TIME.PS(scaled_ps.numerator // scaled_ps.denominator)


def _resolve_single_variants(
    variants: dict[str, _SingleEdgeRaw],
    prd: Time,
) -> dict[str, SingleEdgeTimingDef]:
    return {
        name: SingleEdgeTimingDef(
            edge=_resolve_value(value.edge, prd),
            base=_resolve_value(value.base, prd),
        )
        for name, value in variants.items()
    }


def _resolve_two_variants(
    variants: dict[str, _TwoEdgeRaw],
    prd: Time,
) -> dict[str, TwoEdgeTimingDef]:
    return {
        name: TwoEdgeTimingDef(
            edge_1=_resolve_value(value.edge_1, prd),
            edge_2=_resolve_value(value.edge_2, prd),
            base=_resolve_value(value.base, prd),
        )
        for name, value in variants.items()
    }
