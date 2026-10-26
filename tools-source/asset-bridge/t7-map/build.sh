#!/usr/bin/env bash
# Kino overlay build: compose -> IW7 xmodel/xsurface/images -> fastfile.
# Usage: build.sh <name> [kino_compose.py args...]
# Outputs $KINO_RUNTIME/kino-build-<name> and $KINO_RUNTIME/kino-ff-work-<name>/zone/kino.ff.
set -euo pipefail
K="$(cd "$(dirname "$0")" && pwd)"
R="${KINO_RUNTIME:-$HOME/Documents/IW7-Runtime}"
EXPORT="${KINO_EXPORT:-$R/kino-bo3-export-b}"
ZONE="${BO3_ZONE:?set BO3_ZONE to the BO3 zone directory}"
TEMPLATE="${KINO_TEMPLATE:-$R/kino-template-unlit}"
PREPARED="${KINO_PREPARED:?set KINO_PREPARED to prepared iw7-paris-server source inputs (resource scheduler)}"
name=$1; shift
B="$R/kino-build-$name"; W="$R/kino-ff-work-$name"
rm -rf "$B" "$W"
cd "$K"
python kino_compose.py --export "$EXPORT" --zone-dir "$ZONE" --template "$TEMPLATE" --out "$B" "$@" | tail -3
if [ -n "${KINO_VISION_TEMPLATE:-}" ]; then python make_visions.py "$KINO_VISION_TEMPLATE" "$B"; fi
"${KINO_WRITER:-$K/kino-writer.exe}" "$B/kmsh" "$B/assets" | tail -2
"${KINO_WRITER:-$K/kino-writer.exe}" --images "$B/images" "$B/assets"
powershell -NoProfile -ExecutionPolicy Bypass -File "$K/Build-KinoFF.ps1" -BuildRoot "$B" -Work "$W" -PreparedSource "$PREPARED" -StockRoot "${IW7_ROOT:?set IW7_ROOT}" -ZoneTool "${KINO_ZONETOOL:?set KINO_ZONETOOL}" -TlsDll "${KINO_TLSDLL:?set KINO_TLSDLL}" -Sentinel "${KINO_SENTINEL:?set KINO_SENTINEL}"
grep -E "FATAL|ERROR|Successfully" "$W/build.stdout.log" | tail -3
