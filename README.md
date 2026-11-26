# Trabalho 1 – Testes de desempenho (ES III)

Equipe: Luiz Felipe de Lima Silva Tavares da Costa e Samuel Alves de Sousa · Linguagem dos testes: **Python** (Locust)

| Parte | Sistema | Onde está |
|---|---|---|
| Exemplo A – Semana do Cliente | Sabor Express (`localhost:5000`) | `pacote-A/exemplo/` (script do professor, sem alterações) |
| **Desafio A – Abertura da matrícula** | Matrícula Acadêmica (`localhost:5000`) | `pacote-A/desafio/locustfile_matricula.py` + `plano_desafio_A.md` |
| Exemplo B – Catálogo | Biblioteca (`127.0.0.1:8000`) | `pacote-B/exemplo/` (script do professor, sem alterações) |
| **Desafio B – Consulta de minicursos** | Minicursos (`127.0.0.1:8000`) | `pacote-B/desafio/desafio_locust.py` + `plano_desafio_B.md` |
| **Projeto anterior** | API do *produtos-web* (Prog. para Internet II) em `localhost:3000` | `projeto-anterior/` |
| Sistemas testados (cópia do kit do professor, sem alterações) | Pacote A (Flask) e Pacote B | `sistemas/` |
| Resultados brutos | CSV, HTML, logs, JSON de cada execução | `resultados/` |
| Tabela-resumo e gráficos | gerados por `ferramentas/analisar.py` | `resultados/registro_resultados.csv`, `resultados/graficos/` |
| Relatório | | `relatorio.md` / `relatorio.pdf` |
| Slides da apresentação (Pacote A, com apêndices do B e do projeto) | | `slides.pdf` |

## Passo a passo no Windows (Git CMD)

**Pré-requisitos**
- Python 3 (testado com 3.13 e 3.15). No instalador, marque *Add python.exe to PATH*.
- Git for Windows (instala o terminal **Git CMD**, usado em todos os passos).

Use sempre `127.0.0.1` nos endereços, não `localhost`: no Windows, `localhost` deixou cada requisição cerca de 2 s mais lenta.

**1. Baixar o trabalho** (uma vez)
```bat
cd C:\
mkdir Projetos
cd Projetos
git clone https://github.com/luizfelipettavares/es3-trabalho1-desempenho
```

**2. Criar o ambiente e instalar as dependências** (uma vez)
```bat
cd C:\Projetos\es3-trabalho1-desempenho
python -m venv .venv
.venv\Scripts\activate.bat
python -m pip install -r requirements.txt
python -m pip install -r sistemas\pacote-A\requirements.txt
```
Certo quando a linha começa com `(.venv)` e o `pip` termina sem erro.
Em toda janela nova, entre na pasta e rode `.venv\Scripts\activate.bat` de novo.

**3. Subir os sistemas** (uma janela do Git CMD para cada; não feche)

Janela 1 – Pacote A (porta 5000):
```bat
cd C:\Projetos\es3-trabalho1-desempenho
.venv\Scripts\activate.bat
cd sistemas\pacote-A
python app.py
```
Certo quando aparece `Running on http://127.0.0.1:5000`.

Janela 2 – Pacote B (porta 8000):
```bat
cd C:\Projetos\es3-trabalho1-desempenho
.venv\Scripts\activate.bat
cd sistemas\pacote-B
python app.py
```
Certo quando aparece `Aplicação local em http://127.0.0.1:8000`.

**4. Rodar o teste** (janela 3)
```bat
cd C:\Projetos\es3-trabalho1-desempenho
.venv\Scripts\activate.bat
cd pacote-A\desafio
set TIPO_TESTE=carga
set DURACAO_S=30
locust -f locustfile_matricula.py --host http://127.0.0.1:5000 --headless --csv demo
```
- `TIPO_TESTE`: `carga`, `pico` ou `estresse`. `DURACAO_S=30` encurta a carga para 30 s (sem ele: 120 s, como no relatório).
- O teste zera o sistema sozinho antes de começar.

Resultado esperado: consulta e matrícula em dezenas de ms; comprovante em segundos;
`erros técnicos = 0.00%`, `[INTEGRIDADE] vagas OK` e `[SLA] REPROVADO` (exit code 1).
O SLA falha por causa do comprovante, como no relatório; não é erro do teste.

Para repetir todas as execuções do relatório, ver a seção 3 abaixo.

**5. Encerrar**: `Ctrl+C` nas janelas 1 e 2. Os arquivos `demo*` criados em `pacote-A\desafio` podem ser apagados.

**Se algo der errado**

| Aparece | Fazer |
|---|---|
| `'python' não é reconhecido` | Reinstale o Python marcando *Add python.exe to PATH* e abra um Git CMD novo. |
| `'locust' não é reconhecido` | Ambiente não ativado: `.venv\Scripts\activate.bat` na pasta do trabalho. |
| `ModuleNotFoundError: No module named 'flask'` | Faltou o passo 2: `python -m pip install -r sistemas\pacote-A\requirements.txt`. |
| `Address already in use` / porta ocupada | O sistema já está rodando em outra janela: use essa ou feche-a com `Ctrl+C`. |
| Conexão recusada | A janela 1 parou: rode `python app.py` de novo. |
| Tudo em ~2.000 ms | Ficou `localhost` no comando: troque por `127.0.0.1`. |

## Passo a passo completo (Linux/macOS e todas as execuções)

As seções abaixo trazem todos os comandos usados para gerar os resultados registrados.

## 1. Preparar o ambiente (uma vez)

```bash
python -m venv .venv
source .venv/bin/activate            # Windows: .venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```
Ativação no Windows: Git CMD/CMD `.venv\Scripts\activate.bat` · PowerShell `.venv\Scripts\Activate.ps1` · Git Bash `source .venv/Scripts/activate`.

O sistema do Pacote A (`python app.py`) precisa do Flask, que não está no `requirements.txt` acima.
Com o ambiente ativado, instale também:

```bash
python -m pip install -r sistemas/pacote-A/requirements.txt
```
O sistema do Pacote B usa só a biblioteca padrão do Python e não precisa de nada extra.

Versões usadas nas execuções registradas: ver `versoes_utilizadas.txt`.

## 2. Subir os sistemas (um terminal para cada)

```bash
# sistemas testados (cópia do kit do professor, em sistemas/ – ver sistemas/LEIA.md)
cd sistemas/pacote-A && python app.py   # http://localhost:5000
cd sistemas/pacote-B && python app.py        # http://127.0.0.1:8000

# projeto anterior (Node 20+): https://github.com/luizfelipettavares/produtos-web
cd produtos-web/api && npm install && npm run build && PORT=3000 node dist/server.js # http://localhost:3000
```

> **Windows: use `127.0.0.1`, não `localhost`.** Num teste em Windows 11, com `--host http://localhost:5000`
> toda requisição levou cerca de 2 s a mais (inclusive a consulta, que é de dezenas de ms). Com
> `--host http://127.0.0.1:5000` os tempos ficaram normais. Exemplo no Git CMD/CMD:
>
> ```bat
> cd pacote-A\desafio
> set TIPO_TESTE=carga
> set DURACAO_S=30
> locust -f locustfile_matricula.py --host http://127.0.0.1:5000 --headless --csv demo
> ```
> (`DURACAO_S=30` encurta a carga para 30 s; sem ele são 120 s, como no relatório.)

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
