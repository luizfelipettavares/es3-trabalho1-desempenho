#!/usr/bin/env bash
# Desafio A: carga x3, pico x3, estresse x1. Requer o sistema A rodando em localhost:5000.
# Uso: bash ferramentas/rodar_pacote_A.sh   (a partir da raiz do trabalho1-desempenho)
set -u
# Retomável: cada execução concluída deixa <prefixo>.ok e é pulada na próxima chamada.
RAIZ="$(cd "$(dirname "$0")/.." && pwd)"
OUT="$RAIZ/resultados/pacote-A/desafio"; mkdir -p "$OUT"; cd "$OUT"
LF="$RAIZ/pacote-A/desafio/locustfile_matricula.py"
rodar () { # tipo prefixo
  [ -f "$2.ok" ] && { echo "== $2 já executado"; return; }
  echo ">> $1 ($2)"; TIPO_TESTE=$1 python3 -m locust -f "$LF" --host http://localhost:5000 \
    --headless --csv "$2" --html "$2.html" > "$2.log" 2>&1; touch "$2.ok"; sleep 5; }
for r in 1 2 3; do rodar carga carga_r$r; done
for r in 1 2 3; do rodar pico pico_r$r; done
rodar estresse estresse_r1
