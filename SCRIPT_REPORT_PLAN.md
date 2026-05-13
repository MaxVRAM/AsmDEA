# Plan: `script_report.json` — Script-First Analysis Output

Last Updated: 2026-05-13

---

## 1. Goal

Add a new reporting layer that produces `reports/script_report.json`, providing a **script-first** view of the Unity project. Where `file_report.json` is keyed by assembly with files as a nested list, this new report inverts the relationship: every C# script in the project becomes a top-level object keyed by its Unity GUID (read from the `.cs.meta` file).

This complements the existing assembly-first reports and unlocks future dashboard views that need per-script metadata (namespace, imports, owning assembly) without re-deriving it from the asmdef dictionary.

---

## 2. Output Schema

Target file: `reports/script_report.json`

```jsonc
{
  "summary": {
    "totalScripts": 1785,
    "scriptsWithNamespace": 1700,
    "scriptsWithoutNamespace": 85,
    "scriptsWithoutMeta": 0,
    "orphanedScripts": 8,
    "totalImports": 12450,
    "uniqueNamespacesImported": 312
  },
  "scripts": {
    "GUID:abc123...": {
      "name": "DroneCommand",
      "relativePath": "OPT-CUAS/com.opt.cuas/Runtime/OPT.CUAS.Contracts/Commands/DroneCommand.cs",
      "namespace": "OPT.CUAS.Contracts.Commands",
      "importCount": 4,
      "imports": [
        "System",
        "System.Collections.Generic",
        "UnityEngine",
        "OPT.CUAS.Contracts.Ids"
      ],
      "assembly": "GUID:e630ff3f9d1bf194295a2acc815bf99d"
    }
  }
}
```

### Field specification (per script entry)

| Field          | Type           | Source                                                                                  | Notes                                                                                                         |
| -------------- | -------------- | --------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------- |
| key            | string         | `.cs.meta` `guid:` line, prefixed `"GUID:"`                                             | Matches the existing assembly-GUID convention in `dictionary.py:23-27`. Scripts without a meta file are skipped from the dict but counted in `summary.scriptsWithoutMeta`. |
| `name`         | string         | `Path.stem` of the `.cs` file                                                           | E.g. `DroneCommand.cs` -> `"DroneCommand"`.                                                                   |
| `relativePath` | string         | Path relative to `root_path`, forward-slash normalized                                  | Honours `--filepath-type` like other reporters via `common.format_path`.                                       |
| `namespace`    | string \| null | First namespace declaration in the file (reuses `NamespaceAnalyser.extract_namespace_from_file`) | `null` when no namespace declaration is present.                                                          |
| `importCount`  | int            | `len(imports)`                                                                          | Convenience field, mirrors `fileCount` pattern in `file_report.json`.                                          |
| `imports`      | string[]       | Parsed `using` directives                                                               | Deduplicated, sorted alphabetically. Excludes `using static`, `using X = ...` aliases, and `global using` are normalised (see §3.2). |
| `assembly`     | string \| null | GUID of owning assembly                                                                 | Uses the same directory-walk logic as `FileAnalyser.find_owning_assembly`. `null` for orphaned scripts.        |

### Summary fields

- `totalScripts` — every `.cs` file discovered (matches `file_report.json.summary.totalCsFiles`).
- `scriptsWithNamespace` / `scriptsWithoutNamespace` — count of entries where `namespace` is non-null vs. null.
- `scriptsWithoutMeta` — `.cs` files missing a sidecar `.cs.meta` (cannot be keyed by GUID; reported as a count only).
- `orphanedScripts` — entries where `assembly` is `null`.
- `totalImports` — sum of `importCount` across all entries.
- `uniqueNamespacesImported` — size of the union of all `imports` arrays.

---

## 3. Implementation

### 3.1 New analyser: `analysers/script_analyser.py`

New class `ScriptAnalyser`, following the constructor pattern of `FileAnalyser` and `NamespaceAnalyser` (`asmdef_dict`, `root_path`, `filter_paths`).

**Public method:**

```python
def analyse(self) -> dict[str, Any]:
    """
    Returns:
        {
            "scripts": {guid: ScriptEntry, ...},
            "stats": {...},
            "scripts_without_meta": [Path, ...],
        }
    """
```

