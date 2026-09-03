# ADR-009: Laço de Simulação v0.1 — propriedade do módulo, regra de transição de estado do buffer, e escopo do atraso de pipeline

*Tradução de [`docs/adr/ADR-009-simulation-loop-v0.1.md`](../ADR-009-simulation-loop-v0.1.md) — a versão em inglês é a canônica.*

## Status

Accepted

## Data

2026-08-19

## Contexto

A ADR-002 estabeleceu a simulação em malha fechada e nomeou o "laço de simulação" como um módulo necessário: algo que percorre as TTIs, alimenta estado exógeno mais estado dependente de decisão a um escalonador via `scheduling_interface`, aplica os valores de `AllocationDecision` retornados para atualizar `Buffer`/`HARQState`, e repassa o resultado adiante. Ela explicitamente adiou a propriedade e o design desse módulo. A ADR-003 se apoiou nisso definindo um atraso de pipeline `d` configurável (padrão 1) entre o momento em que uma decisão é computada e o momento em que seu efeito é aplicado, mas também deixou o design concreto do Laço de Simulação para uma etapa seguinte.

Com `scenario_generator`, `scheduling_interface`, e três `reference_implementations` (Round Robin, Proportional Fair, MaxCQI) agora implementados, este módulo é a lacuna estrutural restante que impede qualquer um deles de ser executado de ponta a ponta contra um `Scenario`. Projetá-lo traz à tona duas questões que nem a ADR-002 nem a ADR-003 resolveram:

1. **O que significa "efetivamente transmitido"**, concretamente, para atualizar a ocupação de `Buffer`? A fórmula da ADR-002 ("ocupação anterior + novas chegadas − o que foi efetivamente transmitido") pressupõe uma regra para converter uma `AllocationDecision` em bytes transmitidos. Nenhuma regra assim existe em lugar nenhum do modelo de domínio: `AllocationDecision` carrega somente `resource_block_ids`, `ResourceBlock` não carrega nenhum campo de capacidade, e `ChannelQuality.cqi` é deliberadamente só um índice ordinal, sem conversão CQI-para-taxa (ADR-006, `Documentos relacionados`). Inventar um modelo de capacidade/taxa agora exigiria decidir uma tabela MCS ou uma constante arbitrária de bytes por Resource Block — um compromisso de modelagem sem consumidor atual (nenhuma implementação de referência ou teste precisa ainda de uma cifra de throughput com precisão de byte) e diretamente contra o Princípio de Design 5 de `docs/specification/domain-model-v0.1.md` ("vocabulário mínimo e aditivo").
2. **O que significa o atraso de pipeline `d`**, operacionalmente, dentro de um laço síncrono, em uma única passagem, por TTI? A ADR-003 descreve `d=0` como "a decisão computada para a TTI *n* é aplicada dentro da própria *n*... o escalonador nunca observa um estado que omita o efeito de sua própria decisão mais recente", e `d≥1` como observar estado dependente de decisão que está atrasado por `d` TTIs. Para `d≥1`, aplicar isso literalmente exige que um laço mantenha uma fila de decisões cujos efeitos estão pendentes — um mecanismo de "serviço pendente" ainda não projetado. Para `d=0`, nenhuma fila é necessária: causalmente, um escalonador nunca pode observar o resultado de uma decisão que ainda não tomou, então a única leitura sincronicamente realizável de "aplicada dentro da própria *n*" é que o efeito da decisão é refletido no estado de `Buffer` *depois* que `allocate()` retorna para a TTI *n*, mas *antes* que a TTI *n+1* comece.

## Decisão

**O Laço de Simulação v0.1 vive em um novo módulo de topo, `src/radio_scheduler/simulation_loop/`.** Ele expõe uma única função livre, `run(scenario, algorithm, pipeline_delay=0) -> SimulationResult[StateT]` — não uma classe com estado — de forma consistente com a preferência já estabelecida deste projeto por estado explícito e não escondido (ADR-007, ADR-008).

