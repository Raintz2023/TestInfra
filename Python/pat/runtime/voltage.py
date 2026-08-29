from __future__ import annotations

import ate

from Python.pat.physical import VOLTAGE, Voltage
from Python.pat.runtime.model import Pin, Socket


class InputVoltage:
    def __init__(self, vil: Voltage = VOLTAGE.MV(0), vih: Voltage = VOLTAGE.MV(1200)):
        self.vil = vil
        self.vih = vih

    @property
    def vil(self) -> Voltage: return self._vil

    @vil.setter
    def vil(self, value: Voltage) -> None: self._vil = _require_voltage(value, "VIL")

    @property
    def vih(self) -> Voltage: return self._vih

    @vih.setter
    def vih(self, value: Voltage) -> None: self._vih = _require_voltage(value, "VIH")


class OutputVoltage:
    def __init__(self, vol: Voltage = VOLTAGE.MV(300), voh: Voltage = VOLTAGE.MV(900)):
        self.vol = vol
        self.voh = voh

    @property
    def vol(self) -> Voltage: return self._vol

    @vol.setter
    def vol(self, value: Voltage) -> None: self._vol = _require_voltage(value, "VOL")

    @property
    def voh(self) -> Voltage: return self._voh

    @voh.setter
    def voh(self, value: Voltage) -> None: self._voh = _require_voltage(value, "VOH")


def _require_voltage(value: Voltage, field: str) -> Voltage:
    if not isinstance(value, Voltage):
        raise TypeError(f"{field} must be Voltage, got {type(value).__name__}")
    value.as_uv()
    return value


class InputVoltageGroup:
    def __init__(self, supply: "VoltageSupply"):
        self._supply = supply

    def variant(self, name: str = "default") -> InputVoltage:
        return self._supply.input_variant(name)

    @property
    def vil(self) -> Voltage:
        return self.variant().vil

    @vil.setter
    def vil(self, value: Voltage) -> None:
        self.variant().vil = value

    @property
    def vih(self) -> Voltage:
        return self.variant().vih

    @vih.setter
    def vih(self, value: Voltage) -> None:
        self.variant().vih = value


class OutputVoltageGroup:
    def __init__(self, supply: "VoltageSupply"):
        self._supply = supply

    def variant(self, name: str = "default") -> OutputVoltage:
        return self._supply.output_variant(name)

    @property
    def vol(self) -> Voltage:
        return self.variant().vol

    @vol.setter
    def vol(self, value: Voltage) -> None:
        self.variant().vol = value

    @property
    def voh(self) -> Voltage:
        return self.variant().voh

    @voh.setter
    def voh(self, value: Voltage) -> None:
        self.variant().voh = value


class VoltageSupply:
    def __init__(self, name: str, kind: str):
        self.name = str(name)
        self.kind = str(kind).upper()
        if self.kind not in {"VIN", "VOUT"}:
            raise ValueError(f"VOLTAGE supply kind must be VIN or VOUT, got {self.kind}")
        self._variants: dict[str, InputVoltage | OutputVoltage] = {}
        self._input_group = InputVoltageGroup(self)
        self._output_group = OutputVoltageGroup(self)

    def define_input(self, variant: str, vil: Voltage, vih: Voltage) -> None:
        self._check_kind("VIN")
        self._variants[_normalize_variant_name(variant)] = InputVoltage(vil, vih)

    def define_output(self, variant: str, vol: Voltage, voh: Voltage) -> None:
        self._check_kind("VOUT")
        self._variants[_normalize_variant_name(variant)] = OutputVoltage(vol, voh)

    def variant(self, name: str = "default"):
        variant_name = _normalize_variant_name(name)
        try:
            return self._variants[variant_name]
        except KeyError as exc:
            raise RuntimeError(f"VOLTAGE {self.name}@{variant_name} is not defined") from exc

    @property
    def variant_names(self) -> tuple[str, ...]:
        return tuple(self._variants.keys())

    @property
    def default(self):
        return self.variant("default")

    def input_variant(self, name: str = "default") -> InputVoltage:
        value = self.variant(name)
        if not isinstance(value, InputVoltage):
            raise RuntimeError(f"VOLTAGE {self.name}@{_normalize_variant_name(name)} is not an input supply")
        return value

    def output_variant(self, name: str = "default") -> OutputVoltage:
        value = self.variant(name)
        if not isinstance(value, OutputVoltage):
            raise RuntimeError(f"VOLTAGE {self.name}@{_normalize_variant_name(name)} is not an output supply")
        return value

    @property
    def input(self) -> InputVoltageGroup:
        self._check_kind("VIN")
        return self._input_group

    @property
    def output(self) -> OutputVoltageGroup:
        self._check_kind("VOUT")
        return self._output_group

    def _check_kind(self, kind: str) -> None:
        if self.kind != kind:
            raise RuntimeError(f"VOLTAGE {self.name} is {self.kind}, not {kind}")


