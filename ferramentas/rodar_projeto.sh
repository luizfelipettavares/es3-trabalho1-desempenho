#!/usr/bin/env bash
# Projeto anterior (produtos-web API em localhost:3000): 6 fases x 3 repetições, 60 s cada.
set -u
# Retomável: cada execução concluída deixa <prefixo>.ok e é pulada na próxima chamada.
RAIZ="$(cd "$(dirname "$0")/.." && pwd)"
OUT="$RAIZ/resultados/projeto-anterior"; mkdir -p "$OUT"; cd "$OUT"
LF="$RAIZ/projeto-anterior/locustfile_produtos.py"
fase () { [ -f "$1.ok" ] && { echo "== $1 já executado"; return; }; echo ">> $1"; python3 -m locust -f "$LF" --host http://localhost:3000 --headless \
    -u "$2" -r "$3" -t "$4" --stop-timeout 5s --csv "$1" --html "$1.html" > "$1.log" 2>&1; touch "$1.ok"; }
for r in 1 2 3; do
  fase referencia10_r$r 10 5 60s
  fase nominal50_r$r 50 10 60s
  fase estresse100_r$r 100 20 60s
  fase estresse200_r$r 200 40 60s
  fase estresse400_r$r 400 50 60s
  fase recuperacao50_r$r 50 10 60s
done