1. **Regra de transição de estado do Buffer (v0.1): drenagem binária, sem noção de capacidade.** Um UE que recebe pelo menos um Resource Block em uma TTI (ou seja, aparece no conjunto validado de `AllocationDecision` daquela TTI com um `resource_block_ids` não vazio) tem toda a sua `Buffer.occupancy_bytes` da TTI atual — depois que a chegada daquela TTI é aplicada — drenada para exatamente `0`. Um UE que não recebe nenhum Resource Block naquela TTI carrega todo o seu backlog adiante, inalterado (mais a chegada da próxima TTI). Isso deliberadamente não é uma alegação sobre capacidade real de transmissão: é a regra mais simples que permite que `Buffer` seja genuinamente dependente de decisão (fechando o laço conforme a ADR-002) sem inventar um modelo de CQI-para-taxa ou de bytes-por-Resource-Block que nada neste projeto atualmente consome.

2. **`HARQState` não é populado em v0.1.** O `ObservableState.harq_states` de toda TTI é `()`. `HARQState.retransmission_pending` (ADR-006) só pode ser derivado de forma não trivial a partir de um modelo de falha de transmissão, que não existe (ponto 1). Nenhuma das três `reference_implementations` existentes (Round Robin, Proportional Fair, MaxCQI) lê `observable_state.harq_states`, então não há consumidor atual para servir sequer com um valor de placeholder.

3. **v0.1 suporta somente `pipeline_delay=0`.** `run()` levanta `ValueError` para qualquer outro valor, antes de processar qualquer TTI. Sob `d=0`, uma TTI *n* é processada assim: aplicar as chegadas de *n* → construir `ObservableState` (pré-decisão) → chamar `allocate()` exatamente uma vez → validar as decisões retornadas → drenar para `0` o `Buffer` de todo UE que as decisões (validadas) serviram → avançar para a TTI *n+1*. Nenhuma fila de decisões pendentes é necessária ou construída, porque a decisão computada para *n* é totalmente aplicada antes que *n* termine.

4. **`pipeline_delay ≥ 1` está fora do escopo de v0.1**, e não simplesmente não suportado silenciosamente. Suportá-lo exige um mecanismo de "serviço pendente" — uma fila de atraso mantendo decisões computadas mas ainda não aplicadas, drenada `d` TTIs depois de terem sido computadas — que ainda não foi projetado. Isso é nomeado explicitamente aqui como trabalho futuro, não deixado como uma lacuna não declarada.

## Alternativas consideradas

- **Inventar agora um modelo de capacidade de bytes-por-Resource-Block ou CQI-para-MCS**, para que `Buffer` pudesse refletir uma cifra de bytes transmitidos mais realista. Rejeitada para v0.1: nenhuma implementação de referência, teste, ou benchmark precisa atualmente de um número de throughput com precisão de byte: `Buffer` só é lido hoje pelas verificações de elegibilidade de RR/PF/MaxCQI (`occupancy_bytes > 0`), que a regra binária de drenagem já satisfaz exatamente. Adicionar um modelo de capacidade agora seria exatamente o tipo de "abstração sem consumidor imediato" contra o qual o princípio incremental deste projeto (`CLAUDE.md`) alerta, e preempiria uma decisão de modelagem (tabela MCS, eficiência espectral) que merece sua própria ADR dedicada quando algo realmente precisar dela (já sinalizada como dívida futura durante o design do Proportional Fair).
- **Suportar `pipeline_delay ≥ 1` agora, via uma fila de decisões.** Rejeitada para v0.1: viável, mas a linha do tempo de observação do escalonador resultante (`Buffer` em *n* refletindo a decisão computada em *n-d*) já foi implementada uma vez, incorretamente confundida com a leitura literal e causalmente impossível de `d=0`, e revertida antes que qualquer código fosse escrito. Retentar isso corretamente é um trabalho futuro bem delimitado, uma vez que `d=0` esteja comprovadamente funcionando de ponta a ponta contra as três implementações de referência.
- **Popular `HARQState` com um placeholder derivado de `occupancy_bytes > 0`** (ou seja, "retransmissão pendente" sempre que restar backlog). Rejeitada: isso seria redundante com `Buffer` sob o modelo atual sem falhas (nunca diverge dele), sugere de forma enganosa que existe um sinal real de HARQ, e não tem nenhum leitor hoje.
- **Modelar o Laço de Simulação como uma classe com estado** (ex.: com um método `.step()` avançando uma TTI por chamada, atributos de instância mutáveis para decisões acumuladas). Rejeitada: conflita com o precedente de estado explícito já estabelecido por `scenario_generator` (ADR-007) e `scheduling_interface` (ADR-008); uma função livre que recebe e retorna valores imutáveis mantém as mesmas propriedades de testabilidade e ausência de estado escondido.

## Consequências

