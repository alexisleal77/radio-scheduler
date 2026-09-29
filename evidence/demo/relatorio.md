# Radio Scheduler — relatório de demonstração (Entrega A)

- Commit: `1866fe4d4b277cb9a080bad6649c2ebee8f2f74a`
- Comando: `uv run python scripts/demo.py`
- Gerado em: 2026-09-29T23:01:58.715598+00:00

Executa Round Robin, Proportional Fair e MaxCQI sobre os mesmos cenários exógenos (pequenos, construídos à mão para ter oráculo verificável — ver `src/radio_scheduler/demo/scenarios.py`), com estado inicial independente por algoritmo, e mede custo computacional via `benchmark.benchmark_run()`. Ver `docs/design.md` seções 1-2 para a distinção entre o componente de escalonamento e o ambiente experimental que o exercita.

## Cenário: `ue_competition`

Duas UEs, CQI empatado (10) em toda TTI, ambas com backlog em toda TTI — isola a política de cada algoritmo (rotação do RR, justiça por média de throughput do PF, escolha gulosa e sem memória do MaxCQI) sem nenhuma diferença de qualidade de canal para justificá-la.

### RoundRobin v0.1

| TTI | UE | Resource Blocks |
|---|---|---|
| 0 | ue-0 | rb-0-0 |
| 0 | ue-1 | rb-0-1 |
| 1 | ue-0 | rb-1-0 |
| 1 | ue-1 | rb-1-1 |

Custo computacional (mediana de 10 repetições): 0.041 ms tempo de relógio, 0.040 ms CPU, 4.9 KiB pico de memória.

### ProportionalFair v0.1

| TTI | UE | Resource Blocks |
|---|---|---|
| 0 | ue-0 | rb-0-0, rb-0-1 |
| 1 | ue-1 | rb-1-0, rb-1-1 |

Custo computacional (mediana de 10 repetições): 0.039 ms tempo de relógio, 0.039 ms CPU, 4.8 KiB pico de memória.

### MaxCQI v0.1

| TTI | UE | Resource Blocks |
|---|---|---|
| 0 | ue-0 | rb-0-0, rb-0-1 |
| 1 | ue-0 | rb-1-0, rb-1-1 |

Custo computacional (mediana de 10 repetições): 0.033 ms tempo de relógio, 0.033 ms CPU, 4.6 KiB pico de memória.

## Cenário: `cqi_difference`

Duas UEs, um Resource Block, uma TTI, ambas em cold-start: só o CQI difere (ue-0=3, ue-1=12). Mostra o MaxCQI escolhendo por CQI puro, enquanto RR e PF (em cold-start) escolhem por ordem canônica, CQI-cego.

### RoundRobin v0.1

| TTI | UE | Resource Blocks |
|---|---|---|
| 0 | ue-0 | rb-0-0 |

Custo computacional (mediana de 10 repetições): 0.023 ms tempo de relógio, 0.023 ms CPU, 3.6 KiB pico de memória.

### ProportionalFair v0.1

| TTI | UE | Resource Blocks |
|---|---|---|
| 0 | ue-0 | rb-0-0 |

Custo computacional (mediana de 10 repetições): 0.025 ms tempo de relógio, 0.024 ms CPU, 3.7 KiB pico de memória.

### MaxCQI v0.1

| TTI | UE | Resource Blocks |
|---|---|---|
| 0 | ue-1 | rb-0-0 |

Custo computacional (mediana de 10 repetições): 0.021 ms tempo de relógio, 0.021 ms CPU, 3.4 KiB pico de memória.

## Cenário: `no_eligibility_or_resources`

Duas condições de contorno distintas: TTI 0 tem Resource Block mas nenhuma UE elegível (sem backlog); TTI 1 tem UEs elegíveis mas nenhum Resource Block disponível. As três implementações devem retornar zero decisões em ambos os casos, sem erro.

### RoundRobin v0.1

Nenhuma decisão de alocação em nenhuma TTI (sem UE elegível e/ou sem Resource Block disponível nesse cenário).

Custo computacional (mediana de 10 repetições): 0.028 ms tempo de relógio, 0.028 ms CPU, 3.9 KiB pico de memória.

### ProportionalFair v0.1

Nenhuma decisão de alocação em nenhuma TTI (sem UE elegível e/ou sem Resource Block disponível nesse cenário).

Custo computacional (mediana de 10 repetições): 0.033 ms tempo de relógio, 0.033 ms CPU, 4.4 KiB pico de memória.

### MaxCQI v0.1

Nenhuma decisão de alocação em nenhuma TTI (sem UE elegível e/ou sem Resource Block disponível nesse cenário).

Custo computacional (mediana de 10 repetições): 0.028 ms tempo de relógio, 0.028 ms CPU, 4.1 KiB pico de memória.

## Limitações conhecidas (v0.1)

- `pipeline_delay` só suporta 0 nesta versão (ADR-009); `d >= 1` é trabalho futuro, não uma funcionalidade já implementada.
- O drenamento de `Buffer` é binário (zera tudo se a UE recebeu ao menos um Resource Block; carrega tudo adiante caso contrário) — não é um modelo de capacidade física de transmissão (ADR-009).
- `HARQState` nunca é populado nesta versão — não existe modelo de falha de transmissão do qual derivá-lo (ADR-009).
- `ChannelQuality.cqi` é um índice ordinal (0-15), sem conversão para taxa/capacidade física por Resource Block (ADR-006); Proportional Fair usa CQI como aproximação de throughput alcançado em sua média móvel interna, nunca como uma medição real de taxa.
- O benchmark mede apenas custo computacional — tempo de relógio, tempo de CPU, pico de memória rastreada pelo Python (ADR-010). Vazão, fairness de taxa e latência de pacotes/QoS continuam fora de escopo nesta entrega.

