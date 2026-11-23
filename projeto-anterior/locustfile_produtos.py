"""PROJETO ANTERIOR - Trabalho 1: API do produtos-web (Express/Node) em localhost:3000.

Operações e proporção (justificativa no plano):
  listar        GET /api/products                 peso 5  -> abrir a página carrega o catálogo
  buscar        GET /api/products?q=<termo>       peso 3  -> busca por nome
  buscar_estoque GET /api/products?q=..&inStock=true peso 1 -> busca + filtro de estoque
  categorias    GET /api/products/categories      peso 1
Verificações de conteúdo: HTTP 200, JSON lista; listar = 6 produtos; busca devolve só nomes
que contêm o termo (sem diferenciar maiúsculas); com inStock só produtos stocked=true;
categorias == ["Frutas", "Verduras"].

Fases (uma execução cada, 3 repetições): ver ferramentas/rodar_projeto.sh
  python -m locust -f projeto-anterior/locustfile_produtos.py --host http://localhost:3000 \
     --headless -u 50 -r 10 -t 60s --csv nominal50_r1 --html nominal50_r1.html
"""
import csv
import random
import time

from locust import HttpUser, between, events, task

TERMOS = ["ma", "maçã", "pit", "er", "abóbora", "x"]          # "x" = busca sem resultado
CATALOGO = 6


def _json_ou_falha(r):
    if r.status_code != 200:
        r.failure(f"HTTP {r.status_code}")
        return None
    try:
        d = r.json()
    except ValueError:
        r.failure("JSON inválido")
        return None
    if not isinstance(d, list):
        r.failure("não é lista")
        return None
    return d


class Cliente(HttpUser):
    wait_time = between(0.5, 2)

    @task(5)
    def listar(self):
        with self.client.get("/api/products", name="listar", catch_response=True, timeout=5) as r:
            d = _json_ou_falha(r)
            if d is not None and len(d) != CATALOGO:
                r.failure(f"catálogo com {len(d)} itens")

    def _buscar(self, so_estoque):
        termo = random.choice(TERMOS)
        params = {"q": termo, **({"inStock": "true"} if so_estoque else {})}
        nome = "buscar_estoque" if so_estoque else "buscar"
        with self.client.get("/api/products", params=params, name=nome, catch_response=True, timeout=5) as r:
            d = _json_ou_falha(r)
            if d is None:
                return
            if any(termo.lower() not in p["name"].lower() for p in d):
                r.failure("item fora da busca")
            elif so_estoque and any(not p["stocked"] for p in d):
                r.failure("item em falta com inStock=true")

    @task(3)
    def buscar(self):
        self._buscar(False)

    @task(1)
    def buscar_estoque(self):
        self._buscar(True)

    @task(1)
    def categorias(self):
        with self.client.get("/api/products/categories", name="categorias", catch_response=True, timeout=5) as r:
            d = _json_ou_falha(r)
            if d is not None and d != ["Frutas", "Verduras"]:
                r.failure(f"categorias {d}")


_e = {"arq": None, "w": None, "t0": 0, "runner": None}


@events.test_start.add_listener
def _abrir(environment, **_):
    pref = getattr(environment.parsed_options, "csv_prefix", None) or "produtos"
    _e.update(arq=open(f"{pref}_requisicoes.csv", "w", newline="", encoding="utf-8"),
              t0=time.time(), runner=environment.runner)
    _e["w"] = csv.writer(_e["arq"])
    _e["w"].writerow(["t_s", "usuarios", "nome", "status", "tempo_ms", "falha"])


@events.request.add_listener
def _reg(name, response_time, response, exception, **_):
    if _e["w"]:
        _e["w"].writerow([f"{time.time() - _e['t0']:.3f}", _e["runner"].user_count if _e["runner"] else "",
                          name, getattr(response, "status_code", 0), f"{response_time:.1f}", 1 if exception else 0])


@events.quitting.add_listener
def _fechar(environment, **_):
    if _e["arq"]:
        _e["arq"].close()