class VoltageSet:
    """One selectable voltage configuration, such as VS0 or VS1."""

    def __init__(self, name: str, vdc: Voltage | None = None, *, digital: bool = False):
        self.name = str(name)
        self.digital = bool(digital)
        if self.digital:
            if vdc is not None:
                raise RuntimeError(f"Digital VOLTAGE set {self.name} cannot define VDC")
            self._vdc: Voltage | None = None
        else:
            if vdc is None:
                raise RuntimeError(f"Analog VOLTAGE set {self.name} requires VDC")
            self._vdc = _require_voltage(vdc, "VDC")
        self._supplies: dict[str, VoltageSupply] = {}

    @property
    def vdc(self) -> Voltage:
        if self._vdc is None:
            raise RuntimeError(f"Digital VOLTAGE set {self.name} has no VDC")
        return self._vdc

    @vdc.setter
    def vdc(self, value: Voltage) -> None:
        if self.digital:
            raise RuntimeError(f"Digital VOLTAGE set {self.name} has no VDC")
        self._vdc = _require_voltage(value, "VDC")

    def add(self, supply: VoltageSupply) -> None:
        if self.digital:
            raise RuntimeError(f"Digital VOLTAGE set {self.name} cannot define supplies")
        if supply.name in self._supplies:
            raise RuntimeError(f"VOLTAGE {self.name} has duplicate supply {supply.name}")
        self._supplies[supply.name] = supply

    def supply(self, name: str) -> VoltageSupply:
        try:
            return self._supplies[name]
        except KeyError as exc:
            raise RuntimeError(f"VOLTAGE set {self.name} has no supply {name}") from exc

    @property
    def supplies(self) -> tuple[VoltageSupply, ...]:
        return tuple(self._supplies.values())

    @property
    def vin(self) -> InputVoltageGroup:
        """Return the VIN supply declared in vol.pat."""
        return self.supply("VIN").input

    @property
    def vout(self) -> OutputVoltageGroup:
        """Return the VOUT supply declared in vol.pat."""
        return self.supply("VOUT").output

    # Compatibility aliases for the singular VIN/VOUT access paths.
    @property
    def input(self) -> InputVoltageGroup:
        return self._single_kind("VIN").input

    @property
    def output(self) -> OutputVoltageGroup:
        return self._single_kind("VOUT").output

    def _single_kind(self, kind: str) -> VoltageSupply:
        matches = [supply for supply in self._supplies.values() if supply.kind == kind]
        if len(matches) != 1:
            raise RuntimeError(
                f"VOLTAGE set {self.name} requires exactly one {kind} supply for shorthand access; "
                f"use supply(name) when multiple supplies exist"
            )
        return matches[0]


def _normalize_variant_name(name: str) -> str:
    variant = str(name)
    if variant.startswith("@"):
        variant = variant[1:]
    return variant


def _validate_supply(supply: VoltageSupply) -> None:
    if "default" not in supply.variant_names:
        raise RuntimeError(f"VOLTAGE {supply.name} requires @default")
    for variant_name in supply.variant_names:
        value = supply.variant(variant_name)
        if isinstance(value, InputVoltage):
            if value.vil >= value.vih:
                raise RuntimeError(f"VOLTAGE {supply.name}@{variant_name} requires VIL < VIH")
            _check_uv(supply.name, variant_name, "VIL", value.vil)
            _check_uv(supply.name, variant_name, "VIH", value.vih)
        elif isinstance(value, OutputVoltage):
            if value.vol > value.voh:
                raise RuntimeError(f"VOLTAGE {supply.name}@{variant_name} requires VOL <= VOH")
            _check_uv(supply.name, variant_name, "VOL", value.vol)
            _check_uv(supply.name, variant_name, "VOH", value.voh)
        else:
            raise RuntimeError(f"VOLTAGE {supply.name}@{variant_name} has unsupported type")


