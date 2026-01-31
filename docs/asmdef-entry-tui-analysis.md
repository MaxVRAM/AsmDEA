# AsmdefEntry Model Analysis for TUI Implementation

**Created:** January 31, 2026  
**Purpose:** Reference document for TUI infrastructure development

---

## Executive Summary

The `AsmdefEntry` dataclass in `models/asmdef_entry.py` is a well-designed but **currently unused** model that represents Unity Assembly Definition files. While not integrated into the core analyser pipeline, it is **recommended for adoption in the TUI layer** where typed access to assembly properties will improve code quality and maintainability.

---

## Current Usage Status

| Location | Usage Type |
|----------|------------|
| `models/asmdef_entry.py` | Definition |
| `models/__init__.py` | Re-exported in `__all__` |
| `tests/unit/test_models.py` | Unit tests only |

**Key Finding:** `AsmdefEntry` is not used in any production code path. The analysers, reporters, and CLI all work with raw `dict[str, Any]` representations of assembly data.

---

## Data Flow Analysis

### Current Architecture (Raw Dictionaries)

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────┐
│ .asmdef files   │────▶│ dictionary.py    │────▶│ asmdef_dict │
│ (JSON on disk)  │     │ build_asmdef_    │     │ dict[GUID,  │
│                 │     │ dictionary()     │     │ dict[str,   │
└─────────────────┘     └──────────────────┘     │ Any]]       │
                                                 └──────┬──────┘
                                                        │
                        ┌───────────────────────────────┼───────────────────────────────┐
                        │                               │                               │
                        ▼                               ▼                               ▼
               ┌────────────────┐             ┌─────────────────┐             ┌─────────────────┐
               │ CycleAnalyser  │             │ NamespaceAnalyser│            │ FileAnalyser    │
               │ (raw dict)     │             │ (raw dict)       │            │ (raw dict)      │
               └────────────────┘             └─────────────────┘             └─────────────────┘
```

### Why AsmdefEntry Was Created

The class provides:

- **Strong typing** for 15+ fields from `.asmdef` JSON schema
- **Pythonic naming conventions** (e.g., `root_namespace` vs `rootNamespace`)
- **Default values** for optional Unity fields
- **Bidirectional serialization** via `from_dict()` and `to_dict()`

It appears to be **planned infrastructure** that was never integrated, likely due to the overhead of maintaining two parallel representations.

---

## TUI Feasibility Assessment

### Proposed TUI Views and Data Models

| TUI View | Primary Data Model | AsmdefEntry Relevance |
|----------|-------------------|----------------------|
| CycleView | `CycleReport` | ❌ Low—works with GUID/name strings |
| NamespaceView | `NamespaceAnalysisReport` | ⚠️ Partial—could enrich file listings |
| FileView | Raw dict with `csFiles` | ✅ High—typed access beneficial |
| EnforcementView | `SortingResult` | ✅ High—sorted references need context |

### Benefits for TUI Development

1. **Type Safety in Widgets**
   - `DataTable` columns map cleanly to typed dataclass fields
   - IDE autocompletion improves development velocity
   - Compile-time checks catch field name typos

2. **Encapsulation of Unity Conventions**
   - Unity uses camelCase (`rootNamespace`, `allowUnsafeCode`)
   - Python convention is snake_case (`root_namespace`, `allow_unsafe_code`)
   - `AsmdefEntry` handles this translation consistently

3. **Clean Widget Binding**

   ```python
   # Example: Populating a DataTable from typed entries
   for entry in entries:
       table.add_row(
           entry.name,
           entry.root_namespace or "(none)",
           str(len(entry.references)),
       )
   ```

---

## Recommendations

### ✅ Adopt AsmdefEntry in the TUI Layer

Convert dictionary entries to `AsmdefEntry` instances at view construction time:

```python
# tui/views/file_view.py (conceptual)
from models import AsmdefEntry

def build_entries(asmdef_dict: dict) -> list[AsmdefEntry]:
    """Convert raw dictionary to typed entries for display."""
    return [
        AsmdefEntry.from_dict(guid, data, Path(data.get("relativePath", "")))
        for guid, data in asmdef_dict.items()
        if not guid.startswith("_")
    ]
```

### 🚫 Do Not Retrofit Core Analysers

Refactoring `CycleAnalyser`, `NamespaceAnalyser`, and `FileAnalyser` to use `AsmdefEntry` would:

- Break the existing CLI layer
- Require updating all test fixtures
- Add conversion overhead with minimal benefit (analysers access only 2-3 fields each)

The analysers are stable and well-tested—leave them as-is.

### ⚠️ Address Missing Field: `csFiles`

The `FileAnalyser` populates a `csFiles` array on each assembly entry, but `AsmdefEntry` lacks this field. Options:

1. **Extend AsmdefEntry** with an optional `cs_files: list[Path] = field(default_factory=list)` field
2. **Create a wrapper** like `AsmdefWithFiles` for file-view-specific use
3. **Access csFiles separately** from the raw dict when needed

Recommendation: Option 1 is cleanest if the field is added with a default value (backward compatible).

### 💡 Potential Enhancement: Batch Factory Method

Add a convenience method for bulk conversion:

```python
@classmethod
def from_asmdef_dict(cls, asmdef_dict: dict) -> dict[str, "AsmdefEntry"]:
    """Convert full dictionary to typed entries, skipping metadata keys."""
    return {
        guid: cls.from_dict(guid, data, Path(data.get("relativePath", "")))
        for guid, data in asmdef_dict.items()
        if not guid.startswith("_")
    }
```

---

## Implementation Checklist for TUI

When starting TUI development, consider these steps:

- [ ] Decide whether to extend `AsmdefEntry` with `cs_files` field
- [ ] Create `tui/utils/converters.py` with dict-to-entry conversion helpers
- [ ] Use `AsmdefEntry` in FileView and EnforcementView widgets
- [ ] Keep CycleView working with `CycleReport` directly (no conversion needed)
- [ ] Add type hints using `AsmdefEntry` in view class signatures

---

## Summary Table

| Aspect | Current State | TUI Recommendation |
|--------|---------------|-------------------|
| `AsmdefEntry` usage | Tests only | Adopt in TUI views |
| Analyser integration | Raw dicts | Keep as-is |
| Dictionary builder | Returns raw dicts | No change needed |
| Model completeness | Missing `csFiles` | Extend with optional field |
| Conversion location | N/A | TUI view layer |

---

## Related Files

- Model definition: `models/asmdef_entry.py`
- Model tests: `tests/unit/test_models.py`
- Dictionary builder: `common/dictionary.py`
- TUI plan: `CLAUDE.md` (TUI Implementation Plan section)
