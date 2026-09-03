# ADR-006: Convenções de representação de entidades (referências, incorporação, coleções, escala de CQI)

*Tradução de [`docs/adr/ADR-006-entity-representation-conventions.md`](../ADR-006-entity-representation-conventions.md) — a versão em inglês é a canônica.*

## Status

Accepted

## Data

2026-08-13

## Contexto

`docs/specification/domain-model-v0.1.md` define as 13 Entidades Centrais conceitualmente, mas explicitamente adia o detalhamento em nível de atributo e os tipos de campo concretos para a implementação. Implementar as 11 entidades restantes (Channel Quality, Traffic Arrival, Resource Block, UE, Buffer, HARQ State, Scenario, AllocationDecision, Scheduler, Run, Scheduling Performance Metric) como dataclasses em `radio_scheduler.domain.entities` exige resolver um pequeno conjunto de questões estruturais que se aplicam uniformemente a todas elas — não só a uma entidade isolada. Deixadas sem resolução, cada entidade corre o risco de ser modelada de forma inconsistente (algumas referenciando entidades relacionadas por incorporação, outras por ID, arbitrariamente), que é exatamente o tipo de deriva que `docs/architecture_review.md` e o Princípio de Design 1 (propriedade canônica única) pretendiam prevenir. Essas são decisões estruturais/de fluxo de dados — elas afetam o formato de todo documento JSON produzido sob a ADR-001 — então elas atendem ao critério deste projeto para uma ADR (`docs/adr/README.md`: "afeta limites de módulo... fluxo de dados entre módulos... seria caro reverter depois que a implementação existir").

Pontos de referência usados para decidir isto: como o 3GPP define CQI (um índice padronizado de 0–15, já discutido na pesquisa da ADR-003 sobre pipelines K0/K1/K2 e reutilizado pelo ns-3 NR, srsRAN, OpenAirInterface); e a prática geral de modelagem de dados (comum tanto em conjuntos de dados científicos/reproduzíveis quanto em esquemas relacionais) de normalizar registros repetidos e variáveis no tempo por identificadores no estilo chave-estrangeira, em vez de duplicar cópias incorporadas de um objeto pai em cada registro.

## Decisão

Quatro convenções se aplicam a todas as entidades implementadas a partir deste ponto:

1. **Registros por TTI / repetidos referenciam suas entidades pai por identificador (`str`), não por incorporação.** `ChannelQuality`, `TrafficArrival`, `Buffer`, `HARQState`, e `AllocationDecision` carregam cada um um `ue_id: str` (e, quando relevante, um `tti: TTI`) em vez de incorporar um objeto `UE` completo. Isso evita duplicar um UE inteiro (ou Scenario, ou Scheduler) uma vez por TTI através de potencialmente milhares de registros, e evita o risco de inconsistência do mesmo UE existir como cópias incorporadas ligeiramente diferentes entre registros.
2. **Relacionamentos estáticos, um-para-um, ainda podem ser incorporados.** `UE` incorpora seu `QoSClass` diretamente (criado uma vez, não repetido por TTI); `Run` incorpora seu `Scenario` e `Scheduler` diretamente (um Run tem exatamente um de cada, então não há risco de duplicação a normalizar).
3. **Coleções dentro de entidades são `tuple`, não `list`.** Dataclasses congeladas são, do contrário, imutáveis; um campo `list` quebraria silenciosamente essa garantia (listas são mutáveis no local). Tuplas mantêm toda entidade, incluindo suas coleções, genuinamente imutável e hasheável.
4. **Channel Quality é representada como um índice CQI 3GPP (`int`, 0–15), não SINR.** Este é o valor que as próprias implementações de referência nomeadas pelo projeto (MaxCQI, Proportional Fair) consomem diretamente, evitando uma etapa de conversão SINR→CQI ainda não decidida. Dentro dessa faixa, **1–15 são índices CQI reportáveis**, e **0 representa a ausência de uma indicação de CQI utilizável** — uma condição "fora de faixa" ou um CQI não reportado, conforme a própria abstração do simulador (esta é uma convenção em nível de simulação adotada para este projeto, não uma reafirmação da própria indexação da tabela CQI do 3GPP). O HARQ State é simplificado para um único `retransmission_pending: bool` em vez de modelar múltiplos processos HARQ paralelos, consistente com o princípio de design de "vocabulário mínimo e aditivo" já aplicado a `QoSClass` (rótulo em texto livre em vez do 5QI completo) — modelagem mais rica pode ser adicionada depois sem quebrar este formato.

