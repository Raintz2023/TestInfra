#!/usr/bin/env python3
import re
import sys
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

ANALOG_INFRA_PORTS = {
    "ANALOG_ENABLE",
    "VDDQ_UV",
    "ATE_CLK",
    "ATE_PIN_IN_UV",
    "DUT_INPUT_ENABLE",
    "DUT_INPUT_RISE_STEP_UV",
    "DUT_INPUT_FALL_STEP_UV",
    "DUT_RX_DQS_SKEW",
    "DUT_RX_DQ_SKEW",
    "DUT_TX_DQS_SKEW",
    "DUT_TX_DQ_SKEW",
    "DUT_OUTPUT_ENABLE",
    "DUT_LOW_UV",
    "DUT_HIGH_UV",
    "DUT_RISE_STEP_UV",
    "DUT_FALL_STEP_UV",
    "PIN_IN_UV",
    "PIN_OUT_UV",
}


def is_analog_infra_port(name: str) -> bool:
    # Any *_UV port is a direct analog/power infrastructure signal. It is
    # visible on the DUT boundary for voltage binding, but it must not consume
    # digital IN/OUT pin numbers.
    lower = name.lower()
    return name in ANALOG_INFRA_PORTS or lower.endswith("_uv") or lower.endswith("uv")


def project_root() -> Path:
    # Locate the repository root from this script's fixed path:
    #   <root>/Verilog/script/gen_pin_adapter.py
    return Path(__file__).resolve().parents[2]


def strip_comments(text: str) -> str:
    text = re.sub(r"/\*.*?\*/", "", text, flags=re.DOTALL)
    return re.sub(r"//.*", "", text)


def parse_ports(dut_text: str, dut_module: str) -> dict[str, PortInfo]:
    # Parse an ANSI-style Verilog module header and extract each port's
    # direction and width. This generator intentionally reads only the DUT
    # interface and never tries to infer behavior from the module body.
    text = strip_comments(dut_text)
    match = re.search(
        rf"module\s+{re.escape(dut_module)}\s*(?:#\s*\(.*?\)\s*)?\((.*?)\)\s*;",
        text,
        re.DOTALL,
    )
    if not match:
        raise ValueError(f"cannot find ANSI-style module header for {dut_module}")

    ports: dict[str, PortInfo] = {}
    for direction, msb, lsb, name in PORT_RE.findall(match.group(1)):
        if is_analog_infra_port(name):
            continue
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


def get_port_width(ports: dict[str, PortInfo], port_name: str) -> int:
    # Small helper for type checkers and readability.
    return ports[port_name]["width"]


def get_port_direction(ports: dict[str, PortInfo], port_name: str) -> Literal["input", "output"]:
    # Small helper for type checkers and readability.
    return ports[port_name]["direction"]


def entry_width(entry: PinEntry) -> int:
    # Convert [lsb, msb] mapping metadata into a bus width.
    return entry["msb"] - entry["lsb"] + 1


def calc_bus_width(entries: list[PinEntry]) -> int:
    # The external IN/OUT bus width is derived from the highest mapped bit.
    # This keeps PIN_IN_NUM / PIN_OUT_NUM in Socket.v synced with the selected DUT.
    if not entries:
        raise ValueError("pin mapping must not be empty")
    return max(entry["msb"] for entry in entries) + 1


def check_mapping(config: PinMapConfig, ports: dict[str, PortInfo]) -> None:
    # Sanity-check the pin mapping against the DUT interface before generating any
    # files. We verify:
    # - the mapped port exists
    # - input/output direction matches
    # - mapped bit width matches the DUT port width
    for entries, direction in ((config["pin_in"], "input"), (config["pin_out"], "output")):
        for entry in entries:
            port = entry["port"]
            if port not in ports:
                raise ValueError(f"port {port} not found in DUT")
            if get_port_direction(ports, port) != direction:
                raise ValueError(
                    f"port {port} direction mismatch: expected {direction}, got {get_port_direction(ports, port)}"
                )
            if get_port_width(ports, port) != entry_width(entry):
                raise ValueError(
                    f"port {port} width mismatch: expected {get_port_width(ports, port)}, got {entry_width(entry)}"
                )


def width_decl(width: int) -> str:
    # Render Verilog packed range text for a port/wire declaration.
    return "" if width == 1 else f"[{width - 1}:0] "


