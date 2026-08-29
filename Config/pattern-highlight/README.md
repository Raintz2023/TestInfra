# Pattern Highlight

VS Code language support for TestInfra `.pat` files.

## Features

- Syntax highlighting for `SOCKET`, `COMMAND`, `TIMING`, `VOLTAGE`, register,
  function, and pattern matrix files.
- Go to Definition for local labels and labels from recursive `INCLUDE` files.
- Go to Definition for user commands from the schema selected by `USE`.
- Go to Definition for row-local `TSx` selectors and pattern-level
  `VOLTAGE = VSx` selections.
- Hover documentation for `CPA`, `CPL`, `CCR`, `ALERT`, `POP`, `TSx`, and
  fixed `VSx` voltage sets.
- Diagnostics for duplicate/unresolved labels, missing INCLUDE files, duplicate
  command definitions, forbidden TIMING `OPEN`/`CLOSE` fields, and invalid
  TIMING/VOLTAGE physical literals, missing/duplicate pattern voltage
  selection, forbidden row-level VS commands, and pattern-local `REGISTER`
  blocks. Schema register definitions belong in `reg.pat`; channel `.close`
  remains Python-only.
- TIMING fields accept either absolute uppercase time literals such as `5PS`
  or unitless `PRD` ratios such as `0.05`; `PRD` itself still requires a unit.
- VOLTAGE threshold fields accept either absolute literals such as `300MV` or
  unitless set-level `VDC` ratios such as `0.25`; `VDC` itself requires a unit.

Resolution checks the current file directory first. Additional pbuild-style
search roots can be configured with:

```json
{
  "patternHighlight.includePaths": ["Python/pat/chip/pattern"],
  "patternHighlight.schemaPaths": ["Python/pat"]
}
```

The TextMate grammar retains the existing `*.pattern` scopes, so existing
`editor.tokenColorCustomizations` continue to apply.