Nenhuma lógica de validação (ex.: verificar `0 <= cqi <= 15`) é adicionada a nenhuma entidade, conforme o Princípio de Design 3 (entidades são dados puros, sem comportamento incorporado).

## Alternativas consideradas

- **Incorporar entidades relacionadas completas em todo lugar** (ex.: `ChannelQuality` carregando um objeto `UE` aninhado). Rejeitada: duplica os mesmos dados de UE em cada registro por TTI, e cria o risco de duas "cópias" do mesmo UE divergirem silenciosamente — exatamente o risco de acoplamento/consistência que o modelo de domínio foi criado para prevenir.
- **Representar Channel Quality como SINR (float, dB)** em vez de CQI. Rejeitada para v0.1: SINR é a grandeza fisicamente mais fundamental, mas exige uma tabela de mapeamento SINR→CQI que ainda não foi decidida e está fora do escopo do marco atual; CQI é diretamente utilizável pelos escalonadores de referência que este projeto nomeia como metas.
- **Modelar HARQ com estado completo por processo** (múltiplos processos HARQ paralelos, como pilhas 3GPP reais fazem). Rejeitada para v0.1 por ser prematura em relação ao princípio de "vocabulário mínimo e aditivo"; uma flag booleana de retransmissão pendente é suficiente até que uma implementação de referência realmente precise de mais.

## Consequências

- Toda entidade futura que referencie um UE, Scenario, Resource Block, ou Scheduler em um contexto por TTI ou por registro precisa seguir a mesma convenção `_id: str`, por consistência.
- A serialização JSON (ADR-001) de um Scenario ou Run será uma estrutura plana/normalizada (arrays paralelos de registros indexados por ID e TTI) em vez de uma árvore profundamente aninhada — isso precisa ser levado em conta assim que um JSON Schema concreto for escrito.
- Se CQI mais adiante se mostrar insuficiente (ex.: um algoritmo futuro precisar de SINR bruto), adicionar um campo `sinr` ao lado de `cqi` é aditivo e não quebra a decisão desta ADR, conforme o próprio princípio de evolução do modelo de domínio.
- O booleano simplificado do HARQ State vai precisar ser revisitado (um novo campo ou entidade aditiva, não uma mudança que quebra compatibilidade) se uma implementação de referência futura exigir distinguir qual entre vários processos HARQ paralelos está pendente.

## Critérios de validação

Todas as 13 entidades de domínio em `radio_scheduler.domain.entities` seguem as mesmas convenções de referência/incorporação/coleção descritas acima, sem exceções; um Scenario e um Run podem cada um ser convertidos de ida e volta para uma estrutura dict/JSON plana sem que nenhuma entidade exija tratamento especial.

## Documentos relacionados

- [`docs/specification/domain-model-v0.1.md`](../../specification/domain-model-v0.1.md) — definições conceituais de entidade às quais esta ADR adiciona estrutura em nível de implementação.
- [`ADR-001`](ADR-001-json-as-scenario-format.md) — formato JSON canônico que estas convenções moldam.
- [`ADR-003`](ADR-003-scheduling-pipeline-delay.md) — pesquisa anterior sobre K0/K1/K2 do 3GPP e convenções de simuladores (ns-3 NR, srsRAN, OpenAirInterface), reutilizada aqui para a decisão da escala de CQI.
- [`ADR-005`](ADR-005-domain-module.md) — `radio_scheduler.domain` como o módulo onde essas entidades vivem.
