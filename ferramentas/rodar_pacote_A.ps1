# Windows PowerShell - mesmo roteiro de rodar_pacote_A.sh
$Raiz = Split-Path -Parent $PSScriptRoot
$Out = "$Raiz\resultados\pacote-A\desafio"; New-Item -ItemType Directory -Force $Out | Out-Null; Set-Location $Out
$LF = "$Raiz\pacote-A\desafio\locustfile_matricula.py"
function Rodar($tipo, $pref) { Write-Host ">> $tipo ($pref)"; $env:TIPO_TESTE = $tipo
  python -m locust -f $LF --host http://localhost:5000 --headless --csv $pref --html "$pref.html" *> "$pref.log"; Start-Sleep 5 }
1..3 | ForEach-Object { Rodar carga "carga_r$_" }
1..3 | ForEach-Object { Rodar pico "pico_r$_" }
Rodar estresse estresse_r1
