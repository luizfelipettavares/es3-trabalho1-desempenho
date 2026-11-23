#!/usr/bin/env bash
# Desafio B: 6 fases x 3 repetições (o estresse é seguido direto pela recuperação).
# Requer o sistema B rodando em 127.0.0.1:8000.
set -u
# Retomável: cada execução concluída deixa <prefixo>.ok e é pulada na próxima chamada.
RAIZ="$(cd "$(dirname "$0")/.." && pwd)"
OUT="$RAIZ/resultados/pacote-B/desafio"; mkdir -p "$OUT"; cd "$OUT"
LF="$RAIZ/pacote-B/desafio/desafio_locust.py"
fase () { # prefixo usuarios ritmo duracao
  [ -f "$1.ok" ] && { echo "== $1 já executado"; return; }
  echo ">> $1"; python3 -m locust -f "$LF" --host http://127.0.0.1:8000 --headless \
    -u "$2" -r "$3" -t "$4" --stop-timeout 5s --csv "$1" --html "$1.html" > "$1.log" 2>&1; touch "$1.ok"; }
for r in 1 2 3; do
  fase verificacao1_r$r 1 1 15s
  fase referencia5_r$r 5 1 90s
  fase carga20_r$r 20 2 90s
  fase estresse50_r$r 50 5 90s
  fase estresse100_r$r 100 10 90s
  fase recuperacao20_r$r 20 2 90s
done
