"""Analisa os resultados brutos do Trabalho 1 e gera tabelas e gráficos.

Uso (da raiz do trabalho1-desempenho):
    python ferramentas/analisar.py

Lê   resultados/<pacote>/<...>/<prefixo>_stats.csv        (agregado do Locust)
     resultados/<pacote>/<...>/<prefixo>_requisicoes.csv  (1 linha por requisição, gravada pelos locustfiles)
     resultados/pacote-A/desafio/<prefixo>_resumo.json    (SLA, negócio, integridade)
Gera resultados/registro_resultados.csv  (formato do Modelo_Registro_Resultados_Desempenho.csv + colunas extras)
     resultados/resumo_analise.json      (números usados no relatório)
     resultados/graficos/*.png

Medido x interpretado: este script só calcula; a interpretação está no relatório.
"""
import csv
import datetime as dt
import json
import pathlib
import statistics

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

RAIZ = pathlib.Path(__file__).resolve().parent.parent
RES = RAIZ / "resultados"
GRAF = RES / "graficos"
GRAF.mkdir(parents=True, exist_ok=True)

# paleta de referência (skill dataviz), 3 primeiros slots + neutros
AZUL, LARANJA, AQUA = "#2a78d6", "#eb6834", "#1baf7a"
TEXTO, TEXTO2, GRADE, META = "#0b0b0b", "#52514e", "#e6e5e0", "#8a8983"
plt.rcParams.update({
    "font.size": 10, "axes.edgecolor": GRADE, "axes.labelcolor": TEXTO2, "xtick.color": TEXTO2,
    "ytick.color": TEXTO2, "axes.grid": True, "grid.color": GRADE, "grid.linewidth": 0.8,
    "axes.spines.top": False, "axes.axisbelow": True, "axes.spines.right": False, "lines.linewidth": 2, "legend.frameon": False,
    "figure.dpi": 130, "savefig.bbox": "tight",
})
DATA = dt.date.today().isoformat()


# ------------------------------------------------------------------ leitura
def ler_stats(prefixo):
    arq = prefixo.with_name(prefixo.name + "_stats.csv")
    linhas = {r["Name"]: r for r in csv.DictReader(open(arq, encoding="utf-8"))}
    return linhas


def agregado(prefixo):
    r = ler_stats(prefixo)["Aggregated"]
    n = int(r["Request Count"])
    return {"requisicoes": n, "p50_ms": float(r["50%"]), "p95_ms": float(r["95%"]),
            "req_s": float(r["Requests/s"]),
            "falhas_pct": 100 * int(r["Failure Count"]) / n if n else 0.0}


def ler_requisicoes(prefixo):
    arq = prefixo.with_name(prefixo.name + "_requisicoes.csv")
    if not arq.exists():
        return None
    dados = {"t": [], "u": [], "nome": [], "status": [], "ms": [], "falha": []}
    for r in csv.DictReader(open(arq, encoding="utf-8")):
        dados["t"].append(float(r["t_s"]))
        dados["u"].append(int(r["usuarios"] or 0))
        dados["nome"].append(r["nome"])
        dados["status"].append(int(r["status"] or 0))
        dados["ms"].append(float(r["tempo_ms"]))
        dados["falha"].append(int(r["falha"]))
    return {k: np.array(v) for k, v in dados.items()}


def metricas(req, mascara):
    ms, falha, t = req["ms"][mascara], req["falha"][mascara], req["t"][mascara]
    if len(ms) == 0:
        return None
    span = max(t.max() - t.min(), 1.0)       # evita vazão infinita com 1 amostra
    return {"requisicoes": int(len(ms)), "p50_ms": float(np.percentile(ms, 50)),
            "p95_ms": float(np.percentile(ms, 95)), "req_s": float(len(ms) / span),
            "falhas_pct": float(100 * falha.mean())}


