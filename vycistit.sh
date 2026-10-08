#!/usr/bin/env bash
set -euo pipefail

if [ "$(id -u)" -eq 0 ]; then
	if [ -n "${SUDO_USER:-}" ]; then
		echo "Nevolejte ./vycistit.sh přes sudo. Spusťte ho jako běžný uživatel." >&2
		chown -R "${SUDO_USER}":"$(id -gn "${SUDO_USER}")" "$(dirname "$0")" 2>/dev/null || true
	else
		echo "Tento projekt nesmí běžet jako root. Spusťte ho jako běžný uživatel." >&2
	fi
	exit 1
fi

# Vrátí demo do výchozího stavu: smaže roztříděné soubory a souhrn, vyprázdní klient_upload/.
cd "$(dirname "$0")"
if ! command -v flock >/dev/null 2>&1; then
	echo "Chyba: příkaz flock není dostupný; nelze ověřit, zda aplikace už běží." >&2
	exit 1
fi
lock_id="$(printf '%s' "$PWD" | sha256sum | cut -d ' ' -f 1)"
exec 9>"/tmp/pojistne-udalosti-${lock_id}.lock"
if ! flock -n 9; then
	echo "Aplikace právě běží. Před čištěním ji ukončete pomocí Ctrl+C, jinak může dojít ke ztrátě výsledků." >&2
	exit 1
fi
rm -rf roztridene klient_upload
mkdir klient_upload
echo "Vyčištěno."
