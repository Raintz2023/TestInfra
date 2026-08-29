const vscode = require("vscode");
const path = require("path");

const SYSTEM_COMMANDS = new Map([
  ["CPA", "Flush all scheduled events and compare every accumulated sample record."],
  ["CPL", "Flush all scheduled events and compare only the latest sample group."],
  ["CCR", "Clear all accumulated compare results."],
  ["ALERT", "Emit a waveform debug marker in the current vector row without ending the row."],
  ["POP", "Advance the enabled DEQUE data source by one element. Requires FUNCTION { DEQUE }."],
]);

const LABEL_DEFINITION = /^\s*([A-Z][A-Z0-9_]*)\s*#/;
const GOTO_REFERENCE = /\bGOTO-(?:\d+|[A-Z][A-Z0-9_]*)\s+([A-Z][A-Z0-9_]*)\b/g;
const INCLUDE_DIRECTIVE = /^\s*INCLUDE\s+([^\s/][^\s]*|\.?\.?\/[^\s]+)\s*$/;
const USE_DIRECTIVE = /^\s*USE\s+([^\s]+)\s*$/;
const COMMAND_DEFINITION = /^\s*([A-Z][A-Z0-9_]*)\s*\([^)]*\)\s*\{/;
const VOLTAGE_SELECTION = /^\s*VOLTAGE\s*=\s*(VS[A-Z0-9_]*)\s*$/;

function activate(context) {
  const diagnostics = vscode.languages.createDiagnosticCollection("pattern");
  const diagnosticTimers = new Map();
  context.subscriptions.push(diagnostics);

  context.subscriptions.push(
    vscode.languages.registerDefinitionProvider("pattern", {
      provideDefinition: provideDefinition,
    }),
    vscode.languages.registerHoverProvider("pattern", {
      provideHover: provideHover,
    }),
    vscode.workspace.onDidOpenTextDocument((document) => refreshDiagnostics(document, diagnostics)),
    vscode.workspace.onDidSaveTextDocument((document) => refreshDiagnostics(document, diagnostics)),
    vscode.workspace.onDidChangeTextDocument((event) => {
      scheduleDiagnostics(event.document, diagnostics, diagnosticTimers);
    }),
    vscode.workspace.onDidDeleteFiles((event) => {
      for (const uri of event.files) diagnostics.delete(uri);
    }),
  );

  for (const document of vscode.workspace.textDocuments) {
    refreshDiagnostics(document, diagnostics);
  }
}

function deactivate() {}

async function provideDefinition(document, position) {
  const wordRange = document.getWordRangeAtPosition(position, /[A-Za-z_][A-Za-z0-9_]*/);
  if (!wordRange) return undefined;
  const word = document.getText(wordRange);
  const line = stripComment(document.lineAt(position.line).text);

  if (isGotoTarget(line, word)) {
    return findLabelLocations(document, word);
  }

  if (/^TS[A-Z0-9_]*$/.test(word)) {
    return findSchemaDefinition(document, "tim.pat", word);
  }
  if (/^VS[A-Z0-9_]*$/.test(word)) {
    return findSchemaDefinition(document, "vol.pat", word);
  }
  if (SYSTEM_COMMANDS.has(word)) return undefined;

  const commandLocations = await findCommandDefinitions(document, word);
  if (commandLocations.length) return commandLocations;

  return findLabelLocations(document, word);
}

async function provideHover(document, position) {
  const wordRange = document.getWordRangeAtPosition(position, /[A-Za-z_][A-Za-z0-9_]*/);
  if (!wordRange) return undefined;
  const word = document.getText(wordRange);

  if (SYSTEM_COMMANDS.has(word)) {
    const body = new vscode.MarkdownString();
    body.appendCodeblock(word, "pattern");
    body.appendMarkdown(SYSTEM_COMMANDS.get(word));
    return new vscode.Hover(body, wordRange);
  }

  if (/^TS[A-Z0-9_]*$/.test(word)) {
    return systemSelectorHover(
      word,
      "Timing selector",
      "Selects this timing set for the current vector row. The next row defaults to TS0 unless another TS is selected.",
      wordRange,
    );
  }
  if (/^VS[A-Z0-9_]*$/.test(word)) {
    return systemSelectorHover(
      word,
      "Pattern voltage set",
      "The pattern header selects one fixed voltage set with `VOLTAGE = VSx`. Row-level voltage switching is not supported.",
      wordRange,
    );
  }

  const definitions = await findCommandDefinitions(document, word);
  if (definitions.length) {
    return new vscode.Hover(
      new vscode.MarkdownString(`**User command** \`${word}\`\n\nUse Go to Definition to open its COMMAND declaration.`),
      wordRange,
    );
  }
  return undefined;
}

function systemSelectorHover(word, title, description, range) {
  const body = new vscode.MarkdownString();
  body.appendMarkdown(`**${title}** \`${word}\`\n\n${description}\n\nThis system command supports Go to Definition.`);
  return new vscode.Hover(body, range);
}

async function refreshDiagnostics(document, collection) {
  if (document.languageId !== "pattern" || document.uri.scheme !== "file") return;
  const documentVersion = document.version;
  const results = [];
  const labelLines = new Map();
  const commandLines = new Map();
  const voltageSelections = [];
  let hasBegin = false;
  const isRegisterFile = document.uri.fsPath.endsWith(`${path.sep}reg.pat`);

  for (let lineNumber = 0; lineNumber < document.lineCount; lineNumber += 1) {
    const text = stripComment(document.lineAt(lineNumber).text);
    if (!isRegisterFile && /^\s*REGISTER\s*\{/.test(text)) {
      results.push(diagnosticForWord(
        document,
        lineNumber,
        "REGISTER",
        "REGISTER is schema-level; move this block to the USE schema's reg.pat.",
      ));
    }
    if (/^\s*BEGIN\s*$/.test(text)) hasBegin = true;
    const voltageSelection = text.match(VOLTAGE_SELECTION);
    if (voltageSelection) voltageSelections.push({ lineNumber, name: voltageSelection[1] });
    const label = text.match(LABEL_DEFINITION);
    if (label) {
      addDuplicateDiagnostic(results, labelLines, label[1], document, lineNumber, "label");
    }
    const command = text.match(COMMAND_DEFINITION);
    if (command) {
      addDuplicateDiagnostic(results, commandLines, command[1], document, lineNumber, "command");
    }

    const include = text.match(INCLUDE_DIRECTIVE);
    if (include && !(await resolveInclude(document.uri, include[1]))) {
      results.push(diagnosticForWord(document, lineNumber, include[1], `INCLUDE file not found: ${include[1]}`));
    }

    if (/\bOPEN\s*:/.test(text)) {
      results.push(diagnosticForWord(document, lineNumber, "OPEN", "OPEN was removed; timing channels are enabled or disabled through the Python session .close property."));
    }
    if (/\bCLOSE\s*:/.test(text)) {
      results.push(diagnosticForWord(document, lineNumber, "CLOSE", "CLOSE is runtime-only; remove it from tim.pat and set the timing variant's .close property in Python."));
    }
    for (const timingValue of text.matchAll(/\b(PRD|EDGE|EDGE_1|EDGE_2|BASE)\s*:\s*([^\s,}]+)/g)) {
      const field = timingValue[1];
      const value = timingValue[2];
      const absoluteTime = /^-?[0-9]+(?:\.[0-9]+)?(?:PS|NS|US|MS|S)$/.test(value);
      const periodRatio = field !== "PRD" && /^-?[0-9]+(?:\.[0-9]+)?$/.test(value);
      if (!absoluteTime && !periodRatio) {
        results.push(diagnosticForWord(
          document,
          lineNumber,
          value,
          field === "PRD"
            ? "PRD requires an adjacent uppercase time unit: PS, NS, US, MS, or S."
            : "Timing values require a time unit or a unitless PRD ratio.",
        ));
      }
    }
    for (const voltageValue of text.matchAll(/\b(VIL|VIH|VOL|VOH|VDC)\s*:\s*([^\s,}]+)/g)) {
      const field = voltageValue[1];
      const value = voltageValue[2];
      const absolute = /^-?[0-9]+(?:\.[0-9]+)?(?:UV|MV|V)$/.test(value);
      const ratio = /^-?[0-9]+(?:\.[0-9]+)?$/.test(value);
      if ((field === "VDC" && !absolute) || (field !== "VDC" && !absolute && !ratio)) {
        const message = field === "VDC"
          ? "VDC requires an adjacent uppercase unit: UV, MV, or V."
          : "Voltage thresholds require an absolute UV/MV/V value or a unitless VDC ratio.";
        results.push(diagnosticForWord(document, lineNumber, value, message));
      }
    }
    if (text.includes("|") && /\bVS[A-Z0-9_]*\b/.test(text)) {
      const name = text.match(/\bVS[A-Z0-9_]*\b/)[0];
      results.push(diagnosticForWord(
        document,
        lineNumber,
        name,
        `Row-level VOLTAGE command ${name} is not supported; declare VOLTAGE = ${name} before BEGIN.`,
      ));
    }
  }

  if (hasBegin && voltageSelections.length === 0) {
    results.push(new vscode.Diagnostic(
      new vscode.Range(0, 0, 0, 0),
      "Pattern must declare VOLTAGE = VSx before BEGIN.",
      vscode.DiagnosticSeverity.Error,
    ));
  }
  for (const duplicate of voltageSelections.slice(1)) {
    results.push(diagnosticForWord(
      document,
      duplicate.lineNumber,
      duplicate.name,
      "A pattern can select only one voltage set.",
    ));
  }

  const allLabels = await collectIncludedLabelNames(document);
  const commandNames = await collectCommandNames(document);
  for (let lineNumber = 0; lineNumber < document.lineCount; lineNumber += 1) {
    const text = stripComment(document.lineAt(lineNumber).text);
    for (const match of text.matchAll(GOTO_REFERENCE)) {
      const target = match[1];
      if (!allLabels.has(target)) {
        results.push(diagnosticForWord(document, lineNumber, target, `Unknown label: ${target}`));
      }
    }
    for (const match of text.matchAll(/\b([A-Z][A-Z0-9_]*)\s*</g)) {
      const command = match[1];
      if (!commandNames.has(command) && !SYSTEM_COMMANDS.has(command)) {
        results.push(diagnosticForWord(document, lineNumber, command, `Unknown user command: ${command}`));
      }
    }
  }
  if (document.version !== documentVersion) return;
  collection.set(document.uri, results);
}

