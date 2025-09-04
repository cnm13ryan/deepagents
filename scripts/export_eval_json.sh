#!/usr/bin/env bash

set -euo pipefail

usage() {
  cat <<EOF
Usage: $(basename "$0") [--out OUTPUT.json] [--auto-name] <log_path>

Export an Inspect eval log ('.eval' or '.json') to JSON.

Options:
  -o, --out OUTPUT.json   Custom output path. Defaults to 'scripts/eval.json'
                          (same directory as this script).
  -a, --auto-name         Name output as <input-basename>.json next to the input
                          file when --out is not provided. For non-local URIs
                          (e.g., s3://) falls back to the script directory.

Examples:
  $(basename "$0") .inspect/logs/2025-09-04T14-05-28+01-00_iterative-task_ABC.eval
  $(basename "$0") --out /tmp/eval.json file:///abs/path/to/log.eval
  $(basename "$0") -o .inspect/logs/eval.json s3://bucket/path/to/log.eval

Notes:
- Uses 'uv run inspect log dump' if available, otherwise 'inspect log dump'.
- Works regardless of on-disk format; output is always JSON.
EOF
}

OUT_JSON=""
AUTO_NAME=false

# Parse options
while [[ $# -gt 0 ]]; do
  case "${1-}" in
    -h|--help)
      usage; exit 0;;
    -o|--out)
      if [[ $# -lt 2 ]]; then
        echo "error: --out requires a path argument" >&2; echo >&2; usage >&2; exit 2
      fi
      OUT_JSON="$2"; shift 2;;
    -a|--auto-name)
      AUTO_NAME=true; shift;;
    --)
      shift; break;;
    -*)
      echo "error: unknown option: $1" >&2; echo >&2; usage >&2; exit 2;;
    *)
      break;;
  esac
done

if [[ $# -lt 1 ]]; then
  echo "error: missing <log_path> argument" >&2; echo >&2; usage >&2; exit 2
fi

LOG_PATH="$1"; shift
if [[ $# -gt 0 ]]; then
  echo "error: too many arguments; only one <log_path> is accepted" >&2; echo >&2; usage >&2; exit 2
fi

# Resolve default output file to the script directory if not provided
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
if [[ -z "$OUT_JSON" && "$AUTO_NAME" == true ]]; then
  # Derive name from the input path/URI basename
  _base="${LOG_PATH##*/}"
  # Strip common extensions
  _base="${_base%.eval}"
  _base="${_base%.json}"
  # Determine destination directory
  if [[ ! "$LOG_PATH" =~ :// ]]; then
    _dest_dir="$(cd -- "$(dirname -- "$LOG_PATH")" && pwd)"
  elif [[ "$LOG_PATH" == file://* ]]; then
    _local_path_auto="${LOG_PATH#file://}"
    _dest_dir="$(cd -- "$(dirname -- "$_local_path_auto")" && pwd)"
  else
    _dest_dir="$SCRIPT_DIR"
    echo "note: --auto-name with non-local URI; writing to ${_dest_dir}" >&2
  fi
  OUT_JSON="${_dest_dir}/${_base}.json"
fi

OUT_JSON="${OUT_JSON:-${SCRIPT_DIR}/eval.json}"

# Ensure output directory exists
mkdir -p -- "$(dirname -- "$OUT_JSON")"

# If the path looks local (no scheme) or file://, do a best-effort existence check
if [[ ! "$LOG_PATH" =~ :// ]]; then
  if [[ ! -f "$LOG_PATH" ]]; then
    echo "error: log file not found: $LOG_PATH" >&2
    exit 1
  fi
elif [[ "$LOG_PATH" == file://* ]]; then
  _local_check="${LOG_PATH#file://}"
  if [[ ! -f "$_local_check" ]]; then
    echo "error: file URI not found: $_local_check" >&2
    exit 1
  fi
fi

# Prefer 'uv run inspect', fall back to 'inspect'
if command -v uv >/dev/null 2>&1; then
  RUNNER=(uv run inspect)
elif command -v inspect >/dev/null 2>&1; then
  RUNNER=(inspect)
else
  echo "error: neither 'uv' nor 'inspect' found in PATH" >&2
  exit 1
fi

echo "Exporting log to ${OUT_JSON} ..." >&2
"${RUNNER[@]}" log dump "$LOG_PATH" >"$OUT_JSON"
echo "Done: ${OUT_JSON}" >&2
