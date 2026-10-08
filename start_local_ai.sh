#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"
mkdir -p logs
log_file="$PWD/logs/run_$(date '+%Y%m%d_%H%M%S')_$$.log"
exec > >(tee -a "$log_file") 2>&1
printf '=== Start běhu: %s ===\nLog: %s\n' "$(date '+%Y-%m-%d %H:%M:%S %z')" "$log_file"

finish_run() {
  local status=$?
  trap - EXIT
  printf '=== Konec běhu: %s (exit_code=%s) ===\n' "$(date '+%Y-%m-%d %H:%M:%S %z')" "$status"
  exit "$status"
}
trap finish_run EXIT

if [ "$(id -u)" -eq 0 ]; then
  if [ -n "${SUDO_USER:-}" ]; then
    echo "Nevolejte tento projekt přes sudo. Spusťte ho jako běžný uživatel: ./spustit.sh" >&2
    chown -R "${SUDO_USER}":"$(id -gn "${SUDO_USER}")" "$(dirname "$0")" 2>/dev/null || true
  else
    echo "Tento projekt nesmí běžet jako root. Spusťte ho jako běžný uživatel." >&2
  fi
  exit 1
fi

if ! command -v flock >/dev/null 2>&1; then
  echo "Chyba: příkaz flock není dostupný; nelze ověřit, zda aplikace už běží." >&2
  exit 1
fi

lock_id="$(printf '%s' "$PWD" | sha256sum | cut -d ' ' -f 1)"
exec 9>"/tmp/pojistne-udalosti-${lock_id}.lock"
if ! flock -n 9; then
  echo "Aplikace už pro tento projekt běží. Ukončete ji pomocí Ctrl+C před dalším spuštěním." >&2
  exit 1
fi

if ! command -v ollama >/dev/null 2>&1; then
  echo "Chyba: Ollama není nainstalovaná. Nainstalujte ji a spusťte: https://ollama.com" >&2
  exit 1
fi

if ! pgrep -x ollama >/dev/null 2>&1; then
  echo "Spouštím lokální Ollama server…"
  nohup ollama serve >/tmp/pojistne-udalosti-ollama.log 2>&1 &
  for _ in $(seq 1 30); do
    if curl -fsS http://localhost:11434/v1/models >/dev/null 2>&1; then
      break
    fi
    sleep 1
  done
fi

if ! curl -fsS http://localhost:11434/v1/models >/dev/null 2>&1; then
  echo "Ollama server se nepodařilo spustit na http://localhost:11434" >&2
  exit 1
fi

available_models="$(ollama list)"
if ! grep -Fq "llava:latest" <<< "$available_models"; then
  echo "Stahuji model llava:latest pro rozpoznání fotek…"
  ollama pull llava:latest
fi

.venv/bin/python zpracuj_dokumenty.py "$@"