function scheduleDiagnostics(document, collection, timers) {
  if (document.languageId !== "pattern") return;
  const key = document.uri.toString();
  const previous = timers.get(key);
  if (previous) clearTimeout(previous);
  timers.set(key, setTimeout(() => {
    timers.delete(key);
    refreshDiagnostics(document, collection);
  }, 250));
}

function addDuplicateDiagnostic(results, map, name, document, lineNumber, kind) {
  if (map.has(name)) {
    results.push(diagnosticForWord(document, lineNumber, name, `Duplicate ${kind}: ${name}`));
  } else {
    map.set(name, lineNumber);
  }
}

function diagnosticForWord(document, lineNumber, word, message) {
  const line = document.lineAt(lineNumber).text;
  const start = Math.max(0, line.indexOf(word));
  const range = new vscode.Range(lineNumber, start, lineNumber, start + word.length);
  return new vscode.Diagnostic(range, message, vscode.DiagnosticSeverity.Error);
}

function stripComment(line) {
  return line.split("//", 1)[0];
}

function isGotoTarget(line, word) {
  return new RegExp(`\\bGOTO-(?:\\d+|[A-Z][A-Z0-9_]*)\\s+${escapeRegex(word)}\\b`).test(line);
}

async function findLabelLocations(document, label) {
  const local = findDefinitionsInText(document, new RegExp(`^\\s*(${escapeRegex(label)})\\s*#`));
  if (local.length) return local;

  const locations = [];
  const visited = new Set([document.uri.toString()]);
  await visitIncludes(document, visited, async (included) => {
    locations.push(...findDefinitionsInText(included, new RegExp(`^\\s*(${escapeRegex(label)})\\s*#`)));
  });
  return locations;
}

