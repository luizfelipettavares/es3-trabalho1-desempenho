# Plano de teste de desempenho – Desafio B (consulta de minicursos)

Equipe: Luiz Felipe de Lima Silva Tavares da Costa e Samuel Alves de Sousa  Pacote/Projeto: B – Minicursos  Data: 17/11/2026
Escrito **antes** das execuções. Resultados e análise: `../../relatorio.md`.

## 1. Plano

| Item | Preenchimento |
|---|---|
| Pergunta / hipótese | Com 20 usuários, a consulta de cursos atende p95 ≤ 500 ms e falhas ≤ 1%. Hipótese: como o servidor só atende 4 consultas simultâneas (+30 ms cada), a vazão máxima fica perto de 4 / 0,03 s ≈ 130 req/s; acima disso aparecem 503. Com think time médio de 0,4 s + 30 ms, 20 usuários pedem ~46 req/s (abaixo do limite), 50 pedem ~115 req/s (perto) e 100 pedem ~230 req/s (acima). Esperamos a primeira violação em 50 ou 100 usuários. |
| Operações testadas e proporção | `GET /api/cursos` peso 7 (70%) · `GET /api/cursos/1` peso 3 (30%). Peso = probabilidade; a proporção obtida é conferida na tabela. |
| Verificações de conteúdo | Listagem: 200, `total == 3`, 3 itens, contém "Python". Detalhe: 200, `id == 1`, `nome == "Python"`, `vagas == 2`. 503 = falha (evidência de saturação). |
| Think time | 0,2 a 0,6 s (do roteiro) |
| Massa de dados | Não há (consultas sem parâmetro); `DATA_SIZE` padrão (100 livros) |
| Perfis | Verificação 1u (r=1) 15 s · Referência 5u (r=1) 90 s · Carga 20u (r=2) 90 s · Estresse 50u (r=5) 90 s · Estresse 100u (r=10) 90 s · Recuperação 20u (r=2) 90 s, logo depois do estresse |
| Repetições | 3 por patamar (prefixos `_r1`, `_r2`, `_r3`); as 6 fases rodam em sequência dentro de cada repetição |
| Metas (SLA) | Carga 20u: p95 ≤ 500 ms e falhas ≤ 1%. Recuperação: voltar a essas metas em até 30 s com 20 usuários. As mesmas metas são usadas como régua nos demais patamares. |
| Medição | Patamar = requisições depois da rampa (`t ≥ usuários/r`), a partir de `_requisicoes.csv`; agregado do Locust informado à parte. Recuperação medida em janelas de 5 s. |
| Critério de parada | Falhas > 20% por 10 s ou p95 da janela > 2000 ms por 10 s (implementado no script: `[PARADA]` no log); máquina instável. |

## 2. Ambiente

| Item | Valor |
|---|---|
| Processador / memória | Intel Xeon 2,1 GHz, 2 vCPU (VM) / 7,8 GB |
| Sistema operacional | Ubuntu 24.04.5 LTS |
| Python | 3.13.18 (app usa só a biblioteca padrão, `ThreadingHTTPServer`) |
| Ferramenta | Locust 2.47.0 |
| Servidor e gerador na mesma máquina? | Sim |
