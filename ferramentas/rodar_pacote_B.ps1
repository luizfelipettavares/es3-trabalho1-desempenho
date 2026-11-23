# Windows PowerShell - mesmo roteiro de rodar_pacote_B.sh
$Raiz = Split-Path -Parent $PSScriptRoot
$Out = "$Raiz\resultados\pacote-B\desafio"; New-Item -ItemType Directory -Force $Out | Out-Null; Set-Location $Out
$LF = "$Raiz\pacote-B\desafio\desafio_locust.py"
function Fase($pref, $u, $r, $t) { Write-Host ">> $pref"
  python -m locust -f $LF --host http://127.0.0.1:8000 --headless -u $u -r $r -t $t --stop-timeout 5s --csv $pref --html "$pref.html" *> "$pref.log" }
foreach ($r in 1..3) {
  Fase "verificacao1_r$r" 1 1 15s;  Fase "referencia5_r$r" 5 1 90s;  Fase "carga20_r$r" 20 2 90s
  Fase "estresse50_r$r" 50 5 90s;   Fase "estresse100_r$r" 100 10 90s; Fase "recuperacao20_r$r" 20 2 90s
}
