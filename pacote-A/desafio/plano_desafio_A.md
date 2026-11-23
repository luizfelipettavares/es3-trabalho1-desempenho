# Plano de teste de desempenho – Desafio A (abertura da matrícula)

Equipe: Luiz Felipe de Lima Silva Tavares da Costa e Samuel Alves de Sousa  Pacote/Projeto: A – Matrícula Acadêmica  Data: 17/11/2026
Escrito **antes** das execuções. Resultados e análise: `../../relatorio.md`.

## 1. Plano

| Item | Preenchimento |
|---|---|
| Pergunta / hipótese | Com 100 alunos por 2 min o portal atende p95 geral ≤ 800 ms, p95 do comprovante ≤ 1,5 s e erros técnicos < 1%, sem vagas negativas. Hipótese de risco: o comprovante (geração de PDF simulada) é o gargalo, por ser a operação mais lenta. |
| Operações testadas e proporção | `GET /api/disciplinas` peso 6 · `POST /api/matriculas` peso 3 · `GET /api/matriculas/<id>/comprovante` peso 1, **mais** 1 download automático logo após cada 201. Justificativa: na abertura o aluno atualiza a oferta várias vezes para ver vagas (consulta domina); tenta a matrícula até conseguir ou desistir; baixa o comprovante ao concluir e às vezes volta para conferir. Depois de matriculado (ou sem vaga), o aluno não reenvia a matrícula: a tarefa vira consulta. Em regime: ~90% consulta, ~10% comprovante; no início, surto de POST. |
| Verificações de conteúdo | Oferta: HTTP 200, 7 disciplinas, contém ES3, **nenhuma vaga < 0**. Matrícula 201: comprovante `COMP-NNNNNN`, disciplinas e aluno iguais aos enviados. Comprovante: 200, mesmo id e aluno. 409/422 = regra de negócio correta (`success()`, contadas à parte). Falha técnica = 5xx, timeout (15 s), corpo inválido, status inesperado. Ao final: vagas consumidas por disciplina = nº de 201 que a incluíam. |
| Think time | 1 a 4 s (aluno lendo a oferta e marcando caixas) |
| Massa de dados | 1 aluno diferente por usuário virtual (20260001…20260200, sequencial). Combinações de 2 a 4 disciplinas, no máximo uma por horário (sem choque), escolhidas entre as que o aluno viu com vaga. Acima de 200 VUs (estresse) os números se repetem e o 2º VU recebe 409 "já possui" – documentado. Reset automático antes de cada execução. |
| Perfis | **Carga:** 100 alunos, rampa 5 s (r=20), até 120 s. **Pico:** 0→200 em 10 s, mantém até 70 s, cai para 20 até 100 s (observa a volta). **Estresse:** degraus de +50 a cada 30 s, 50→400 (240 s). |
| Repetições | Carga 3×, pico 3×, estresse 1× (cada estresse consome ~4 min e satura o servidor; uma repetição basta para localizar o ponto de quebra, as 3 cargas medem a variação). |
| Metas (SLA) | p95 geral ≤ 800 ms; p95 comprovante ≤ 1500 ms; erros técnicos < 1%; vagas nunca negativas e consistentes. Avaliadas em **todos** os tipos de teste (carga é onde a meta é obrigatória; no pico e no estresse mostram até onde vale). |
| Critério de parada | Estresse: falhas técnicas > 20% **ou** p95 da janela > 10 s por 10 s seguidos → encerra e registra o motivo (`[PARADA]` no log). Interromper manualmente se a máquina ficar instável. |

## 2. Ambiente

| Item | Valor |
|---|---|
| Processador / memória | Intel Xeon 2,1 GHz, 2 vCPU (máquina virtual) / 7,8 GB |
| Sistema operacional | Ubuntu 24.04.5 LTS (kernel 6.18) |
| Python | 3.13.18 |
| Ferramenta | Locust 2.47.0 (1 processo, sem workers) |
| Servidor | Flask 3.1.3, servidor de desenvolvimento `threaded=True` (como no kit) |
| Servidor e gerador na mesma máquina? | **Sim** – disputam as 2 vCPUs; números absolutos valem só para esta máquina |
