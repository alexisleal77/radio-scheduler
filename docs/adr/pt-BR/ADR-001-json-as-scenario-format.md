# ADR-001: JSON como formato canônico de dados de cenário

*Tradução de [`docs/adr/ADR-001-json-as-scenario-format.md`](../ADR-001-json-as-scenario-format.md) — a versão em inglês é a canônica.*

## Status

Accepted

## Data

2026-07-27

## Contexto

`scenario_generator` produz dados de cenário (estado de rede ao longo do tempo — UEs, CQI, demanda de buffer/tráfego, resource blocks, classe de QoS) que precisam ser reproduzíveis, byte a byte, contra qualquer algoritmo de escalonamento. `docs/architecture.md` declara reprodutibilidade como um princípio de design central: o mesmo cenário deve produzir resultados comparáveis e determinísticos entre execuções e entre algoritmos.

Um formato de serialização para cenários (e, por extensão, resultados de benchmark) precisa ser escolhido. A linguagem de implementação ainda não estava decidida, então o formato precisa ser bem suportado e se comportar de forma consistente entre linguagens.

## Decisão

Usar JSON como o formato canônico para dados de cenário e resultados de benchmark.

## Alternativas consideradas

- **YAML** — mais legível para humanos e suporta comentários, mas seus parsers divergem em comportamento entre linguagens e a tipagem implícita é ambígua (ex.: o "problema da Noruega", em que valores como `NO`, `on`, ou `1.0` são interpretados de forma inconsistente dependendo do parser). Isso é um risco direto à garantia de reprodutibilidade para dados que são gerados e consumidos por código, não escritos à mão.

## Consequências

- Arquivos de cenário e de resultado podem ser validados com JSON Schema, o que também serve de base para a futura suíte de testes de conformidade das implementações de `scheduling_interface`.
- O comportamento de parsing é consistente independentemente de qual linguagem venha a ser escolhida para a implementação.
- Arquivos de cenário/configuração destinados a serem escritos ou editados à mão por humanos perdem o suporte a comentários e a sintaxe mais leve do YAML; esta ADR não impede o uso de YAML para esses arquivos caso essa necessidade surja — ela só fixa o formato para dados de cenário e resultados.
- A falta de suporte nativo do JSON a comentários ou vírgulas finais significa que os fixtures de cenário versionados em `tests/` vão precisar de documentação externa (ex.: um README irmão ou campos `$comment`) em vez de notas inline.

## Critérios de validação

Arquivos de cenário produzidos por `scenario_generator` e resultados produzidos por `benchmark` são interpretados de forma idêntica em pelo menos dois runtimes de linguagens diferentes (relevante uma vez que a linguagem de implementação for escolhida), e validam contra um JSON Schema publicado sem ambiguidade na interpretação de tipos.

## Documentos relacionados

- [`docs/architecture.md`](../../architecture.md) — princípio de reprodutibilidade, responsabilidades do `scenario_generator`.
- [`docs/architecture_review.md`](../../architecture_review.md) — lacunas de materialização de cenário e da suíte de testes de conformidade.