def janelas(req, largura=5.0, nome=None):
    """Série temporal em janelas de `largura` s: (t_meio, usuarios, p95, falhas%, req/s)."""
    sel = np.ones(len(req["t"]), bool) if nome is None else (req["nome"] == nome)
    t = req["t"][sel]
    if len(t) == 0:
        return []
    saida = []
    for ini in np.arange(0, t.max() + largura, largura):
        m = sel & (req["t"] >= ini) & (req["t"] < ini + largura)
        if m.sum() == 0:
            continue
        saida.append((ini + largura / 2, int(np.median(req["u"][m])), float(np.percentile(req["ms"][m], 95)),
                      float(100 * req["falha"][m].mean()), float(m.sum() / largura)))
    return saida


registro = []
resumo = {}


def registrar(cenario, execucao, tipo, usuarios, ritmo, duracao, met, decisao, justificativa, extra=None):
    linha = {"cenario": cenario, "execucao": execucao, "data": DATA, "tipo_teste": tipo, "usuarios": usuarios,
             "ritmo_r": ritmo, "duracao_s": duracao, "requisicoes": met["requisicoes"],
             "p50_ms": round(met["p50_ms"]), "p95_ms": round(met["p95_ms"]), "req_s": round(met["req_s"], 1),
             "falhas_pct": round(met["falhas_pct"], 2), "decisao": decisao, "justificativa": justificativa}
    linha.update(extra or {})
    registro.append(linha)


# ------------------------------------------------------------------ fases com -u/-r/-t (Pacote B e projeto)
def analisar_fases(cenario, pasta, fases, meta_p95, meta_falhas, chave):
    """fases: [(prefixo_base, usuarios, ritmo, duracao_s, rotulo)]"""
    res = {}
    for base, u, r, dur, rotulo in fases:
        reps = []
        for rep in (1, 2, 3):
            pref = pasta / f"{base}_r{rep}"
            if not pref.with_name(pref.name + "_stats.csv").exists():
                continue
            ag = agregado(pref)
            req = ler_requisicoes(pref)
            rampa = u / r
            pat = metricas(req, req["t"] >= rampa) if req is not None else None
            por_ep = {}
            if req is not None:
                for nome in sorted(set(req["nome"])):
                    m = metricas(req, (req["nome"] == nome) & (req["t"] >= rampa))
                    if m:
                        por_ep[nome] = m
            base_met = pat or ag
            atende = base_met["p95_ms"] <= meta_p95 and base_met["falhas_pct"] <= meta_falhas
            parada = ""
            log = pref.with_name(pref.name + ".log")
            if log.exists():
                for l in open(log, encoding="utf-8", errors="replace"):
                    if l.startswith("[PARADA]"):
                        parada = l.strip()
            justif = (f"patamar após rampa de {rampa:.0f} s: p95={base_met['p95_ms']:.0f} ms, "
                      f"falhas={base_met['falhas_pct']:.2f}% (meta p95<={meta_p95} ms e falhas<={meta_falhas}%)"
                      + (f"; {parada}" if parada else ""))
            extra = {"p95_agregado_ms": round(ag["p95_ms"]), "falhas_agregado_pct": round(ag["falhas_pct"], 2)}
            for nome, m in por_ep.items():
                extra[f"p95_{nome}_ms"] = round(m["p95_ms"])
                extra[f"n_{nome}"] = m["requisicoes"]
            registrar(cenario, f"r{rep}", rotulo, u, r, dur, base_met,
                      "atende" if atende else "nao atende", justif, extra)
            reps.append({"rep": rep, "agregado": ag, "patamar": pat, "por_endpoint": por_ep,
                         "atende": atende, "parada": parada})
        res[base] = {"usuarios": u, "rotulo": rotulo, "reps": reps}
    resumo[chave] = res
    return res


