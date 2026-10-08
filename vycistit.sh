#!/usr/bin/env bash

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
cd "$(dirname "$0")" && rm -rf roztridene klient_upload && mkdir klient_upload && echo "Vyčištěno."
