"""DESAFIO B - Trabalho 1: consulta de minicursos (Locust / Python)

Mistura exigida: 70% listagem (peso 7) e 30% detalhe (peso 3), em expectativa.
O peso define probabilidade, não uma proporção exata por execução: a proporção
obtida é conferida depois no relatório (contagem de requisições por nome).

Verificações de conteúdo (além do tempo):
  cursos          GET /api/cursos    -> HTTP 200, total == 3, len(itens) == 3, contém "Python"
  curso_detalhe   GET /api/cursos/1  -> HTTP 200, id == 1, nome == "Python", vagas == 2
HTTP 503 ("Capacidade didática ocupada") conta como falha: é exatamente a evidência
de saturação que o estresse procura.

Fases (uma execução por fase, repetir 3 vezes: prefixo <fase>_r1, _r2, _r3):
  python -m locust -f desafio/desafio_locust.py --host http://127.0.0.1:8000 --headless \
      -u 20 -r 2 -t 90s --stop-timeout 5s --csv carga20_r1 --html carga20_r1.html
O script ferramentas/rodar_pacote_B.sh executa todas as fases e repetições.

Critério de parada (PARAR_SE_VIOLAR=1, padrão): a execução é interrompida se, por
10 s seguidos, falhas > 20% ou p95 da janela > 2000 ms. O motivo vai para o log.
Também grava <prefixo>_requisicoes.csv (uma linha por requisição) para medir o
patamar depois da rampa.
"""
import csv
import os
import time

import gevent
from locust import HttpUser, between, events, task

ESPERADO_DETALHE = {"id": 1, "nome": "Python", "vagas": 2}


class Visitante(HttpUser):
    wait_time = between(0.2, 0.6)

    @task(7)
    def listar_cursos(self):
        with self.client.get("/api/cursos", name="cursos", catch_response=True, timeout=5) as r:
            if r.status_code != 200:
                r.failure(f"HTTP {r.status_code}")
                return
            try:
                d = r.json()
                nomes = {c["nome"] for c in d["itens"]}
            except (ValueError, KeyError, TypeError):
                r.failure("Resposta inválida")
                return
            if d["total"] != 3 or len(d["itens"]) != 3:
                r.failure(f"total incoerente: {d['total']}")
            elif "Python" not in nomes:
                r.failure("curso esperado ausente")

    @task(3)
    def detalhar_curso(self):
        with self.client.get("/api/cursos/1", name="curso_detalhe", catch_response=True, timeout=5) as r:
            if r.status_code != 200:
                r.failure(f"HTTP {r.status_code}")
                return
            try:
                d = r.json()
            except ValueError:
                r.failure("Resposta inválida")
                return
            divergentes = {k: d.get(k) for k, v in ESPERADO_DETALHE.items() if d.get(k) != v}
            if divergentes:
                r.failure(f"conteúdo divergente: {divergentes}")


# ---------------------------------------------------------------- registro e parada
_estado = {"arq": None, "w": None, "t0": None}


@events.test_start.add_listener
def abrir_registro(environment, **_):
    prefixo = getattr(environment.parsed_options, "csv_prefix", None) or "minicursos"
    _estado["arq"] = open(f"{prefixo}_requisicoes.csv", "w", newline="", encoding="utf-8")
    _estado["w"] = csv.writer(_estado["arq"])
    _estado["w"].writerow(["t_s", "usuarios", "nome", "status", "tempo_ms", "falha"])
    _estado["t0"] = time.time()
    _estado["runner"] = environment.runner
    if os.getenv("PARAR_SE_VIOLAR", "1") == "1" and environment.runner is not None:
        gevent.spawn(_vigiar, environment)


@events.request.add_listener
def registrar(name, response_time, response, exception, **_):
    if _estado["w"] is None:
        return
    status = getattr(response, "status_code", 0) if response is not None else 0
    env_runner = _estado.get("runner")
    _estado["w"].writerow([f"{time.time() - _estado['t0']:.3f}", env_runner.user_count if env_runner else "",
                           name, status, f"{response_time:.1f}", 1 if exception else 0])


def _vigiar(environment):
    desde = None
    while True:
        gevent.sleep(1)
        st = environment.runner.stats.total
        rps = st.current_rps or 0
        falhas = (st.current_fail_per_sec or 0) / rps if rps else 0
        p95 = st.get_current_response_time_percentile(0.95) or 0
        t = time.time() - _estado["t0"]
        if t > 5 and (falhas > 0.20 or p95 > 2000):
            desde = desde or t
            if t - desde >= 10:
                print(f"[PARADA] t={t:.0f}s falhas={falhas:.0%} p95_janela={p95:.0f} ms "
                      f"(critério: >20% ou >2000 ms por 10 s)", flush=True)
                environment.runner.quit()
                return
        else:
            desde = None


@events.quitting.add_listener
def fechar_registro(environment, **_):
    if _estado["arq"]:
        _estado["arq"].close()