async function collectIncludedLabelNames(document) {
  const labels = new Set();
  collectLabels(document, labels);
  const visited = new Set([document.uri.toString()]);
  await visitIncludes(document, visited, async (included) => collectLabels(included, labels));
  return labels;
}

function collectLabels(document, output) {
  for (let lineNumber = 0; lineNumber < document.lineCount; lineNumber += 1) {
    const match = stripComment(document.lineAt(lineNumber).text).match(LABEL_DEFINITION);
    if (match) output.add(match[1]);
  }
}

async function visitIncludes(document, visited, visitor) {
  for (let lineNumber = 0; lineNumber < document.lineCount; lineNumber += 1) {
    const match = stripComment(document.lineAt(lineNumber).text).trim().match(INCLUDE_DIRECTIVE);
    if (!match) continue;
    const uri = await resolveInclude(document.uri, match[1]);
    if (!uri || visited.has(uri.toString())) continue;
    visited.add(uri.toString());
    const included = await vscode.workspace.openTextDocument(uri);
    await visitor(included);
    await visitIncludes(included, visited, visitor);
  }
}

async function resolveInclude(sourceUri, target) {
  const normalized = target.endsWith(".pat") ? target : `${target}.pat`;
  const direct = vscode.Uri.joinPath(sourceUri, "..", ...normalized.split("/"));
  if (await isFile(direct)) return direct;

  for (const root of configuredRoots("patternHighlight.includePaths", sourceUri)) {
    const candidate = vscode.Uri.joinPath(root, ...normalized.split("/"));
    if (await isFile(candidate)) return candidate;
  }

  const basename = normalized.split("/").pop();
  const matches = await vscode.workspace.findFiles(`**/${basename}`, "**/{.git,C++,build,node_modules}/**", 50);
  return matches.find((uri) => uri.path.endsWith(normalized)) || matches[0];
}

