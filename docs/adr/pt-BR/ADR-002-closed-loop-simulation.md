# ADR-002: Simulação em malha fechada com separação explícita entre estado exógeno e estado dependente de decisão

*Tradução de [`docs/adr/ADR-002-closed-loop-simulation.md`](../ADR-002-closed-loop-simulation.md) — a versão em inglês é a canônica.*

## Status

Accepted

## Data

2026-07-27

## Contexto

`docs/architecture.md` descreve o `scenario_generator` como produzindo cenários "independentes de qualquer algoritmo" e sem "nenhum conhecimento de algoritmos de escalonamento". Levado ao pé da letra, isso significa que toda a trajetória de estado de rede — incluindo a ocupação do buffer — é pré-gerada e idêntica independentemente de qual escalonador rodar contra ela, ou mesmo se algum rodar.

Isso não se sustenta para estado que é causalmente posterior às decisões de escalonamento. A ocupação do buffer na TTI *n* depende do que foi de fato transmitido na TTI *n-1*, que depende do que o escalonador escolheu alocar e se essa transmissão teve sucesso. A necessidade de retransmissão HARQ é o mesmo tipo de caso: ela só existe porque uma transmissão anterior foi escalonada e falhou, ou era devida mas não foi escalonada. Se esse estado é pré-definido independentemente do escalonamento, todo algoritmo é avaliado contra uma trajetória de fila drenada por um servidor ideal hipotético, não pelo algoritmo de fato sob teste — o que anula o propósito de comparar algoritmos quanto a congestionamento, latência e satisfação de QoS, todas metas declaradas do projeto.

`docs/architecture_review.md` sinalizou essa ambiguidade entre malha aberta/malha fechada como a decisão não resolvida de maior prioridade, já que ela determina o formato de `scheduling_interface` e se um módulo de laço de simulação é necessário.

## Decisão

Radio Scheduler usa **simulação em malha fechada**. O estado de rede é dividido em duas categorias:

- **Estado exógeno** — gerado inteiramente de antemão por `scenario_generator`, independente de qualquer escalonador e idêntico entre todos os algoritmos avaliados contra um dado cenário:
  - Qualidade de canal / CQI por UE por TTI
  - Mobilidade do UE
  - Processo de chegada de pacotes / demanda de tráfego (novos bytes entrando no buffer de cada UE por TTI)
  - Resource blocks disponíveis por TTI
  - Classe de QoS por UE

- **Estado dependente de decisão** — computado incrementalmente, TTI a TTI, como função da decisão de alocação do escalonador e do estado exógeno daquela TTI. Esse estado *não* é produzido por `scenario_generator` e não é idêntico entre algoritmos:
  - Ocupação do buffer (ocupação anterior + novas chegadas − o que foi efetivamente transmitido, conforme a decisão do escalonador e o resultado da transmissão)
  - Estado de retransmissão HARQ (uma retransmissão é necessária quando uma transmissão foi escalonada e falhou, ou era devida mas não foi escalonada)

Produzir estado dependente de decisão exige um componente que percorra as TTIs, alimente o estado exógeno mais o estado dependente de decisão atual ao escalonador via `scheduling_interface`, aplique a alocação retornada para atualizar o estado de buffer/HARQ, e repasse o resultado a `benchmark`/`tests`. Este é o "laço de simulação" (simulation loop), uma lacuna de módulo já identificada em `docs/architecture_review.md`. Esta ADR estabelece que tal módulo é necessário; ela não atribui sua propriedade nem projeta sua interface — essa é uma decisão separada, a ser tomada depois.

## Alternativas consideradas

- **Simulação em malha aberta** (estado de rede completo, incluindo ocupação do buffer, pré-gerado independentemente de qualquer escalonador) — mais simples de implementar, trivialmente paralelizável, e os arquivos de cenário são reproduzíveis byte a byte por si só, sem exigir laço de simulação. Rejeitada porque não consegue produzir dinâmicas realistas de congestionamento, estouro de buffer ou latência causadas pelas próprias escolhas de um escalonador — exatamente as propriedades que `benchmark` precisa medir para comparar desempenho de escalonamento de forma significativa.

## Consequências

- A responsabilidade de `scenario_generator` se estreita: ele produz somente estado exógeno, não a trajetória completa de estado de rede. `docs/architecture.md` precisa ser atualizado para refletir essa separação (fora do escopo desta ADR).
- Um novo módulo — o laço de simulação — agora é necessário. Nenhum módulo existente é seu dono ainda; atribuir essa propriedade (provavelmente junto com a questão de propriedade do modelo de domínio) é a próxima decisão a tomar, conforme a ordem de resolução em `docs/architecture_review.md`.
- O mesmo cenário, reproduzido contra dois escalonadores diferentes, produzirá legitimamente trajetórias de buffer/HARQ diferentes. A reprodutibilidade é preservada no nível do estado exógeno (fixo/com seed) e da regra de transição de estado (determinística dado o estado anterior e a decisão) — não no nível da própria trajetória de buffer, que se espera que varie por algoritmo e é precisamente o que está sendo medido.
- Os fixtures de `tests/` para comportamento dependente de buffer precisam levar em conta que o estado de buffer esperado é função tanto do cenário quanto do escalonador sob teste, não do cenário isoladamente.
- `scheduling_interface` precisa levar em conta a manutenção de estado do escalonador entre TTIs (ex.: a média corrente de throughput do Proportional Fair, o último UE servido do Round Robin), já que a interface agora é invocada repetidamente dentro de um laço em etapas, em vez de uma única vez contra um cenário totalmente materializado. Esta ADR não resolve essa questão de manutenção de estado — ela permanece em aberto, conforme `docs/architecture_review.md`.

## Critérios de validação

- Dois algoritmos de escalonamento diferentes, executados contra o mesmo cenário, produzem valores de estado exógeno idênticos (CQI, chegadas, mobilidade, resource blocks, classe de QoS) em cada TTI, e trajetórias de buffer/HARQ divergentes onde suas decisões de alocação divergem.
- Reexecutar o mesmo algoritmo contra o mesmo cenário (mesma seed) produz uma trajetória de estado dependente de decisão idêntica, confirmando que a regra de transição de estado é determinística.
- A saída de `scenario_generator` não contém nenhum campo de ocupação de buffer ou de HARQ — só estado exógeno — uma vez que o módulo esteja implementado.

## Documentos relacionados

- [`docs/architecture.md`](../../architecture.md) — responsabilidades de `scenario_generator` e `scheduling_interface` (a serem atualizadas para refletir a separação exógeno/dependente de decisão).
- [`docs/architecture_review.md`](../../architecture_review.md) — identificação original da ambiguidade malha aberta/malha fechada e do módulo de laço de simulação ausente.
- [`ADR-001`](ADR-001-json-as-scenario-format.md) — formato canônico para dados de cenário; os campos de estado exógeno definidos aqui são o que `scenario_generator` vai serializar sob esse formato.
