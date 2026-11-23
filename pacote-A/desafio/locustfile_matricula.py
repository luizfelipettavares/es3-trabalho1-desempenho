"""
DESAFIO A - Trabalho 1: abertura da matrícula 2026.2 (Locust / Python)

Cenário: às 19h a coordenação libera a matrícula e os 200 alunos entram no
portal quase juntos. Cada usuário virtual (VU) é UM aluno diferente.

Jornada do aluno e proporção (justificativa no plano, seção 1):
  consultar_oferta      peso 6  -> o aluno atualiza a oferta várias vezes para ver as vagas
  matricular            peso 3  -> tenta matricular; se a matrícula sai (201), baixa o
                                   comprovante logo em seguida (fluxo natural da tela)
  baixar_comprovante    peso 1  -> quem já se matriculou volta para baixar/conferir o comprovante
O aluno escolhe disciplinas entre as que viu com vaga na última consulta; se receber
409 "Vagas esgotadas" tenta outra combinação, e se não sobrar nada com vaga desiste.
Depois que o aluno já está matriculado (ou desistiu), a tarefa "matricular" vira uma
consulta à oferta (o aluno não reenvia a matrícula). Em regime, a mistura fica ~90% consulta /
~10% comprovante, com um surto de POSTs no início (todos querem se matricular já).

Tipos de teste (variável TIPO_TESTE):
  carga     -> 100 alunos (rampa de 5 s) mantidos até 120 s (DURACAO_S muda, p/ ensaio rápido)
  pico      -> 0 -> 200 alunos em 10 s, mantém até 70 s, cai para 20 até 100 s (recuperação)
  estresse  -> degraus de +50 alunos a cada 30 s: 50, 100, ..., 400 (240 s)
               com critério de parada: falhas técnicas > 20% ou p95 > 10 s por 10 s seguidos

Regras de verificação:
  - 201: corpo tem id, comprovante COMP-NNNNNN e as mesmas disciplinas enviadas
  - 409/422: regra de negócio CORRETA -> resp.success(), contadas à parte
  - 5xx, timeout, corpo inválido, status inesperado -> falha técnica
  - vagas nunca negativas (em toda consulta) e, ao final, vagas consumidas
    == número de matrículas 201 em cada disciplina (integridade)

Executar (Linux/macOS):
  TIPO_TESTE=carga locust -f locustfile_matricula.py --host http://localhost:5000 \
      --headless --csv ../../resultados/pacote-A/desafio/carga_r1 --html ../../resultados/pacote-A/desafio/carga_r1.html
Windows (PowerShell):
  $env:TIPO_TESTE="carga"; locust -f locustfile_matricula.py --host http://localhost:5000 --headless --csv carga_r1 --html carga_r1.html

O reset (POST /api/admin/reset) é feito automaticamente no início (RESET=0 desliga).
Ao final, gera <prefixo>_resumo.json (SLA, contadores de negócio e integridade) e
<prefixo>_requisicoes.csv (uma linha por requisição, para análise após a rampa).
"""
import csv
import itertools
import json
import os
import random
import re
import threading
import time
from collections import Counter

import requests
from locust import HttpUser, LoadTestShape, between, events, task

# ---------------------------------------------------------------- metas (SLA)
SLA_P95_GERAL_MS = 800
SLA_P95_COMPROVANTE_MS = 1500
SLA_ERRO_TECNICO_MAX = 0.01          # < 1%
NOME_COMPROVANTE = "GET /api/matriculas/[id]/comprovante"

# ---------------------------------------------------------------- massa de dados
# Oferta (horário de cada disciplina). Combinações são montadas escolhendo no
# máximo UMA disciplina por horário -> nunca há choque de horário.
HORARIOS = {
    "SEG-19h": ["ES3", "RED"],
    "TER-19h": ["BD2"],
    "QUA-19h": ["PW2"],
    "QUI-19h": ["IHC"],
    "SEX-19h": ["EMP"],
    "QUA-21h": ["MOB"],
}
TOTAL_ALUNOS = 200
_seq_aluno = itertools.count(0)
_lock = threading.Lock()