def grafico_fases(res, titulo, arquivo, meta_p95, meta_falhas):
    bases = [b for b in res if res[b]["reps"]]
    rot = [f"{res[b]['rotulo'].replace(' ', chr(10))}\n{res[b]['usuarios']}u" for b in bases]
    x = np.arange(len(bases))
    fig, eixos = plt.subplots(1, 3, figsize=(15, 4))
    for ax, chave, nome, meta in ((eixos[0], "p95_ms", "p95 (ms)", meta_p95),
                                  (eixos[1], "req_s", "vazão (req/s)", None),
                                  (eixos[2], "falhas_pct", "falhas (%)", meta_falhas)):
        valores = [[(rp["patamar"] or rp["agregado"])[chave] for rp in res[b]["reps"]] for b in bases]
        med = [statistics.median(v) for v in valores]
        lo = [m - min(v) for m, v in zip(med, valores)]
        hi = [max(v) - m for m, v in zip(med, valores)]
        if chave == "req_s":   # vazão total (clara) e só das respostas com sucesso (azul)
            ok = [statistics.median([(rp["patamar"] or rp["agregado"])["req_s"] * (1 - (rp["patamar"] or rp["agregado"])["falhas_pct"] / 100)
                                     for rp in res[b]["reps"]]) for b in bases]
            ax.bar(x, med, width=0.6, color="#a9c9f0", label="total")
            ax.bar(x, ok, width=0.6, color=AZUL, label="com sucesso")
            ax.legend(fontsize=8, loc="upper left")
        else:
            ax.bar(x, med, width=0.6, color=AZUL, yerr=[lo, hi], capsize=3, ecolor=TEXTO2)
        if meta is not None:
            ax.axhline(meta, color=META, linestyle="--", linewidth=1.2)
            ax.text(len(bases) - 0.5, meta, f"meta {meta}", color=TEXTO2, va="bottom", ha="right", fontsize=8)
        ax.set_xticks(x, rot, fontsize=7.5)
        ax.set_title(nome, color=TEXTO, fontsize=10, loc="left")
    fig.suptitle(titulo + "  (barra = mediana de 3 repetições; traço = mín–máx; após a rampa)",
                 x=0.01, y=1.04, ha="left", color=TEXTO, fontsize=11)
    fig.savefig(GRAF / arquivo)
    plt.close(fig)


def grafico_recuperacao(pasta, base, titulo, arquivo, meta_p95, meta_falhas, chave):
    fig, ax = plt.subplots(1, 2, figsize=(11, 3.4))
    cores = [AZUL, LARANJA, AQUA]
    rec = {}
    for rep in (1, 2, 3):
        pref = pasta / f"{base}_r{rep}"
        req = ler_requisicoes(pref) if pref.with_name(pref.name + "_stats.csv").exists() else None
        if req is None:
            continue
        s = janelas(req, 5)
        t = [a[0] for a in s]
        ax[0].plot(t, [a[2] for a in s], color=cores[rep - 1], label=f"r{rep}")
        ax[1].plot(t, [a[3] for a in s], color=cores[rep - 1], label=f"r{rep}")
        ok = [a[0] for a in s if a[2] <= meta_p95 and a[3] <= meta_falhas]
        rec[f"r{rep}"] = {"primeira_janela_dentro_da_meta_s": ok[0] if ok else None,
                          "janelas_fora_da_meta": sum(1 for a in s if not (a[2] <= meta_p95 and a[3] <= meta_falhas)),
                          "janelas": len(s)}
    for a, nome, meta in ((ax[0], "p95 por janela de 5 s (ms)", meta_p95), (ax[1], "falhas por janela de 5 s (%)", meta_falhas)):
        a.axhline(meta, color=META, linestyle="--", linewidth=1.2)
        a.set_title(nome, loc="left", fontsize=10, color=TEXTO)
        a.set_xlabel("tempo desde o início da execução (s)")
        a.legend(fontsize=8)
    fig.suptitle(titulo, x=0.01, y=1.04, ha="left", color=TEXTO, fontsize=11)
    fig.savefig(GRAF / arquivo)
    plt.close(fig)
    resumo.setdefault(chave, {})["recuperacao"] = rec


# ------------------------------------------------------------------ Pacote B
FASES_B = [("verificacao1", 1, 1, 15, "verificação"), ("referencia5", 5, 1, 90, "referência"),
           ("carga20", 20, 2, 90, "carga nominal"), ("estresse50", 50, 5, 90, "estresse 1"),
           ("estresse100", 100, 10, 90, "estresse 2"), ("recuperacao20", 20, 2, 90, "recuperação")]