**Internal helpers (reuse existing logic where possible):**

- `_iter_cs_files()` — copy/extract the directory walk from `FileAnalyser._iter_cs_files` (`file_analyser.py:107-129`). Both analysers will end up walking the tree; consider lifting this to `common/path_utils.py` as a shared helper in a follow-up, but **not** in this change to keep the diff minimal.
- `_build_path_to_guid_mapping()` — same body as `FileAnalyser._build_path_to_guid_mapping` to resolve owning assembly. Reuse the existing `FileAnalyser.find_owning_assembly` by composing rather than re-implementing: `ScriptAnalyser` can hold an internal `FileAnalyser` instance for this purpose.
- `_extract_namespace(path)` — delegates to `NamespaceAnalyser.extract_namespace_from_file` (already static, already comment-stripping aware).
- `_extract_imports(path)` — new helper, see §3.2.
- `_read_script_guid(cs_path)` — looks up `<cs_path>.meta` and reuses `common.dictionary.extract_guid_from_meta` (`dictionary.py:10-31`). No duplication needed.

### 3.2 Parsing `using` directives

Implement in `ScriptAnalyser._extract_imports(file_path: Path) -> list[str]`:

- Read file once; strip single-line `//` comments line-by-line (mirror the cleaner in `NamespaceAnalyser.extract_namespace_from_file` at `namespace_analyser.py:64-72`).
- Match each line against a single anchored regex:
  ```python
  USING_RE = re.compile(
      r"^\s*(?:global\s+)?using\s+(?:static\s+)?"
      r"(?:[\w@]+\s*=\s*)?"          # optional alias prefix
      r"([\w\.]+)\s*;"
  )
  ```
  - `global using ...;` → captured.
  - `using static System.Math;` → captures `System.Math`.
  - `using X = System.Collections.Generic.List<int>;` → alias target ignored intentionally (only namespace-style targets are useful here); when the target is generic / contains `<`, the regex won't match — that's the correct behaviour.
- Stop reading once the first non-`using`/non-blank/non-`namespace` line is reached (a small perf win on large files; **optional**, drop if it complicates the loop).
- Deduplicate via `sorted(set(...))` before returning.

Edge cases to document in the docstring (not necessarily handle):

- Multi-line block `/* ... */` comments containing the word `using` are not stripped. Acceptable: matching `^\s*using` makes false positives unlikely.
- `#if` conditional usings are still captured even if the preprocessor would exclude them. Acceptable for a static analysis tool.

### 3.3 New reporter: `reporting/script_reporter.py`

New class `ScriptReporter(BaseReporter)` mirroring `FileAnalysisReporter`:

- `__init__` accepts the same `verbose`, `console`, `filepath_type`, `root_path` parameters as the other reporters.
- `print_console_report(data)` — header panel + summary table:
  - Total scripts, scripts with/without namespace, orphaned scripts, unique imports.
  - Top-N most-imported namespaces table (configurable, default 10).
- `generate_json_report(data)` — emits the schema in §2 exactly. Iterate `scripts` dict in **GUID-sorted** order so JSON diffs are stable across runs.
- No `print_detailed_report` in v1 (can be added if/when the dashboard needs it).

### 3.4 Wiring into `asmdea.py`

Three edits to `asmdea.py`:

1. **Imports** (`asmdea.py:35` and `:53`): add `ScriptAnalyser`, `ScriptReporter`.
2. **New command** `cmd_map_scripts` modeled on `cmd_map_files` (`asmdea.py:468-504`):
   - Loads dict, applies filters, runs `ScriptAnalyser`, writes `reports/script_report.json`.
   - Does **not** mutate the dictionary file (unlike `cmd_map_files`).
3. **`analyze` pipeline** (`asmdea.py:660-693`): bump step count from 4 to 5 and insert "Mapping Scripts" between "Mapping C# Files to Assemblies" (step 2) and "Validating Namespace Compliance" (step 3 → 4). Script mapping depends on the asmdef dict (already built in step 1) but does **not** depend on `csFiles` being populated, so it can run in parallel slot. Sequencing it after `map-files` keeps console output ordered intuitively.
4. **Subparser**: register `map-scripts` alongside `map-files` (`asmdea.py:252-256`).
5. **Help epilog & `commands` dispatch**: add entries.

