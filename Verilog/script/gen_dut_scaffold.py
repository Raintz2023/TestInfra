#!/usr/bin/env python3
from __future__ import annotations

import argparse
import re
from pathlib import Path
from typing import Literal, TypedDict


class PortInfo(TypedDict):
    direction: Literal["input", "output"]
    width: int


class PinEntry(TypedDict):
    port: str
    lsb: int
    msb: int


class PinMapConfig(TypedDict):
    dut: str
    pin_in: list[PinEntry]
    pin_out: list[PinEntry]


PORT_RE = re.compile(
    r"\b(input|output)\s+"
    r"(?:(?:wire|reg|logic)\s+)?"
    r"(?:signed\s+)?"
    r"(?:\[\s*(\d+)\s*:\s*(\d+)\s*\]\s+)?"
    r"([A-Za-z_]\w*)",
    re.MULTILINE,
)


def project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def strip_comments(text: str) -> str:
    text = re.sub(r"/\*.*?\*/", "", text, flags=re.DOTALL)
    return re.sub(r"//.*", "", text)


def parse_ports(dut_text: str, dut_module: str) -> dict[str, PortInfo]:
    text = strip_comments(dut_text)
    match = re.search(
        rf"module\s+{re.escape(dut_module)}\s*\((.*?)\)\s*;",
        text,
        re.DOTALL,
    )
    if not match:
        raise ValueError(f"cannot find ANSI-style module header for {dut_module}")

    ports: dict[str, PortInfo] = {}
    for direction, msb, lsb, name in PORT_RE.findall(match.group(1)):
        width = 1 if not msb else abs(int(msb) - int(lsb)) + 1
        ports[name] = PortInfo(direction=direction, width=width)
    if not ports:
        raise ValueError(f"no input/output ports found in {dut_module}")
    return ports


def entries_from_ports(ports: dict[str, PortInfo], direction: Literal["input", "output"]) -> list[PinEntry]:
    entries: list[PinEntry] = []
    offset = 0
    for name, info in ports.items():
        if info["direction"] != direction:
            continue
        width = info["width"]
        entries.append(PinEntry(port=name, lsb=offset, msb=offset + width - 1))
        offset += width
    return entries


def build_config_from_ports(dut: str, ports: dict[str, PortInfo]) -> PinMapConfig:
    return PinMapConfig(
        dut=dut,
        pin_in=entries_from_ports(ports, "input"),
        pin_out=entries_from_ports(ports, "output"),
    )


def pin_text(entry: PinEntry) -> str:
    if entry["lsb"] == entry["msb"]:
        return str(entry["lsb"])
    return f"[{entry['lsb']}:{entry['msb']}]"


def input_default(port: str) -> int:
    name = port.upper()
    if name in {"RST_N", "RESET_N"}:
        return 1
    return 0


def input_waveform(port: str) -> str:
    name = port.upper()
    if name in {"CLK", "CLOCK"}:
        return "RZZ"
    return "NRZ"


def emit_soc(config: PinMapConfig) -> str:
    lines = ["SOCKET {"]
    for entry in config["pin_in"]:
        lines.append(
            f"    IN  {entry['port']:<12} {{ PIN: {pin_text(entry):<8}, WAV: {input_waveform(entry['port'])}, DEF: {input_default(entry['port'])} }}"
        )
    lines.append("")
    for entry in config["pin_out"]:
        lines.append(
            f"    OUT {entry['port']:<12} {{ PIN: {pin_text(entry):<8}, WAV: STB }}"
        )
    lines.append("}")
    lines.append("")
    return "\n".join(lines)


def emit_cmd() -> str:
    return "\n".join([
        "COMMAND {",
        "    // Add DUT command definitions here.",
        "    //",
        "    // Examples:",
        "    // SET_PIN(value) {",
        "    //     DRIVE PIN_NAME = value;",
        "    // }",
        "    //",
        "    // SAMPLE_PIN(expect) {",
        "    //     SAMPLE PIN_NAME = expect;",
        "    // }",
        "}",
        "",
    ])


def emit_tim() -> str:
    return "\n".join([
        "TIMING {",
        "    // Starter timing set. Tune the phases for the DUT before real runs.",
        "    TS0 {",
        "        PRD: 10",
        "        NRZ { EDGE: 1, BASE: 0 }",
        "        RZ  { EDGE_1: 2, EDGE_2: 4, BASE: 0 }",
        "        RZZ { EDGE_1: 2, EDGE_2: 7, BASE: 0 }",
        "        STB { EDGE: 8, BASE: 0 }",
        "    }",
        "}",
        "",
    ])


def write_text(path: Path, content: str, force: bool) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and not force:
        return "kept"
    path.write_text(content, encoding="utf-8")
    return "wrote"


def schema_name(dut: str) -> str:
    name = re.sub(r"[^A-Za-z0-9_]", "_", dut).strip("_").lower()
    if not name:
        raise ValueError(f"invalid DUT name: {dut!r}")
    return name


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Generate starter Python pattern schema from RTL port order.")
    parser.add_argument("dut", help="DUT module name, e.g. Dram or Chip")
    parser.add_argument("--force", action="store_true", help="overwrite existing schema files")
    args = parser.parse_args(argv)

    root = project_root()
    dut_path = root / "Verilog" / "dut" / f"{args.dut}.v"
    if not dut_path.is_file():
        raise FileNotFoundError(f"DUT RTL not found: {dut_path}")

    ports = parse_ports(dut_path.read_text(encoding="utf-8", errors="replace"), args.dut)
    config = build_config_from_ports(args.dut, ports)

    schema_dir = root / "Python" / "pat" / schema_name(args.dut)
    statuses = {
        schema_dir / "soc.pat": write_text(schema_dir / "soc.pat", emit_soc(config), args.force),
        schema_dir / "cmd.pat": write_text(schema_dir / "cmd.pat", emit_cmd(), args.force),
        schema_dir / "tim.pat": write_text(schema_dir / "tim.pat", emit_tim(), args.force),
    }

    for path, status in statuses.items():
        print(f"[{status.upper()}] {path.relative_to(root)}")
    print(f"[INFO] USE {schema_dir.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