pB = RES / "pacote-B" / "desafio"
if pB.exists():
    rb = analisar_fases("Desafio B - minicursos", pB, FASES_B, 500, 1, "pacote_B")
    grafico_fases(rb, "Desafio B – consulta de minicursos", "B_patamares.png", 500, 1)
    grafico_recuperacao(pB, "recuperacao20", "Desafio B – recuperação com 20 usuários logo após o estresse de 100",
                        "B_recuperacao.png", 500, 1, "pacote_B_rec")

# exemplo B (1 execução, sem _requisicoes)
exB = RES / "pacote-B" / "exemplo" / "carga20_r1"
if exB.with_name("carga20_r1_stats.csv").exists():
    ag = agregado(exB)
    registrar("Exemplo B - catálogo", "r1", "carga", 20, 2, 90, ag,
              "atende" if ag["p95_ms"] <= 500 and ag["falhas_pct"] <= 1 else "nao atende",
              "agregado do Locust (inclui rampa)")
    resumo["exemplo_B"] = ag

# ------------------------------------------------------------------ Pacote A - exemplo
exA = RES / "pacote-A" / "exemplo"
resumo["exemplo_A"] = {}
for tipo, u in (("carga", 50), ("estresse", "25→250")):
    pref = exA / tipo
    if pref.with_name(tipo + "_stats.csv").exists():
        st = ler_stats(pref)
        ag = agregado(pref)
        rel = st.get("GET /api/relatorio/vendas")
        resumo["exemplo_A"][tipo] = {"agregado": ag, "por_endpoint": {
            n: {"p95_ms": float(r["95%"]), "max_ms": float(r["Max Response Time"]), "req": int(r["Request Count"])}
            for n, r in st.items() if n != "Aggregated"}}
        p95_rel = float(rel["95%"]) if rel else None
        ok = ag["p95_ms"] <= 500 and ag["falhas_pct"] <= 1 and (p95_rel is None or p95_rel <= 2000)
        registrar("Exemplo A - Semana do Cliente", "r1", tipo, u, "", "", ag, "atende" if ok else "nao atende",
                  f"agregado; p95 do relatório de vendas = {p95_rel:.0f} ms (meta 2000)", {"p95_relatorio_ms": p95_rel})
    hist = exA / f"{tipo}_stats_history.csv"
    if hist.exists() and tipo == "estresse":
        linhas = [r for r in csv.DictReader(open(hist, encoding="utf-8")) if r["Name"] == "Aggregated"]
        t0 = int(linhas[0]["Timestamp"])
        def num(v):
            try:
                return float(v)
            except ValueError:
                return float("nan")
        tt = [int(r["Timestamp"]) - t0 for r in linhas]
        fig, (a1, a2) = plt.subplots(2, 1, figsize=(8, 4.6), sharex=True, gridspec_kw={"height_ratios": [3, 1]})
        a1.plot(tt, [num(r["95%"]) for r in linhas], color=AZUL)
        a1.axhline(500, color=META, linestyle="--", linewidth=1.1)
        a1.text(2, 500, "meta geral 500 ms", color=TEXTO2, fontsize=8, va="bottom")
        a1.set_title("Exemplo A – estresse: p95 agregado em janela móvel de 10 s (ms)", loc="left", fontsize=10, color=TEXTO)
        a2.plot(tt, [num(r["User Count"]) for r in linhas], color=TEXTO2)
        a2.set_ylabel("usuários")
        a2.set_xlabel("tempo (s)")
        fig.savefig(GRAF / "A_exemplo_estresse_p95.png")
        plt.close(fig)

# ------------------------------------------------------------------ Pacote A - desafio
pA = RES / "pacote-A" / "desafio"
NOMES_A = {"GET /api/disciplinas": ("consulta", AZUL), "POST /api/matriculas": ("matrícula", LARANJA),
           "GET /api/matriculas/[id]/comprovante": ("comprovante", AQUA)}