### 3.5 Module exports

- `analysers/__init__.py`: add `ScriptAnalyser` to imports and `__all__`.
- `reporting/__init__.py`: add `ScriptReporter` to imports and `__all__`.

### 3.6 No model dataclass in v1

Other analysers (cycle, namespace) have dedicated `models/*.py` dataclasses because they have rich nested state and percentage calculations. The script report is flat and the JSON shape is the canonical structure — adding a `ScriptEntry` dataclass would be ceremony without payoff. The analyser returns a plain `dict[str, Any]` like `FileAnalyser` does. Revisit if a future feature needs typed access.

---

## 4. Test Plan

Add `tests/test_script_analyser.py` covering:

- **GUID resolution**: a fixture project with a `.cs` + `.cs.meta` pair produces an entry keyed by the meta's GUID.
- **Missing meta**: `.cs` file without a `.cs.meta` is counted in `scriptsWithoutMeta` and excluded from the `scripts` dict.
- **Namespace extraction**: file-scoped (`namespace Foo;`), traditional (`namespace Foo {`), and missing-namespace cases.
- **Imports parsing**:
  - Plain `using System;` → `"System"`.
  - `global using System.Linq;` → `"System.Linq"`.
  - `using static System.Math;` → `"System.Math"`.
  - `using L = System.Collections.Generic.List<int>;` → excluded (generic alias target).
  - Duplicate `using System;` declarations → single entry.
  - `using` inside `/* block comment */` → currently captured; assert current behaviour so future change is intentional.
- **Owning assembly**: file under an `asmdef`'s folder → `assembly` is that GUID. File outside any asmdef folder → `assembly` is `null` and counted in `orphanedScripts`.
- **Filter paths**: `filter_paths=["Library/PackageCache"]` excludes scripts under that prefix.
- **Sorting stability**: two runs produce identical JSON byte output (relevant for diff-friendliness).

Add `tests/test_script_reporter.py` for the JSON shape: snapshot a small fixture and assert top-level keys + a representative entry.

---

## 5. Out of Scope (Follow-Ups)

- **Dashboard tab**: a `ScriptsTab.jsx` consuming `script_report.json` is the obvious next step but is intentionally not part of this change.
- **`script_report.json` cross-validation**: e.g. flag imports of namespaces from assemblies not declared in the asmdef `references`. That's a new analyser (potential `ImportAnalyser`), not a reporter concern.
- **Shared `_iter_cs_files` helper**: lift to `common/path_utils.py` once the second consumer (this analyser) is merged and the duplication is concrete.
- **`global using` from `.editorconfig` / SDK-style csproj**: implicit usings injected by the compiler aren't present in source and won't appear in `imports`. Acceptable for v1.

---

## 6. File Change Summary

| File                                    | Change                                                                    |
| --------------------------------------- | ------------------------------------------------------------------------- |
| `analysers/script_analyser.py`          | **New** — `ScriptAnalyser` class.                                         |
| `analysers/__init__.py`                 | Export `ScriptAnalyser`.                                                  |
| `reporting/script_reporter.py`          | **New** — `ScriptReporter(BaseReporter)`.                                 |
| `reporting/__init__.py`                 | Export `ScriptReporter`.                                                  |
| `asmdea.py`                             | New `cmd_map_scripts`, new `map-scripts` subcommand, insert into `analyze` pipeline, update help epilog. |
| `tests/test_script_analyser.py`         | **New** — coverage per §4.                                                |
| `tests/test_script_reporter.py`         | **New** — JSON shape snapshot test.                                       |
| `.env.example`                          | No new variables required.                                                |
| `CLAUDE.md`                             | Append `ScriptAnalyser` / `ScriptReporter` entries to module responsibilities sections. |

---

## 7. Acceptance Criteria

1. `python asmdea.py map-scripts --project-path <p>` writes a valid `reports/script_report.json` matching §2 exactly.
2. `python asmdea.py analyze --project-path <p>` runs 5 steps and produces `script_report.json` alongside the existing four reports.
3. `pytest` passes; new tests cover §4.
4. `mypy .` and `ruff check .` are clean.
5. Running the pipeline twice on an unchanged project produces byte-identical `script_report.json` (sorted keys, deterministic ordering).
