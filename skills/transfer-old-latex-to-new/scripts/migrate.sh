#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
用法：
  migrate.sh --old <旧项目> --new <新项目> [--runs-root <runs目录>] [--run-id <run_id>] [--no-ai] [--skip-compile]
            [--strategy smart|conservative|aggressive|fallback] [--allow-low] [--optimize] [--adapt-word-count]

说明：
  - 这是一个“一键迁移”包装脚本：analyze → apply → (可选) compile
  - 默认 runs 输出在 skill 的 runs/；如需隔离输出（例如测试），使用 --runs-root 指定目录
EOF
}

OLD=""
NEW=""
RUNS_ROOT=""
RUN_ID=""
STRATEGY=""
NO_AI=0
SKIP_COMPILE=0
ALLOW_LOW=0
OPTIMIZE=0
ADAPT_WORD_COUNT=0

while [[ $# -gt 0 ]]; do
  case "$1" in
    --old) OLD="${2:-}"; shift 2;;
    --new) NEW="${2:-}"; shift 2;;
    --runs-root) RUNS_ROOT="${2:-}"; shift 2;;
    --run-id) RUN_ID="${2:-}"; shift 2;;
    --strategy) STRATEGY="${2:-}"; shift 2;;
    --no-ai) NO_AI=1; shift 1;;
    --skip-compile) SKIP_COMPILE=1; shift 1;;
    --allow-low) ALLOW_LOW=1; shift 1;;
    --optimize) OPTIMIZE=1; shift 1;;
    --adapt-word-count) ADAPT_WORD_COUNT=1; shift 1;;
    -h|--help) usage; exit 0;;
    *)
      echo "未知参数：$1" >&2
      usage
      exit 2
      ;;
  esac
done

if [[ -z "${OLD}" || -z "${NEW}" ]]; then
  usage
  exit 2
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RUN_PY="${SCRIPT_DIR}/run.py"

ANALYZE_ARGS=(analyze --old "${OLD}" --new "${NEW}")
APPLY_ARGS=(apply --old "${OLD}" --new "${NEW}")
COMPILE_ARGS=(compile --new "${NEW}")

if [[ -n "${RUNS_ROOT}" ]]; then
  ANALYZE_ARGS+=(--runs-root "${RUNS_ROOT}")
  APPLY_ARGS+=(--runs-root "${RUNS_ROOT}")
  COMPILE_ARGS+=(--runs-root "${RUNS_ROOT}")
fi

if [[ -n "${RUN_ID}" ]]; then
  ANALYZE_ARGS+=(--run-id "${RUN_ID}")
fi

if [[ -n "${STRATEGY}" ]]; then
  ANALYZE_ARGS+=(--strategy "${STRATEGY}")
fi

if [[ "${NO_AI}" -eq 1 ]]; then
  ANALYZE_ARGS+=(--no-ai)
  APPLY_ARGS+=(--no-ai)
fi

if [[ "${ALLOW_LOW}" -eq 1 ]]; then
  APPLY_ARGS+=(--allow-low)
fi
if [[ "${OPTIMIZE}" -eq 1 ]]; then
  APPLY_ARGS+=(--optimize)
fi
if [[ "${ADAPT_WORD_COUNT}" -eq 1 ]]; then
  APPLY_ARGS+=(--adapt-word-count)
fi

echo "==> analyze"
ANALYZE_OUT="$(python "${RUN_PY}" "${ANALYZE_ARGS[@]}")"
echo "${ANALYZE_OUT}"
RID="$(echo "${ANALYZE_OUT}" | awk -F= '/^run_id=/{print $2}' | tail -n 1)"
if [[ -z "${RID}" ]]; then
  echo "未能解析 run_id（analyze 输出异常）" >&2
  exit 2
fi

echo "==> apply (run_id=${RID})"
python "${RUN_PY}" "${APPLY_ARGS[@]}" --run-id "${RID}"

if [[ "${SKIP_COMPILE}" -eq 0 ]]; then
  echo "==> compile (run_id=${RID})"
  python "${RUN_PY}" "${COMPILE_ARGS[@]}" --run-id "${RID}" || true
fi

echo "✅ 完成：run_id=${RID}"