def pin_slice(entry: PinEntry) -> str:
    # Render a single-bit or multi-bit slice used on PIN_IN / PIN_OUT.
    if entry["lsb"] == entry["msb"]:
        return f"[{entry['lsb']}]"
    return f"[{entry['msb']}:{entry['lsb']}]"


def wire_decl(width: int, name: str) -> str:
    # Emit an internal wire declaration inside the generated DUT wrapper.
    if width == 1:
        return f"    wire       {name};"
    return f"    wire [{width - 1}:0] {name};"


def emit_pin_in_adapter(config: PinMapConfig, ports: dict[str, PortInfo], pin_in_width: int) -> str:
    # Generate PinInAdapter.v:
    # flatten the tester-side PIN_IN bus into DUT-friendly named signals.
    lines = [
        "module PinInAdapter(",
        f"    input  wire [{pin_in_width - 1}:0] PIN_IN,",
    ]
    entries = config["pin_in"]
    for idx, entry in enumerate(entries):
        width = get_port_width(ports, entry["port"])
        comma = "," if idx != len(entries) - 1 else ""
        lines.append(f"    output wire {width_decl(width)}{entry['port']}{comma}")
    lines.append(");")
    for entry in entries:
        lines.append(f"    assign {entry['port']:<12} = PIN_IN{pin_slice(entry)};")
    lines.append("")
    lines.append("endmodule")
    lines.append("")
    return "\n".join(lines)


def emit_pin_out_adapter(config: PinMapConfig, ports: dict[str, PortInfo], pin_out_width: int) -> str:
    # Generate PinOutAdapter.v:
    # collect DUT named outputs back into the tester-side PIN_OUT bus.
    lines = ["module PinOutAdapter("]
    entries = config["pin_out"]
    for entry in entries:
        width = get_port_width(ports, entry["port"])
        lines.append(f"    input  wire {width_decl(width)}{entry['port']},")
    lines.append(f"    output wire [{pin_out_width - 1}:0] PIN_OUT")
    lines.append(");")
    for entry in entries:
        lines.append(f"    assign PIN_OUT{pin_slice(entry):<8} = {entry['port']};")
    lines.append("")
    lines.append("endmodule")
    lines.append("")
    return "\n".join(lines)


def detect_analog_infra_ports(dut_text: str, dut_module: str) -> set[str]:
    text = strip_comments(dut_text)
    match = re.search(
        rf"module\s+{re.escape(dut_module)}\s*(?:#\s*\(.*?\)\s*)?\((.*?)\)\s*;",
        text,
        re.DOTALL,
    )
    if not match:
        return set()
    header = match.group(1)
    parsed_uv_ports = {
        name
        for _direction, _msb, _lsb, name in PORT_RE.findall(header)
        if is_analog_infra_port(name)
    }
    known_ports = {name for name in ANALOG_INFRA_PORTS if re.search(rf"\b{name}\b", header)}
    return parsed_uv_ports | known_ports