def validate_voltages(voltages: dict[str, VoltageSet]) -> None:
    if not voltages:
        raise RuntimeError("At least one voltage set is required")
    for name, voltage_set in voltages.items():
        if voltage_set.name != name:
            raise RuntimeError(f"Voltage set key {name} does not match set name {voltage_set.name}")
        if voltage_set.digital:
            if voltage_set.supplies or voltage_set._vdc is not None:
                raise RuntimeError(f"Digital VOLTAGE set {name} cannot define supplies")
            continue
        _check_uv(name, "default", "VDC", voltage_set.vdc)
        if voltage_set.vdc <= VOLTAGE.UV(0):
            raise RuntimeError(f"VOLTAGE {name}.VDC must be greater than zero")
        for supply in voltage_set.supplies:
            for variant_name in supply.variant_names:
                value = supply.variant(variant_name)
                fields = ("vil", "vih") if isinstance(value, InputVoltage) else ("vol", "voh")
                for field in fields:
                    threshold = getattr(value, field)
                    if threshold > voltage_set.vdc:
                        raise RuntimeError(
                            f"VOLTAGE {name} {supply.name}@{variant_name}.{field.upper()} exceeds VDC"
                        )
            _validate_supply(supply)


def _check_uv(supply: str, variant: str, field: str, value: Voltage) -> None:
    uv = value.as_uv()
    if uv < 0 or uv > 0xFFFFFFFF:
        raise RuntimeError(f"VOLTAGE {supply}@{variant}.{field} must fit 0..4294967295 uV")


def clone_voltage(supply: VoltageSupply) -> VoltageSupply:
    cloned = VoltageSupply(supply.name, supply.kind)
    for variant_name in supply.variant_names:
        value = supply.variant(variant_name)
        if isinstance(value, InputVoltage):
            cloned.define_input(variant_name, value.vil, value.vih)
        elif isinstance(value, OutputVoltage):
            cloned.define_output(variant_name, value.vol, value.voh)
    return cloned


def clone_voltage_set(voltage_set: VoltageSet) -> VoltageSet:
    cloned = VoltageSet(
        voltage_set.name,
        None if voltage_set.digital else voltage_set.vdc,
        digital=voltage_set.digital,
    )
    for supply in voltage_set.supplies:
        cloned.add(clone_voltage(supply))
    return cloned


def clone_voltages(voltages: dict[str, VoltageSet]) -> dict[str, VoltageSet]:
    return {name: clone_voltage_set(voltage_set) for name, voltage_set in voltages.items()}


def apply_voltages(ate_obj: ate.ATE, socket: Socket, voltage_set: VoltageSet) -> None:
    validate_voltages({voltage_set.name: voltage_set})
    ate_obj.set_analog_mode(not voltage_set.digital)
    if voltage_set.digital:
        return
    supplies = {supply.name: supply for supply in voltage_set.supplies}
    for supply in supplies.values():
        _validate_supply(supply)
    for power in socket.powers:
        if power.supply != "VDC":
            raise RuntimeError(f"POWER {power.name} must use the set-level VDC supply")
        if power.name != "VDDQ":
            raise RuntimeError(f"Unsupported POWER rail {power.name}; currently only VDDQ is wired")
        ate_obj.set_dut_vddq_uv(voltage_set.vdc.as_uv())

    for pin in socket.pins:
        if not pin.supply:
            continue
        supply = _supply(supplies, pin.supply)
        value = _variant_or_default(supply, pin.voltage_variant)
        if pin.input:
            if supply.kind != "VIN" or not isinstance(value, InputVoltage):
                raise RuntimeError(f"input pin {pin.name} uses non-input VOLTAGE {pin.supply}")
            config = ate.AteInputVoltageConfig()
            config.vil_uv = value.vil.as_uv()
            config.vih_uv = value.vih.as_uv()
            ate_obj.configure_ate_input_voltage_field(pin.lsb, pin.width, config)
        else:
            if supply.kind != "VOUT" or not isinstance(value, OutputVoltage):
                raise RuntimeError(f"output pin {pin.name} uses non-output VOLTAGE {pin.supply}")
            config = ate.AteOutputVoltageConfig()
            config.enabled = True
            config.vol_uv = value.vol.as_uv()
            config.voh_uv = value.voh.as_uv()
            ate_obj.configure_ate_output_voltage_field(pin.lsb, pin.width, config)


def _supply(voltages: dict[str, VoltageSupply], name: str) -> VoltageSupply:
    try:
        return voltages[name]
    except KeyError as exc:
        raise RuntimeError(f"Unknown VOLTAGE supply {name}") from exc


def _variant_or_default(supply: VoltageSupply, variant_name: str):
    if variant_name in supply.variant_names:
        return supply.variant(variant_name)
    return supply.default