# contadores globais (thread/greenlet-safe o suficiente com o lock)
NEGOCIO = Counter()                   # ex.: "409 Vagas esgotadas", "422 Choque..."
MATRICULADAS_POR_DISCIPLINA = Counter()
VAGAS_INICIAIS = {}
VAGAS_NEGATIVAS_VISTAS = []
PARADA = {"motivo": None}

_arquivo_req = None
_escritor_req = None
_t0 = None
_env = None


def combinacao_sem_choque(vagas_vistas):
    """2 a 4 disciplinas, no máximo uma por horário, escolhidas entre as que o aluno
    viu com vaga na última consulta (desconhecidas contam como disponíveis).
    Retorna None se não sobrou nenhuma disciplina com vaga."""
    candidatos = {h: [c for c in cods if vagas_vistas.get(c, 1) > 0] for h, cods in HORARIOS.items()}
    candidatos = {h: cods for h, cods in candidatos.items() if cods}
    if not candidatos:
        return None
    k = min(random.randint(2, 4), len(candidatos))
    return [random.choice(candidatos[h]) for h in random.sample(list(candidatos), k=k)]


class Aluno(HttpUser):
    wait_time = between(1, 4)

    def on_start(self):
        # Um aluno diferente por VU: 20260001 ... 20260200. Acima de 200 VUs
        # (estresse) os números se repetem e o 2º VU recebe 409 "já possui" (regra).
        n = next(_seq_aluno) % TOTAL_ALUNOS + 1
        self.matricula = f"2026{n:04d}"
        self.id_matricula = None
        self.ja_matriculado = False
        self.vagas_vistas = {}

    # ------------------------------------------------------------ jornadas
    @task(6)
    def consultar_oferta(self):
        with self.client.get("/api/disciplinas", name="GET /api/disciplinas",
                             catch_response=True, timeout=15) as r:
            if r.status_code != 200:
                r.failure(f"HTTP {r.status_code}")
                return
            try:
                oferta = r.json()
                codigos = {d["codigo"] for d in oferta}
                negativas = [d["codigo"] for d in oferta if d["vagas"] < 0]
            except (ValueError, KeyError, TypeError):
                r.failure("corpo inválido")
                return
            self.vagas_vistas = {d["codigo"]: d["vagas"] for d in oferta}
            if len(oferta) != 7 or "ES3" not in codigos:
                r.failure(f"oferta incompleta: {sorted(codigos)}")
            elif negativas:
                VAGAS_NEGATIVAS_VISTAS.append(negativas)
                r.failure(f"VAGAS NEGATIVAS: {negativas}")

    @task(3)
    def matricular(self):
        if self.ja_matriculado:
            return self.consultar_oferta()
        escolha = combinacao_sem_choque(self.vagas_vistas)
        if escolha is None:               # nada mais com vaga: o aluno desiste e só consulta
            self.ja_matriculado = True
            with _lock:
                NEGOCIO["alunos que desistiram (sem vagas)"] += 1
            return self.consultar_oferta()
        with self.client.post("/api/matriculas", name="POST /api/matriculas",
                              json={"aluno": self.matricula, "disciplinas": escolha},
                              catch_response=True, timeout=15) as r:
            if r.status_code == 201:
                try:
                    corpo = r.json()
                    ok = (re.fullmatch(r"COMP-\d{6}", corpo["comprovante"])
                          and corpo["disciplinas"] == escolha and corpo["aluno"] == self.matricula)
                except (ValueError, KeyError, TypeError):
                    ok = False
                if not ok:
                    r.failure("201 com corpo incoerente")
                    return
                self.id_matricula = corpo["id"]
                self.ja_matriculado = True
                with _lock:
                    NEGOCIO["201 Matrícula realizada"] += 1
                    MATRICULADAS_POR_DISCIPLINA.update(escolha)
            elif r.status_code in (409, 422):
                r.success()               # regra de negócio correta, não é erro técnico
                try:
                    msg = r.json().get("erro", "")
                except ValueError:
                    msg = "?"
                with _lock:
                    NEGOCIO[f"{r.status_code} {msg.split(':')[0]}"] += 1
                if "já possui" in msg:
                    self.ja_matriculado = True    # outro VU com o mesmo número já se matriculou
                elif msg.startswith("Vagas esgotadas:"):
                    for cod in msg.split(":", 1)[1].strip(" .").split(", "):
                        self.vagas_vistas[cod] = 0   # o aluno tenta outra combinação
                return
            else:
                r.failure(f"HTTP {r.status_code}")
                return
        self.baixar_comprovante()

    @task(1)
    def baixar_comprovante(self):
        if self.id_matricula is None:
            return self.consultar_oferta()
        with self.client.get(f"/api/matriculas/{self.id_matricula}/comprovante",
                             name=NOME_COMPROVANTE, catch_response=True, timeout=15) as r:
            if r.status_code != 200:
                r.failure(f"HTTP {r.status_code}")
                return
            try:
                corpo = r.json()
                if corpo["id"] != self.id_matricula or corpo["aluno"] != self.matricula:
                    r.failure("comprovante de outro aluno")
            except (ValueError, KeyError, TypeError):
                r.failure("corpo inválido")


