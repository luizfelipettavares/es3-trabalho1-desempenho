# Plano de teste de desempenho – Projeto anterior (produtos-web)

Equipe: Luiz Felipe de Lima Silva Tavares da Costa e Samuel Alves de Sousa  Projeto: produtos-web (Programação para Internet II) – https://github.com/luizfelipettavares/produtos-web
Data: 17/11/2026 · Escrito **antes** das execuções. Resultados: `../relatorio.md`.

## Sistema
Front React 19 + Vite que consome uma API REST Express 5 / Node (TypeScript). A API serve um
catálogo em memória (6 produtos) com busca por nome (`q`) e filtro de estoque (`inStock`).
Rodando em `localhost:3000` a partir do build (`npm run build && node dist/server.js`). **Sem banco
de dados** (dados em memória no processo Node).

## 1. Plano

| Item | Preenchimento |
|---|---|
| Operação importante | `GET /api/products` – é a primeira e única chamada que a tela faz ao abrir; se ela demora, o usuário vê "Carregando produtos…". |
| Pergunta / hipótese | Com 50 usuários simultâneos (uma turma inteira abrindo o link do trabalho ao mesmo tempo, ~2× o tamanho de uma turma de ADS), a API responde com p95 ≤ 100 ms e falhas ≤ 0,5%. Hipótese: o Node é single-thread mas a operação é trivial (filtro em 6 itens), então o limite deve vir do gerador de carga (mesma máquina, 2 vCPU) antes da API. |
| Por que essas metas (e não as do pacote) | 100 ms é o limite de resposta "instantânea" usado em usabilidade (Nielsen): a lista aparece sem o usuário perceber espera. A chamada não faz I/O, então qualquer valor bem acima de 100 ms indica fila no processo, não trabalho útil. Falhas ≤ 0,5% porque não há regra de negócio que justifique recusar uma leitura: qualquer erro é técnico. |
| Operações e proporção | listar (`/api/products`) peso 5 – abrir a página · buscar (`?q=`) peso 3 · buscar com estoque (`?q=&inStock=true`) peso 1 · categorias peso 1. Termos: ma, maçã, pit, er, abóbora, x (sem resultado). |
| Verificações de conteúdo | 200; JSON lista; listar = 6 itens; busca só devolve nomes que contêm o termo (sem diferenciar maiúsculas); com `inStock=true` nenhum item `stocked=false`; categorias = [Frutas, Verduras]. |
| Think time | 0,5 a 2 s |
| Perfis (60 s cada, em sequência) | Referência 10u (r=5) · **Nominal 50u (r=10)** · Estresse 100u (r=20) · 200u (r=40) · 400u (r=50) · Recuperação 50u (r=10) logo após o estresse |
| Repetições | 3 de cada fase |
| Metas | Nominal 50u: p95 ≤ 100 ms e falhas ≤ 0,5% (medido após a rampa). Recuperação: dentro da meta já na primeira janela de 5 s após a rampa. |
| Critério de parada | Falhas > 20% ou p95 > 2 s por 10 s, ou máquina instável (CPU do gerador a 100% invalida a medição – registrar). |

## 2. Ambiente

| Item | Valor |
|---|---|
| Processador / memória | Intel Xeon 2,1 GHz, 2 vCPU (VM) / 7,8 GB |
| Sistema operacional | Ubuntu 24.04.5 LTS |
| Runtime do sistema | Node 22.23.4, Express 5 (build `tsc`) |
| Banco | Nenhum (dados em memória) |
| Ferramenta | Locust 2.47.0 / Python 3.13.18 |
| Servidor e gerador na mesma máquina? | Sim |