resumo["pacote_A"] = {}
for tipo, reps in (("carga", 3), ("pico", 3), ("estresse", 1)):
    for rep in range(1, reps + 1):
        pref = pA / f"{tipo}_r{rep}"
        js = pref.with_name(pref.name + "_resumo.json")
        if not js.exists():
            continue
        rj = json.load(open(js, encoding="utf-8"))
        req = ler_requisicoes(pref)
        ag = agregado(pref)
        info = {"resumo": rj, "agregado": ag}
        if tipo == "carga":
            pat = metricas(req, req["t"] >= 5)
            info["patamar"] = pat
            info["patamar_por_endpoint"] = {n: metricas(req, (req["nome"] == n) & (req["t"] >= 5)) for n in NOMES_A}
            # regime: depois que a corrida inicial de matrículas acabou (t >= 30 s)
            info["regime_t30_por_endpoint"] = {n: metricas(req, (req["nome"] == n) & (req["t"] >= 30)) for n in NOMES_A}
        if tipo == "pico":
            info["pico_0_70"] = {n: metricas(req, (req["nome"] == n) & (req["t"] < 70)) for n in NOMES_A}
            info["volta_70_100"] = {n: metricas(req, (req["nome"] == n) & (req["t"] >= 75)) for n in NOMES_A}
            info["serie"] = {n: janelas(req, 5, n) for n in NOMES_A}
        if tipo == "estresse":
            degraus = {}
            for d in range(1, 9):
                ini, fim = (d - 1) * 30 + 5, d * 30          # descarta 5 s de transição de cada degrau
                degraus[50 * d] = {NOMES_A[n][0]: metricas(req, (req["nome"] == n) & (req["t"] >= ini) & (req["t"] < fim))
                                   for n in NOMES_A}
                degraus[50 * d]["geral"] = metricas(req, (req["t"] >= ini) & (req["t"] < fim))
            info["degraus"] = degraus
        sla = rj["sla"]
        decisao = "atende" if rj["aprovado"] else "nao atende"
        justif = (f"p95 geral={rj['p95_ms']:.0f} ms ({'ok' if sla['p95_geral_ok'] else 'violado'}, meta 800); "
                  f"p95 comprovante={rj['p95_comprovante_ms']} ms ({'ok' if sla['p95_comprovante_ok'] else 'violado'}, meta 1500); "
                  f"erro técnico={rj['erro_tecnico_pct']}% ({'ok' if sla['erro_tecnico_ok'] else 'violado'}); "
                  f"integridade de vagas {'ok' if sla['integridade_vagas_ok'] else 'VIOLADA'}"
                  + (f"; {rj['parada']}" if rj.get("parada") else ""))
        usu = {"carga": 100, "pico": "0→200→20", "estresse": "50→400"}[tipo]
        registrar("Desafio A - matrícula", f"r{rep}", tipo, usu, "", "", ag, decisao, justif,
                  {"p95_comprovante_ms": rj["p95_comprovante_ms"],
                   "negocio": "; ".join(f"{k}={v}" for k, v in rj["respostas_negocio"].items())})
        resumo["pacote_A"][f"{tipo}_r{rep}"] = info

        if tipo in ("estresse", "pico") and rep == 1:
            fig, (a1, a2) = plt.subplots(2, 1, figsize=(9, 5.6), sharex=True, gridspec_kw={"height_ratios": [3, 1]})
            for n, (rot, cor) in NOMES_A.items():
                s = janelas(req, 5, n)
                a1.plot([x[0] for x in s], [x[2] for x in s], color=cor, label=rot, marker="o", markersize=3)
            a1.set_yscale("log")
            a1.axhline(800, color=META, linestyle="--", linewidth=1.1)
            a1.text(2, 800, "meta geral 800 ms", color=TEXTO2, fontsize=8, va="bottom")
            a1.axhline(1500, color=META, linestyle=":", linewidth=1.1)
            a1.text(2, 1500, "meta comprovante 1,5 s", color=TEXTO2, fontsize=8, va="bottom")
            a1.set_title(f"Desafio A – {tipo}: p95 por endpoint em janelas de 5 s (ms, escala log)", loc="left", fontsize=10, color=TEXTO)
            a1.legend(fontsize=8, loc="upper left", bbox_to_anchor=(1.0, 1.0))
            s = janelas(req, 5)
            a2.plot([x[0] for x in s], [x[1] for x in s], color=TEXTO2)
            a2.set_ylabel("usuários")
            a2.set_xlabel("tempo (s)")
            fig.savefig(GRAF / f"A_{tipo}_por_endpoint.png")
            plt.close(fig)