def emit_wrapper(config: PinMapConfig,
                 ports: dict[str, PortInfo],
                 pin_in_width: int,
                 pin_out_width: int,
                 analog_infra_ports: set[str],
                 instance_module: str | None = None) -> str:
    # Generate Verilog/ate/DUT.v.
    # This is the only DUT wrapper used by the ATE flow. ATE-side voltage
    # generation and comparison live in Socket.v; DUT-side analog behavior is
    # owned by the selected DUT when it exposes the analog infrastructure ports.
    in_entries = config["pin_in"]
    out_entries = config["pin_out"]
    dut_module = instance_module or config["dut"]

    lines = [
        "module DUT #(",
        "    parameter VOLTAGE_W = 32",
        ")(",
        "    /* verilator lint_off UNUSEDSIGNAL */",
        "    input  wire ATE_CLK,",
        "    input  wire ATE_RST_N,",
        "    input  wire DUT_ANALOG_ENABLE,",
        "    /* verilator lint_on UNUSEDSIGNAL */",
        f"    input  wire [{pin_in_width - 1}:0] IN,",
        f"    input  wire [{pin_in_width - 1}:0] DUT_INPUT_ENABLE,",
        f"    input  wire [{pin_in_width}*VOLTAGE_W-1:0] ATE_PIN_IN_UV,",
        f"    input  wire [{pin_in_width}*VOLTAGE_W-1:0] DUT_INPUT_RISE_STEP_UV,",
        f"    input  wire [{pin_in_width}*VOLTAGE_W-1:0] DUT_INPUT_FALL_STEP_UV,",
        "    input  wire [3:0] DUT_RX_DQS_SKEW,",
        "    input  wire [3:0] DUT_RX_DQ_SKEW,",
        "    input  wire [3:0] DUT_TX_DQS_SKEW,",
        "    input  wire [3:0] DUT_TX_DQ_SKEW,",
        f"    input  wire [{pin_out_width - 1}:0] DUT_OUTPUT_ENABLE,",
        f"    input  wire [{pin_out_width}*VOLTAGE_W-1:0] DUT_LOW_UV,",
        f"    input  wire [{pin_out_width}*VOLTAGE_W-1:0] DUT_HIGH_UV,",
        f"    input  wire [{pin_out_width}*VOLTAGE_W-1:0] DUT_RISE_STEP_UV,",
        f"    input  wire [{pin_out_width}*VOLTAGE_W-1:0] DUT_FALL_STEP_UV,",
        "    input  wire [VOLTAGE_W-1:0] DUT_VDDQ_UV,",
        f"    output wire [{pin_out_width - 1}:0] OUT,",
        f"    output wire [{pin_in_width}*VOLTAGE_W-1:0] PIN_IN_UV,",
        f"    output wire [{pin_out_width}*VOLTAGE_W-1:0] PIN_OUT_UV",
        ");",
        f"    wire [{pin_out_width - 1}:0] dut_output;",
    ]

    for entry in in_entries:
        lines.append(wire_decl(get_port_width(ports, entry["port"]), entry["port"]))
    lines.append("")
    for entry in out_entries:
        lines.append(wire_decl(get_port_width(ports, entry["port"]), entry["port"]))
    lines.append("")

    lines.append("    PinInAdapter u_pin_in_adapter (")
    lines.append("        .PIN_IN      (IN),")
    for idx, entry in enumerate(in_entries):
        comma = "," if idx != len(in_entries) - 1 else ""
        lines.append(f"        .{entry['port']:<12}({entry['port']}){comma}")
    lines.append("    );")
    lines.append("")

    lines.append("    " + dut_module + " u_dut (")
    entries_by_port = {entry["port"]: entry for entry in in_entries + out_entries}
    # Keep the real DUT instance readable by following the RTL module header
    # order. In the normal DUT-name flow, adapter order is derived from that
    # same header, so RTL is the single source of pin numbering.
    ordered_ports = [entries_by_port[name] for name in ports if name in entries_by_port]
    connection_lines: list[str] = []
    for entry in ordered_ports:
        connection_lines.append(f"        .{entry['port']:<12}({entry['port']})")
    infra_connections = {
        "VDDQ_UV": "DUT_VDDQ_UV",
        "ANALOG_ENABLE": "DUT_ANALOG_ENABLE",
        "ATE_CLK": "ATE_CLK",
        "ATE_PIN_IN_UV": "ATE_PIN_IN_UV",
        "DUT_INPUT_ENABLE": "DUT_INPUT_ENABLE",
        "DUT_INPUT_RISE_STEP_UV": "DUT_INPUT_RISE_STEP_UV",
        "DUT_INPUT_FALL_STEP_UV": "DUT_INPUT_FALL_STEP_UV",
        "DUT_RX_DQS_SKEW": "DUT_RX_DQS_SKEW",
        "DUT_RX_DQ_SKEW": "DUT_RX_DQ_SKEW",
        "DUT_TX_DQS_SKEW": "DUT_TX_DQS_SKEW",
        "DUT_TX_DQ_SKEW": "DUT_TX_DQ_SKEW",
        "DUT_OUTPUT_ENABLE": "DUT_OUTPUT_ENABLE",
        "DUT_LOW_UV": "DUT_LOW_UV",
        "DUT_HIGH_UV": "DUT_HIGH_UV",
        "DUT_RISE_STEP_UV": "DUT_RISE_STEP_UV",
        "DUT_FALL_STEP_UV": "DUT_FALL_STEP_UV",
        "PIN_IN_UV": "PIN_IN_UV",
        "PIN_OUT_UV": "PIN_OUT_UV",
    }
    for port, signal in infra_connections.items():
        if port in analog_infra_ports:
            connection_lines.append(f"        .{port:<12}({signal})")
    for idx, line in enumerate(connection_lines):
        comma = "," if idx != len(connection_lines) - 1 else ""
        lines.append(line + comma)
    lines.append("    );")
    lines.append("")

    lines.append("    PinOutAdapter u_pin_out_adapter (")
    for entry in out_entries:
        lines.append(f"        .{entry['port']:<12}({entry['port']}),")
    lines.append("        .PIN_OUT     (dut_output)")
    lines.append("    );")
    lines.append("")
    if "PIN_IN_UV" not in analog_infra_ports:
        lines.append(f"    assign PIN_IN_UV = ATE_PIN_IN_UV;")
    if "PIN_OUT_UV" not in analog_infra_ports:
        lines.append(f"    assign PIN_OUT_UV = {{{pin_out_width}*VOLTAGE_W{{1'b0}}}};")
    lines.append("    assign OUT = dut_output;")
    lines.append("")
    lines.append("endmodule")
    lines.append("")
    return "\n".join(lines)