- As trajetórias de `Buffer` produzidas pelo Laço de Simulação v0.1 não são fisicamente realistas (um UE com qualquer Resource Block sempre drena completamente, independentemente de quanto dado tinha ou quão bom era seu canal) — aceitável para v0.1 porque nada a jusante mede realismo atualmente, mas isso precisa ser revisitado antes que o `throughput_bps`/`SchedulingPerformanceMetric` do `benchmark` possa ser computado de forma significativa.
- Comparar as trajetórias de `Buffer` de dois algoritmos ainda não significa, sob v0.1, o que vai significar quando existir um modelo de capacidade — uma execução só reflete "este UE foi selecionado alguma vez", não "quanto dado de fato se moveu".
- `pipeline_delay` permanece um parâmetro de `run()` (espelhando `domain.Run.pipeline_delay`, padrão `1`) mas v0.1 só aceita `0` — a incompatibilidade entre o padrão de domínio de `Run` (`1`) e o único valor suportado pelo Laço de Simulação (`0`) é uma inconsistência conhecida e temporária até que `d≥1` seja implementado; ela não é resolvida por esta ADR.
- Qualquer ADR futura que introduza um modelo de capacidade/taxa ou uma fila de decisões pendentes para `d≥1` estende esta de forma aditiva; ela não precisa reverter a regra binária de drenagem para as execuções `d=0` já existentes, já que essa regra permanece o comportamento correto especificamente para o caso `d=0`.
- `simulation_loop` se torna o quarto módulo (depois de `domain`, `scenario_generator`, `scheduling_interface`) através do qual a saída de `reference_implementations` pode ser exercitada de ponta a ponta; `benchmark` e `tests` agora podem ser construídos contra uma execução real, não só chamadas unitárias de uma única TTI.

## Critérios de validação

- `run(scenario, algorithm, pipeline_delay=0)` chama `algorithm.initial_state()` exatamente uma vez, e `algorithm.allocate()` exatamente uma vez por TTI em `scenario.ttis`, em ordem ascendente de `index`.
- Para qualquer TTI em que um UE é servido (aparece em uma decisão validada com `resource_block_ids` não vazio), o `Buffer.occupancy_bytes` daquele UE, como visível no `ObservableState` da *próxima* TTI, é exatamente a chegada daquela próxima TTI (ou seja, `0` mais a nova chegada) — nunca carregando adiante a quantidade drenada.
- `run(scenario, algorithm, pipeline_delay=1)` (ou qualquer valor diferente de `0`) levanta `ValueError` antes que qualquer TTI seja processada.
- `ObservableState.harq_states == ()` para toda TTI produzida por `run()`.
- Executar o mesmo `Scenario` através de Round Robin, Proportional Fair, e MaxCQI via `run()` tem sucesso para os três sem nenhuma modificação em `simulation_loop`, confirmando a genericidade sobre `StateT`.

## Documentos relacionados

- [`ADR-002`](ADR-002-closed-loop-simulation.md) — simulação em malha fechada e a separação entre estado exógeno e dependente de decisão da qual a regra de Buffer desta ADR implementa uma instância concreta.
- [`ADR-003`](ADR-003-scheduling-pipeline-delay.md) — atraso de pipeline `d`; esta ADR restringe a faixa suportada em v0.1 a `d=0` e explica por quê, sem alterar a própria decisão da ADR-003 de que `d` deveria eventualmente ser configurável.
- [`ADR-006`](ADR-006-entity-representation-conventions.md) — convenção de CQI como índice (sem campo de taxa/capacidade) que a regra binária de drenagem desta ADR deliberadamente contorna em vez de estender.
- [`ADR-007`](ADR-007-scenario-generator-reproducibility-contract.md) — precedente de estado explícito, local, não global, estendido aqui ao próprio design do Laço de Simulação (função livre, sem estado escondido).
- [`ADR-008`](ADR-008-scheduler-statefulness.md) — contrato de `SchedulingAlgorithm` que o `run()` deste módulo conduz; o Laço de Simulação é o "algo" ao qual o ponto 8 da ADR-008 atribui a responsabilidade de fornecer `ObservableState`, encadear `SchedulerState`, e aplicar decisões.
- [`docs/specification/domain-model-v0.1.md`](../../specification/domain-model-v0.1.md) — Princípio de Design 5 (vocabulário mínimo e aditivo), a base para adiar um modelo de capacidade/taxa.
