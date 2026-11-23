# Trabalho 1 – Testes de desempenho (ES III)

Equipe: Luiz Felipe de Lima Silva Tavares da Costa e Samuel Alves de Sousa · Linguagem dos testes: **Python** (Locust)

| Parte | Sistema | Onde está |
|---|---|---|
| Exemplo A – Semana do Cliente | Sabor Express (`localhost:5000`) | `pacote-A/exemplo/` (script do professor, sem alterações) |
| **Desafio A – Abertura da matrícula** | Matrícula Acadêmica (`localhost:5000`) | `pacote-A/desafio/locustfile_matricula.py` + `plano_desafio_A.md` |
| Exemplo B – Catálogo | Biblioteca (`127.0.0.1:8000`) | `pacote-B/exemplo/` (script do professor, sem alterações) |
| **Desafio B – Consulta de minicursos** | Minicursos (`127.0.0.1:8000`) | `pacote-B/desafio/desafio_locust.py` + `plano_desafio_B.md` |
| **Projeto anterior** | API do *produtos-web* (Prog. para Internet II) em `localhost:3000` | `projeto-anterior/` |
| Resultados brutos | CSV, HTML, logs, JSON de cada execução | `resultados/` |
| Tabela-resumo e gráficos | gerados por `ferramentas/analisar.py` | `resultados/registro_resultados.csv`, `resultados/graficos/` |
| Relatório | | `relatorio.md` / `relatorio.pdf` |
| Slides da apresentação (Pacote A, com apêndices do B e do projeto) | | `slides.pdf` |

## 1. Preparar o ambiente (uma vez)

```bash
python -m venv .venv
source .venv/bin/activate            # Windows: .venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

Versões usadas nas execuções registradas: ver `versoes_utilizadas.txt`.

## 2. Subir os sistemas (um terminal para cada)

```bash
# kit do professor (ESIII_Testes_Funcionais.zip)
cd ESIII_Testes_Funcionais/02_Pacote_A_SaborExpress_Matricula/app && python app.py   # http://localhost:5000
cd ESIII_Testes_Funcionais/03_Pacote_B_Biblioteca_Minicursos && python app.py        # http://127.0.0.1:8000

# projeto anterior (Node 20+): https://github.com/luizfelipettavares/produtos-web
cd produtos-web/api && npm install && npm run build && PORT=3000 node dist/server.js # http://localhost:3000
```

Para o desempenho do projeto usamos a API compilada (`npm run build` + `node dist/server.js`), não o
`tsx watch` de desenvolvimento, para não medir o recompilador.

## 3. Rodar

Sempre a partir desta pasta. Os scripts gravam tudo em `resultados/` e são **retomáveis**:
cada execução concluída deixa um arquivo `<prefixo>.ok` e é pulada se o script for chamado de novo
(apague os `.ok` para repetir do zero).

| O quê | Linux/macOS | Windows (PowerShell) | Duração |
|---|---|---|---|
| Exemplo A | `TIPO_TESTE=carga locust -f pacote-A/exemplo/locustfile.py --host http://localhost:5000 --headless --csv resultados/pacote-A/exemplo/carga --html resultados/pacote-A/exemplo/carga.html` (repetir com `estresse`) | `$env:TIPO_TESTE="carga"; locust ...` | 2 + 5 min |
| Exemplo B | `python -m locust -f pacote-B/exemplo/locustfile.py --host http://127.0.0.1:8000 --headless -u 20 -r 2 -t 90s --stop-timeout 5s --csv resultados/pacote-B/exemplo/carga20_r1 --html resultados/pacote-B/exemplo/carga20_r1.html` | igual | 1,5 min |
| Desafio A (carga ×3, pico ×3, estresse) | `bash ferramentas/rodar_pacote_A.sh` | `ferramentas\rodar_pacote_A.ps1` | ~15 min |
| Desafio B (6 fases × 3) | `bash ferramentas/rodar_pacote_B.sh` | `ferramentas\rodar_pacote_B.ps1` | ~24 min |
| Projeto (6 fases × 3) | `bash ferramentas/rodar_projeto.sh` | — (mesmos comandos do .sh) | ~19 min |
| Corrida de matrícula (defeito) | `python ferramentas/teste_corrida_matricula.py 20 5` | igual | segundos |
| Tabelas e gráficos | `python ferramentas/analisar.py` | igual | segundos |

O desafio A zera o sistema sozinho (`POST /api/admin/reset` no início de cada execução).
Não rode dois testes de carga ao mesmo tempo, nem testes funcionais durante um teste de carga:
gerador e servidor dividem a mesma máquina.

> Testes de carga **só** contra os sistemas em `localhost`. Nunca contra os endereços publicados
> (Vercel/Render) do projeto.

## 4. O que cada arquivo de resultado contém

| Arquivo | Conteúdo |
|---|---|
| `<prefixo>.html` | relatório do Locust |
| `<prefixo>_stats.csv`, `_stats_history.csv`, `_failures.csv` | saídas padrão do Locust (agregado e série a cada segundo) |
| `<prefixo>_requisicoes.csv` | uma linha por requisição (tempo, usuários ativos, nome, status, ms, falha) – usado para medir **depois da rampa** e por janela de tempo |
| `<prefixo>_resumo.json` (só desafio A) | SLA por critério, contagem de 201/409/422, integridade das vagas por disciplina |
| `<prefixo>.log` | saída de console, com as linhas `[SLA]`, `[NEGÓCIO]`, `[INTEGRIDADE]`, `[PARADA]` |