# ---------------------------------------------------------------- perfis de carga
class Perfil(LoadTestShape):
    tipo = os.getenv("TIPO_TESTE", "carga")
    _violacao_desde = None

    def _criterio_de_parada(self, t):
        """Estresse: para se falhas técnicas > 20% ou p95 > 10 s por 10 s seguidos."""
        st = self.runner.stats.total
        rps = st.current_rps or 0
        falhas = (st.current_fail_per_sec or 0) / rps if rps else 0
        p95 = st.get_current_response_time_percentile(0.95) or 0
        if falhas > 0.20 or p95 > 10_000:
            self._violacao_desde = self._violacao_desde or t
            if t - self._violacao_desde >= 10:
                PARADA["motivo"] = (f"critério de parada em t={t:.0f}s: falhas={falhas:.0%}, "
                                    f"p95 janela={p95:.0f} ms")
                return True
        else:
            self._violacao_desde = None
        return False

    def tick(self):
        t = self.get_run_time()
        if self.tipo == "carga":
            return (100, 20) if t < int(os.getenv("DURACAO_S", "120")) else None
        if self.tipo == "pico":
            if t < 70:
                return (200, 20)          # 0 -> 200 em 10 s
            if t < 100:
                return (20, 50)           # volta ao normal: observar recuperação
            return None
        if self.tipo == "estresse":
            if t > 15 and self._criterio_de_parada(t):
                return None
            degrau = int(t // 30) + 1
            usuarios = 50 * degrau
            return (usuarios, 50) if usuarios <= 400 else None
        raise ValueError(f"TIPO_TESTE desconhecido: {self.tipo}")


# ---------------------------------------------------------------- eventos
def _prefixo(environment):
    csv_prefix = getattr(environment.parsed_options, "csv_prefix", None)
    return csv_prefix or f"matricula_{os.getenv('TIPO_TESTE', 'carga')}"


@events.test_start.add_listener
def preparar(environment, **_):
    global _arquivo_req, _escritor_req, _t0, _env
    _env = environment
    host = environment.host or "http://localhost:5000"
    if os.getenv("RESET", "1") == "1":
        requests.post(f"{host}/api/admin/reset", timeout=10).raise_for_status()
    VAGAS_INICIAIS.update({d["codigo"]: d["vagas"]
                           for d in requests.get(f"{host}/api/disciplinas", timeout=10).json()})
    _t0 = time.time()
    _arquivo_req = open(f"{_prefixo(environment)}_requisicoes.csv", "w", newline="", encoding="utf-8")
    _escritor_req = csv.writer(_arquivo_req)
    _escritor_req.writerow(["t_s", "usuarios", "nome", "status", "tempo_ms", "falha"])


@events.request.add_listener
def registrar(request_type, name, response_time, response, exception, **_):
    if _escritor_req is None:
        return
    status = getattr(response, "status_code", 0) if response is not None else 0
    usuarios = _env.runner.user_count if _env and _env.runner else ""
    _escritor_req.writerow([f"{time.time() - _t0:.3f}", usuarios, name, status,
                            f"{response_time:.1f}", 1 if exception else 0])


@events.quitting.add_listener
def verificar(environment, **_):
    if _arquivo_req:
        _arquivo_req.close()
    stats = environment.stats
    total = stats.total
    if total.num_requests == 0:
        return
    host = environment.host or "http://localhost:5000"
    vagas_finais = {d["codigo"]: d["vagas"]
                    for d in requests.get(f"{host}/api/disciplinas", timeout=30).json()}
    integridade = {}
    for cod, ini in VAGAS_INICIAIS.items():
        consumidas = ini - vagas_finais[cod]
        integridade[cod] = {"iniciais": ini, "finais": vagas_finais[cod],
                            "consumidas": consumidas,
                            "matriculas_201": MATRICULADAS_POR_DISCIPLINA.get(cod, 0),
                            "ok": vagas_finais[cod] >= 0 and consumidas == MATRICULADAS_POR_DISCIPLINA.get(cod, 0)}
    integridade_ok = all(v["ok"] for v in integridade.values()) and not VAGAS_NEGATIVAS_VISTAS

    p95 = total.get_response_time_percentile(0.95)
    erro = total.fail_ratio
    comp = stats.entries.get((NOME_COMPROVANTE, "GET"))
    p95_comp = comp.get_response_time_percentile(0.95) if comp and comp.num_requests else None
    por_endpoint = {
        nome: {"req": e.num_requests, "falhas": e.num_failures,
               "p50_ms": e.get_response_time_percentile(0.50),
               "p95_ms": e.get_response_time_percentile(0.95),
               "max_ms": e.max_response_time, "rps": e.total_rps}
        for (nome, _m), e in stats.entries.items()}
    sla = {
        "p95_geral_ok": p95 <= SLA_P95_GERAL_MS,
        "p95_comprovante_ok": p95_comp is not None and p95_comp <= SLA_P95_COMPROVANTE_MS,
        "erro_tecnico_ok": erro < SLA_ERRO_TECNICO_MAX,
        "integridade_vagas_ok": integridade_ok,
    }
    resumo = {
        "tipo": os.getenv("TIPO_TESTE", "carga"), "requisicoes": total.num_requests,
        "falhas_tecnicas": total.num_failures, "erro_tecnico_pct": round(erro * 100, 3),
        "p50_ms": total.get_response_time_percentile(0.5), "p95_ms": p95,
        "p95_comprovante_ms": p95_comp, "rps_medio": round(total.total_rps, 2),
        "respostas_negocio": dict(NEGOCIO), "por_endpoint": por_endpoint,
        "integridade": integridade, "sla": sla, "aprovado": all(sla.values()),
        "parada": PARADA["motivo"],
    }
    with open(f"{_prefixo(environment)}_resumo.json", "w", encoding="utf-8") as f:
        json.dump(resumo, f, ensure_ascii=False, indent=2)

    print(f"\n[SLA] p95 geral = {p95:.0f} ms (meta {SLA_P95_GERAL_MS}) -> {'OK' if sla['p95_geral_ok'] else 'VIOLADO'}")
    print(f"[SLA] p95 comprovante = {p95_comp} ms (meta {SLA_P95_COMPROVANTE_MS}) -> "
          f"{'OK' if sla['p95_comprovante_ok'] else 'VIOLADO'}")
    print(f"[SLA] erros técnicos = {erro:.2%} (meta < 1%) -> {'OK' if sla['erro_tecnico_ok'] else 'VIOLADO'}")
    print(f"[NEGÓCIO] {dict(NEGOCIO)}")
    print(f"[INTEGRIDADE] vagas {'OK' if integridade_ok else 'VIOLADA'}: "
          + ", ".join(f"{c}={v['finais']}" for c, v in integridade.items()))
    if PARADA["motivo"]:
        print(f"[PARADA] {PARADA['motivo']}")
    print("[SLA] APROVADO" if resumo["aprovado"] else "[SLA] REPROVADO")
    environment.process_exit_code = 0 if resumo["aprovado"] else 1