def update_socket(socket_path: Path, pin_in_width: int, pin_out_width: int) -> None:
    # Keep Socket.v parameters aligned with the generated adapter widths so the
    # pin infrastructure does not need manual edits after switching DUTs.
    text = socket_path.read_text()
    text, in_count = re.subn(
        r"(parameter\s+PIN_IN_NUM\s*=\s*)\d+",
        rf"\g<1>{pin_in_width}",
        text,
        count=1,
    )
    text, out_count = re.subn(
        r"(parameter\s+PIN_OUT_NUM\s*=\s*)\d+",
        rf"\g<1>{pin_out_width}",
        text,
        count=1,
    )
    if in_count != 1 or out_count != 1:
        raise ValueError(f"failed to update PIN_IN_NUM/PIN_OUT_NUM in {socket_path}")
    socket_path.write_text(text)


def offset_width(depth: int) -> int:
    if depth <= 1:
        return 1
    return (depth - 1).bit_length()


def emit_ate_socket_config(source_label: str,
                           pin_in_width: int,
                           pin_out_width: int,
                           depth: int = 32) -> str:
    return "\n".join([
        "#pragma once",
        "",
        f"// Generated from {source_label}. Do not edit by hand.",
        "",
        "struct AteSocketConfig {",
        f"    static constexpr int kOffsetWidth = {offset_width(depth)};",
        f"    static constexpr int kPinInCount = {pin_in_width};",
        f"    static constexpr int kPinOutCount = {pin_out_width};",
        "};",
        "",
    ])


def main() -> int:
    # Entry point:
    # 1. parse DUT interface
    # 2. build pin mapping from RTL port order
    # 3. validate mapping
    # 4. generate wrapper/adapters
    # 5. update Socket.v pin widths
    if len(sys.argv) != 2:
        print("usage: gen_pin_adapter.py <dut-name>", file=sys.stderr)
        return 1

    root = project_root()
    dut_name = sys.argv[1]
    source_label = f"Verilog/dut/{dut_name}.v"
    dut_file = root / "Verilog" / "dut" / f"{dut_name}.v"
    if not dut_file.is_file():
        print(f"dut file not found: {dut_file}", file=sys.stderr)
        return 1

    dut_text = dut_file.read_text()
    ports = parse_ports(dut_text, dut_name)
    wrapper_name = f"{dut_name}AnalogWrapper"
    wrapper_file = root / "Verilog" / "dut" / f"{wrapper_name}.v"
    instance_module = dut_name
    analog_text = dut_text
    analog_module = dut_name
    if wrapper_file.is_file():
        instance_module = wrapper_name
        analog_text = wrapper_file.read_text()
        analog_module = wrapper_name
    analog_infra_ports = detect_analog_infra_ports(analog_text, analog_module)
    config = build_config_from_ports(dut_name, ports)
    check_mapping(config, ports)

    pin_in_width = calc_bus_width(config["pin_in"])
    pin_out_width = calc_bus_width(config["pin_out"])

    outputs = {
        root / "Verilog" / "ate" / "DUT.v": emit_wrapper(
            config,
            ports,
            pin_in_width,
            pin_out_width,
            analog_infra_ports,
            instance_module,
        ),
        root / "Verilog" / "pin" / "PinInAdapter.v": emit_pin_in_adapter(config, ports, pin_in_width),
        root / "Verilog" / "pin" / "PinOutAdapter.v": emit_pin_out_adapter(config, ports, pin_out_width),
        root / "C++" / "generated" / "AteSocketConfig.h": emit_ate_socket_config(source_label, pin_in_width, pin_out_width),
    }

    header = "// Generated by Verilog/pin/gen_pin_adapter.py. Do not edit by hand.\n\n"
    for out_path, content in outputs.items():
        out_path.write_text(header + content)

    update_socket(root / "Verilog" / "ate" / "Socket.v", pin_in_width, pin_out_width)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
