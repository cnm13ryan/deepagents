---
title: "Typed Results vs Legacy Outputs"
status: draft
owner: docs
---

# Typed Results vs Legacy Outputs

Many tools can return either compact legacy values (strings/lists) or structured typed models. The mode is controlled by the environment variable `INSPECT_AGENTS_TYPED_RESULTS`.

## Enabling Typed Results
- Set `INSPECT_AGENTS_TYPED_RESULTS=1` (truthy values: `1`, `true`, `yes`, `on`).
- Unset/falsey → legacy outputs for backward compatibility.

## File Tools — Canonical Examples

### read_file

Args
```json
{"file_path": "README.md", "offset": 0, "limit": 3}
```

Typed (INSPECT_AGENTS_TYPED_RESULTS=1)
```json
{
  "lines": [
    "     1\t# Project Title",
    "     2\t",
    "     3\tWelcome to the repo."
  ],
  "summary": "Read 3 lines from README.md (lines 1-3)"
}
```

Legacy (unset/false)
```
     1	# Project Title
     2	
     3	Welcome to the repo.
```

Notes
- Lines are cat‑style: 6‑wide line number, tab, then the (possibly truncated) line text.
- Empty file → Typed: `lines=[]` with an empty‑file summary; Legacy: a plain reminder string.
- In sandbox mode, the summary indicates “(sandbox mode)”.

### ls

Args
```json
{}
```

Typed
```json
{ "files": ["README.md", "pyproject.toml", "src/"] }
```

Legacy
```json
["README.md", "pyproject.toml", "src/"]
```

### write_file

Args
```json
{"file_path": "docs/note.md", "content": "Hello"}
```

Typed
```json
{ "path": "docs/note.md", "summary": "Updated file docs/note.md" }
```

Legacy
```
Updated file docs/note.md
```

### edit_file

Args
```json
{"file_path": "app.py", "old_string": "foo", "new_string": "bar"}
```

Typed
```json
{ "path": "app.py", "replaced": 1, "summary": "Updated file app.py" }
```

Legacy
```
Updated file app.py
```

### delete_file

Args
```json
{"file_path": "docs/old.md"}
```

Typed
```json
{ "path": "docs/old.md", "summary": "Deleted file docs/old.md" }
```

Legacy
```
Deleted file docs/old.md
```

Notes
- Delete is not supported in sandbox filesystem mode; see tool page for details.

## Guidance for Docs & Agents
- Prefer typed examples in docs for clarity; include a short callout on how to switch to legacy behavior.
- Treat summary strings as illustrative; rely on invariants (counts, ranges, backend) rather than exact phrasing.

