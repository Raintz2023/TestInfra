# Pattern Highlight

VS Code syntax highlighting for the custom `.pat` language used by this repo.

The grammar recognizes the four PAT shapes currently present in the project:

- `DEFINE ... END` command definitions from `def.pat`
- `SOCKET ... END` socket definitions from `soc.pat`
- `TIMING ... END` timing definitions from `tim.pat`
- `USE/BEGIN/INCLUDE ... END` pattern matrix files

It intentionally emits the `*.pattern` TextMate scopes already referenced by
your `editor.tokenColorCustomizations`, so your existing colors apply directly.
