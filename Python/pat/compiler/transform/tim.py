from __future__ import annotations

from lark import Transformer, v_args

from Python.pat.compiler.definitions import TimingDef


@v_args(inline=True)
class TimToIR(Transformer):
    def NAME(self, t): return t.value
    def INT(self, t): return int(t)

    def period_spec(self, period_phases):
        return ("period_phases", int(period_phases))

    def nrz_spec(self, nrz_rise_phase):
        return ("nrz_rise_phase", int(nrz_rise_phase))

    def nrz_base_spec(self, nrz_base_phase):
        return ("nrz_base_phase", int(nrz_base_phase))

    def rz_spec(self, rz_rise_phase):
        return ("rz_rise_phase", int(rz_rise_phase))

    def rz_return_spec(self, rz_return_phase):
        return ("rz_return_phase", int(rz_return_phase))

    def rz_base_spec(self, rz_base_phase):
        return ("rz_base_phase", int(rz_base_phase))

    def rzz_rise_spec(self, rzz_rise_phase):
        return ("rzz_rise_phase", int(rzz_rise_phase))

    def rzz_fall_spec(self, rzz_fall_phase):
        return ("rzz_fall_phase", int(rzz_fall_phase))

    def rzz_base_spec(self, rzz_base_phase):
        return ("rzz_base_phase", int(rzz_base_phase))

    def stb_spec(self, sample_phase):
        return ("sample_phase", int(sample_phase))

    def stb_base_spec(self, sample_base_phase):
        return ("sample_base_phase", int(sample_base_phase))

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

        return TimingDef(
            name=str(name),
            period_phases=fields["period_phases"],
            nrz_rise_phase=fields["nrz_rise_phase"],
            nrz_base_phase=fields.get("nrz_base_phase", 0),
            rz_rise_phase=fields.get("rz_rise_phase", fields["nrz_rise_phase"]),
            rz_return_phase=fields.get("rz_return_phase", fields["rzz_rise_phase"]),
            rz_base_phase=fields.get("rz_base_phase", 0),
            rzz_rise_phase=fields["rzz_rise_phase"],
            rzz_fall_phase=fields["rzz_fall_phase"],
            rzz_base_phase=fields.get("rzz_base_phase", 0),
            sample_phase=fields["sample_phase"],
            sample_base_phase=fields.get("sample_base_phase", 0),
        )

    def timing_block(self, *timings):
        return list(timings)