# carga A: p95 por endpoint nas 3 repetições
reps_carga = [resumo["pacote_A"].get(f"carga_r{r}") for r in (1, 2, 3)]
reps_carga = [r for r in reps_carga if r]
if reps_carga:
    fig, ax = plt.subplots(figsize=(8, 3.4))
    x = np.arange(len(NOMES_A))
    for i, (r, cor) in enumerate(zip(reps_carga, (AZUL, LARANJA, AQUA))):
        ax.bar(x + (i - 1) * 0.26, [r["patamar_por_endpoint"][n]["p95_ms"] for n in NOMES_A], width=0.24, color=cor, label=f"r{i + 1}")
    ax.set_xticks(x, [v[0] for v in NOMES_A.values()])
    ax.axhline(800, color=META, linestyle="--", linewidth=1.1)
    ax.axhline(1500, color=META, linestyle=":", linewidth=1.1)
    ax.set_title("Desafio A – carga 100 alunos: p95 por endpoint (ms) nas 3 repetições", loc="left", fontsize=10, color=TEXTO)
    ax.legend(fontsize=8)
    fig.savefig(GRAF / "A_carga_por_endpoint.png")
    plt.close(fig)

# ------------------------------------------------------------------ Projeto anterior
FASES_P = [("referencia10", 10, 5, 60, "referência"), ("nominal50", 50, 10, 60, "nominal"),
           ("estresse100", 100, 20, 60, "estresse 1"), ("estresse200", 200, 40, 60, "estresse 2"),
           ("estresse400", 400, 50, 60, "estresse 3"), ("recuperacao50", 50, 10, 60, "recuperação")]
pP = RES / "projeto-anterior"
if pP.exists():
    rp = analisar_fases("Projeto - produtos-web API", pP, FASES_P, 100, 0.5, "projeto")
    grafico_fases(rp, "Projeto anterior – API produtos-web", "P_patamares.png", 100, 0.5)
    grafico_recuperacao(pP, "recuperacao50", "Projeto – recuperação com 50 usuários logo após o estresse de 400",
                        "P_recuperacao.png", 100, 0.5, "projeto_rec")

    exp = pP / "exploratorio1000_r1"
    if exp.with_name(exp.name + "_stats.csv").exists():   # degrau exploratório extra, 1 execução
        req = ler_requisicoes(exp)
        m = metricas(req, req["t"] >= 10)
        registrar("Projeto - produtos-web API", "r1", "exploratório", 1000, 100, 60, m,
                  "atende" if m["p95_ms"] <= 100 and m["falhas_pct"] <= 0.5 else "nao atende",
                  "degrau extra fora do plano, 1 execução, após 10 s de rampa",
                  {"p95_agregado_ms": round(agregado(exp)["p95_ms"])})
        resumo["projeto_exploratorio_1000"] = m

# ------------------------------------------------------------------ saída
campos = []
for l in registro:
    for k in l:
        if k not in campos:
            campos.append(k)
with open(RES / "registro_resultados.csv", "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=campos)
    w.writeheader()
    w.writerows(registro)
with open(RES / "resumo_analise.json", "w", encoding="utf-8") as f:
    json.dump(resumo, f, ensure_ascii=False, indent=1, default=float)
print(f"{len(registro)} execuções registradas; gráficos em {GRAF}")
