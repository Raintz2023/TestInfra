from __future__ import annotations

from lark import Transformer, v_args

from Python.pat.core.schema_types import SchemaTiming


@v_args(inline=True)
class TimToIR(Transformer):
    def NAME(self, t): return t.value
    def INT(self, t): return int(t)

    def period_spec(self, period_phases):
        return ("period_phases", int(period_phases))

    def nrz_spec(self, nrz_rise_phase):
        return ("nrz_rise_phase", int(nrz_rise_phase))

    def rzz_spec(self, rzz_rise_phase, rzz_fall_phase):
        return ("rzz_rise_phase", int(rzz_rise_phase)), ("rzz_fall_phase", int(rzz_fall_phase))

    def stb_spec(self, sample_phase):
        return ("sample_phase", int(sample_phase))

    def timing_set(self, name, *phase_specs):
        fields: dict[str, int] = {}
        for phase_spec in phase_specs:
            if isinstance(phase_spec, tuple) and len(phase_spec) == 2 and isinstance(phase_spec[0], str):
                key, value = phase_spec
                if key in fields:
                    raise RuntimeError(f"Duplicate timing phase {key} in {name}")
                fields[key] = value
                continue
            for key, value in phase_spec:
                if key in fields:
                    raise RuntimeError(f"Duplicate timing phase {key} in {name}")
                fields[key] = value

        return SchemaTiming(
            name=str(name),
            period_phases=fields["period_phases"],
            nrz_rise_phase=fields["nrz_rise_phase"],
            rzz_rise_phase=fields["rzz_rise_phase"],
            rzz_fall_phase=fields["rzz_fall_phase"],
            sample_phase=fields["sample_phase"],
        )
