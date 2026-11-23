"""Teste exploratório de concorrência (Pacote A): o mesmo aluno envia N matrículas ao mesmo tempo.

Regra R6: uma matrícula por aluno no semestre -> esperado exatamente 1 resposta 201.
Hipótese: em _efetivar_matricula a checagem "aluno já possui matrícula" é feita FORA
da trava _lock_vagas, então pedidos simultâneos podem passar todos pela checagem.

Uso:  python ferramentas/teste_corrida_matricula.py [N=20] [tentativas=5]
Zera o sistema (POST /api/admin/reset) antes de cada tentativa. Só rode em localhost.
"""
import json
import sys
import threading
import urllib.error
import urllib.request

BASE = "http://localhost:5000"
N = int(sys.argv[1]) if len(sys.argv) > 1 else 20
TENTATIVAS = int(sys.argv[2]) if len(sys.argv) > 2 else 5


def post(caminho, corpo):
    req = urllib.request.Request(BASE + caminho, data=json.dumps(corpo).encode(), method="POST",
                                 headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return r.status, json.loads(r.read())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read())


def tentativa():
    post("/api/admin/reset", {})
    largada = threading.Barrier(N)
    status = []

    def aluno():
        largada.wait()                           # todos disparam juntos
        status.append(post("/api/matriculas", {"aluno": "20260001", "disciplinas": ["ES3"]})[0])

    ts = [threading.Thread(target=aluno) for _ in range(N)]
    [t.start() for t in ts]
    [t.join() for t in ts]
    with urllib.request.urlopen(BASE + "/api/disciplinas") as r:
        es3 = next(d["vagas"] for d in json.loads(r.read()) if d["codigo"] == "ES3")
    return status.count(201), status.count(409), es3


if __name__ == "__main__":
    defeito = False
    for i in range(1, TENTATIVAS + 1):
        ok, conflito, es3 = tentativa()
        print(f"tentativa {i}: 201={ok}  409={conflito}  vagas ES3 restantes={es3} (esperado 1 x 201 e 39 vagas)")
        defeito |= ok != 1
    print("DEFEITO REPRODUZIDO: mais de uma matrícula para o mesmo aluno" if defeito else "Regra R6 respeitada sob concorrência")
    post("/api/admin/reset", {})
    sys.exit(1 if defeito else 0)