async function findCommandDefinitions(document, commandName) {
  const files = await schemaFiles(document, "cmd.pat");
  const regex = new RegExp(`^\\s*(${escapeRegex(commandName)})\\s*\\([^)]*\\)\\s*\\{`);
  return findDefinitionsInFiles(files, regex);
}

async function collectCommandNames(document) {
  const names = new Set();
  const files = await schemaFiles(document, "cmd.pat");
  for (const uri of files) {
    const commandDocument = await vscode.workspace.openTextDocument(uri);
    for (let lineNumber = 0; lineNumber < commandDocument.lineCount; lineNumber += 1) {
      const match = stripComment(commandDocument.lineAt(lineNumber).text).match(COMMAND_DEFINITION);
      if (match) names.add(match[1]);
    }
  }
  return names;
}

async function findSchemaDefinition(document, fileName, name) {
  const files = await schemaFiles(document, fileName);
  const regex = new RegExp(`^\\s*(${escapeRegex(name)})\\s*\\{`);
  return findDefinitionsInFiles(files, regex);
}

async function schemaFiles(document, fileName) {
  const results = [];
  const seen = new Set();
  const add = async (uri) => {
    if (!uri || seen.has(uri.toString()) || !(await isFile(uri))) return;
    seen.add(uri.toString());
    results.push(uri);
  };

  await add(vscode.Uri.joinPath(document.uri, "..", fileName));
  const useTargets = [];
  for (let lineNumber = 0; lineNumber < document.lineCount; lineNumber += 1) {
    const match = stripComment(document.lineAt(lineNumber).text).trim().match(USE_DIRECTIVE);
    if (match) useTargets.push(match[1]);
  }

  for (const target of useTargets) {
    await add(vscode.Uri.joinPath(document.uri, "..", target, fileName));
    for (const root of configuredRoots("patternHighlight.schemaPaths", document.uri)) {
      await add(vscode.Uri.joinPath(root, target, fileName));
    }
    const candidates = await vscode.workspace.findFiles(
      `**/${target}/${fileName}`,
      "**/{.git,C++,build,node_modules}/**",
      20,
    );
    for (const candidate of candidates) await add(candidate);
  }

  if (!results.length) {
    const candidates = await vscode.workspace.findFiles(
      `**/${fileName}`,
      "**/{.git,C++,build,node_modules}/**",
      50,
    );
    for (const candidate of candidates) await add(candidate);
  }
  return results;
}

function configuredRoots(setting, sourceUri) {
  const key = setting.replace(/^patternHighlight\./, "");
  const values = vscode.workspace.getConfiguration("patternHighlight", sourceUri).get(key, []);
  const folder = vscode.workspace.getWorkspaceFolder(sourceUri);
  return values.map((value) => {
    if (/^\//.test(value)) return vscode.Uri.file(value);
    return folder ? vscode.Uri.joinPath(folder.uri, ...value.split("/")) : vscode.Uri.file(value);
  });
}

async function findDefinitionsInFiles(files, regex) {
  const locations = [];
  for (const uri of files) {
    const document = await vscode.workspace.openTextDocument(uri);
    locations.push(...findDefinitionsInText(document, regex));
  }
  return locations;
}

function findDefinitionsInText(document, regex) {
  const locations = [];
  for (let lineNumber = 0; lineNumber < document.lineCount; lineNumber += 1) {
    const text = stripComment(document.lineAt(lineNumber).text);
    const match = text.match(regex);
    if (!match) continue;
    const start = text.indexOf(match[1]);
    locations.push(new vscode.Location(document.uri, new vscode.Position(lineNumber, start)));
  }
  return locations;
}

async function isFile(uri) {
  try {
    const stat = await vscode.workspace.fs.stat(uri);
    return (stat.type & vscode.FileType.File) !== 0;
  } catch (_error) {
    return false;
  }
}

function escapeRegex(value) {
  return value.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

module.exports = { activate, deactivate };
