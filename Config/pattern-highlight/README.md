# Pattern Highlight

VS Code syntax highlighting for the custom `.pat` language used by this repo.

The grammar recognizes the PAT shapes currently present in the project:

- `COMMAND { ... }` command definitions from `cmd.pat`
- `SOCKET { ... }` socket definitions from `soc.pat`
- `TIMING { ... }` timing definitions from `tim.pat`
- `USE/BEGIN/INCLUDE ... END` pattern matrix files

Legacy `DEFINE ... END`, `SOCKET ... END`, and `TIMING ... END` blocks are
still accepted by the compiler for older files.

It intentionally emits the `*.pattern` TextMate scopes already referenced by
your `editor.tokenColorCustomizations`, so your existing colors apply directly.
