# ADR-008: Manutenção de estado do escalonador — estado explícito e encadeado em vez de objetos com estado

*Tradução de [`docs/adr/ADR-008-scheduler-statefulness.md`](../ADR-008-scheduler-statefulness.md) — a versão em inglês é a canônica.*

## Status

Accepted

## Data

2026-08-13

## Contexto

`docs/architecture.md` descreve `scheduling_interface` só em alto nível: "dado o estado atual de rede/cenário, retornar uma decisão de alocação de recursos". `docs/architecture_review.md` sinalizou o formato concreto desse contrato como uma questão arquitetural em aberto desde o início: "Manutenção de estado e ciclo de vida do escalonador: uma implementação de `scheduling_interface` é um objeto com estado e ciclo de vida (ex.: reiniciado entre execuções, uma etapa por TTI), ou uma função pura com estado carregado externamente?" Isso nunca foi resolvido, e foi deixado de lado quando o trabalho avançou para a escolha de linguagem e o modelo de domínio. Não pode mais ser adiado: implementar `scheduling_interface` exige decidir isso, já que determina o próprio formato da interface (classe vs. função, o que cada chamada recebe e retorna).

A questão é forçada pela realidade dos algoritmos: Round Robin precisa lembrar qual UE serviu por último; Proportional Fair precisa manter uma média corrente do throughput alcançado de cada UE; MaxCQI pode não precisar de memória nenhuma. Algo precisa carregar essa memória entre TTIs, e onde/como ela é carregada é exatamente o que esta ADR decide. Conforme `docs/adr/README.md`, a manutenção de estado do escalonador é nomeada explicitamente como um exemplo de decisão que justifica uma ADR.

## Decisão

Um escalonador é uma **função de etapa com estado interno explícito, encadeado externamente** — não um objeto com estado com atributos mutáveis escondidos.

1. **Nenhum estado mutável escondido entre chamadas.** Uma implementação de escalonador não mantém nenhum estado próprio entre invocações. Todo valor que ela precisa lembrar de uma TTI para a próxima é passado como entrada e devolvido explicitamente.

2. **Cada etapa recebe, separadamente:**
   - o **estado observável** atual da rede (`ObservableState` — formato exato adiado, ver "Fora do escopo desta ADR" abaixo);
   - o **estado interno anterior** do algoritmo (`SchedulerState` — formato exato adiado; específico do algoritmo).

3. **Cada etapa retorna, separadamente:**
   - zero ou mais valores de `AllocationDecision` para a TTI atual;
   - o **novo estado interno** do algoritmo, a ser encadeado na próxima chamada.

4. **O estado interno é explícito porque algoritmos diferentes têm memórias diferentes.** Round Robin precisa da posição ou identidade do último UE servido. Proportional Fair precisa de um histórico ou média corrente de throughput por UE. MaxCQI pode não precisar de nenhuma memória histórica — um estado vazio é um caso válido de primeira classe (ver ponto 12 abaixo), não uma exceção especial ao contrato.

5. **Estado interno específico de algoritmo nunca é embutido nas entidades de domínio compartilhadas.** O `SchedulerState` de um dado algoritmo permanece local à sua própria implementação em `reference_implementations`; ele não é adicionado como campos em `UE`, `Scenario`, ou qualquer outra entidade em `radio_scheduler.domain`.

6. **`ObservableState` contém somente o que o escalonador pode legitimamente ver na TTI atual:** o estado exógeno daquela TTI (conforme a ADR-002) e qualquer estado dependente de decisão (Buffer, HARQ) visível sob o atraso de pipeline `d` (conforme a ADR-003) — nada de TTIs futuras, e nenhuma métrica final de desempenho de escalonamento (essas pertencem a `benchmark`/`SchedulingPerformanceMetric`, computadas posteriormente, nunca realimentadas em uma decisão de escalonamento).

7. **O contrato permite múltiplos valores de `AllocationDecision` por TTI**, porque os Resource Blocks de uma TTI são tipicamente distribuídos entre mais de um UE. Isso não exige nenhuma mudança na entidade `AllocationDecision` (ADR-006) — ela já tem o formato de uma decisão por UE; a alocação completa de uma TTI é simplesmente o conjunto de valores de `AllocationDecision` retornados juntos.

8. **O Laço de Simulação — não o escalonador — é responsável por:** fornecer o `ObservableState` a cada TTI; carregar o `SchedulerState` anterior do escalonador; invocar o escalonador; reter o `SchedulerState` retornado para a próxima TTI; e aplicar os valores de `AllocationDecision` retornados para atualizar `Buffer` e `HARQState` (conforme a ADR-002).

9. **`scheduling_interface` não deve:** gerar cenários (isso é responsabilidade de `scenario_generator`); mutar nenhum estado global de simulação; computar métricas de desempenho de escalonamento (isso é responsabilidade de `benchmark`); controlar o atraso de pipeline `d` (isso é responsabilidade do Laço de Simulação, conforme a ADR-003); ou acessar qualquer TTI que não seja a atual.

10. **O estado explícito é escolhido deliberadamente pelo que ele permite**, além de preferência estilística: teste unitário isolado de uma única etapa sem construir ou reiniciar um objeto; reprodução exata de uma execução a partir de um traço de estado registrado; inspeção de transições de estado entre TTIs; checkpoint no meio de uma execução; e — mais importante para a meta declarada deste projeto de admitir algoritmos gerados por IA — validação de conformidade direta, já que uma etapa se torna uma verificação pura de igualdade de entrada/saída, em vez de exigir raciocinar sobre os internos mutáveis ou o ciclo de vida de um objeto.

11. **A futura interface Python vai expressar `SchedulerState` de forma genérica** (ex.: via um parâmetro de tipo), para que cada algoritmo possa declarar seu próprio tipo de estado concreto, em vez de o contrato recair em um `dict`, `Any` genérico, ou uma classe universal carregando campos opcionais para as necessidades de todo algoritmo.

12. **Um estado vazio/trivial é explicitamente suportado** para algoritmos sem memória histórica (ex.: MaxCQI): tal algoritmo ainda recebe e retorna um valor de `SchedulerState` a cada chamada, por uniformidade de contrato — é simplesmente um estado trivial, não uma exceção específica de algoritmo à assinatura da etapa.

## Fora do escopo desta ADR

Os tipos concretos em Python e a assinatura do método/função — o formato exato de `ObservableState` e `SchedulerState`, seus nomes de campo, se são dataclasses ou outra construção, e onde vivem na árvore de módulos — **não** são decididos aqui. Esses são detalhes de implementação reversíveis e locais, a serem resolvidos em uma etapa subsequente e menor, de forma consistente com a maneira como a ADR-007 adiou a lista concreta de campos de `ScenarioGeneratorConfig`.

## Alternativas consideradas

- **Objeto escalonador com estado** (atributos de instância mutáveis, ex.: `scheduler.allocate(observable_state) -> AllocationDecision`, com ciclo de vida "uma instância por Run"). Corresponde a como sistemas reais são comumente construídos (ex.: classes de escalonador MAC persistentes no ns-3/OAI). Rejeitada: conflita com a preferência já estabelecida deste projeto por nenhum estado escondido (RNG local e explicitamente encadeado da ADR-007; Princípio de Design 4 do modelo de domínio), e complica a futura suíte de testes de conformidade/validação sinalizada em `docs/architecture_review.md` — testar uma etapa exigiria gerenciar o ciclo de vida e os internos mutáveis de um objeto, em vez de uma verificação pura de entrada/saída.
- **Estado global ou compartilhado** (ex.: um dict em nível de módulo com médias correntes por UE). Rejeitada categoricamente: a mesma classe de risco que a ADR-007 rejeitou explicitamente para pseudo-aleatoriedade — estado compartilhado escondido arrisca contaminação silenciosa entre Runs ou entre algoritmos, e quebra a rastreabilidade exigida pelo Princípio de Design 4.
- **Embutir o estado de cada algoritmo nas entidades de domínio compartilhadas** (ex.: adicionar um campo `running_throughput` a `UE`). Rejeitada: viola o Princípio de Design 2 ("entidades representam conceitos de domínio, não artefatos de implementação") — uma média corrente específica do Proportional Fair não é um conceito que um especialista de domínio reconheceria como pertencente a um UE em geral — e reintroduz exatamente o acoplamento que a ADR-005 foi criada para prevenir, já que todo novo algoritmo seria tentado a adicionar seus próprios campos a entidades compartilhadas.
- **Retornar apenas uma `AllocationDecision` por TTI.** Rejeitada: não corresponde à realidade física, em que os Resource Blocks de uma TTI normalmente são divididos entre múltiplos UEs; o formato já existente de `AllocationDecision`, de uma decisão por UE (ADR-006), já antecipa múltiplas decisões por TTI, então restringir a uma só forçaria uma alocação irrealista de um único UE recebendo tudo, ou exigiria redesenhar uma entidade já aceita sem benefício algum.
- **Usar `dict` ou `Any` como tipo de estado universal.** Rejeitada: derrota a tipagem estática e a autodocumentação do que o estado de um algoritmo de fato contém, torna estado malformado indistinguível de estado válido sem inspeção em tempo de execução, e vai contra o uso consistente deste projeto de estruturas explícitas e tipadas (dataclasses congeladas) em todo o resto do modelo de domínio.

## Consequências

- O Laço de Simulação (ainda sem um módulo designado como dono) precisa ser projetado para encadear o `SchedulerState` ao longo de seu laço por TTI, além de suas responsabilidades já decididas (aplicar decisões, atualizar Buffer/HARQState, respeitar o atraso de pipeline). Isso adiciona um requisito concreto ao design futuro daquele módulo.
- Todo futuro algoritmo de `reference_implementations` define seu próprio tipo de `SchedulerState`; não há, por design, nenhuma entidade compartilhada de "estado de escalonador" a estender.
- Testes unitários para um algoritmo de escalonamento podem chamar sua função de etapa diretamente com um `ObservableState` e `SchedulerState` construídos à mão, verificando as decisões retornadas e o novo estado — sem exigir configuração/desmontagem de objeto.
- Uma futura suíte de conformidade/validação para algoritmos gerados por humanos ou IA (uma lacuna nomeada em `docs/architecture_review.md`) pode ser construída como verificações de entrada/saída contra a função de etapa, sem precisar raciocinar sobre ciclos de vida de objetos mutáveis.
- Os tipos concretos (`ObservableState`, `SchedulerState`, a assinatura exata de função/genérico) ainda precisam ser projetados em uma etapa seguinte; esta ADR restringe esse design mas não o completa.

## Critérios de validação

- Nenhum algoritmo de `reference_implementations` armazena estado como um atributo de instância mutado no local entre chamadas de etapa; toda memória entre TTIs é passada como entrada e retornada explicitamente.
- Chamar a função de etapa de um escalonador duas vezes com entradas `(ObservableState, SchedulerState)` idênticas produz saídas idênticas de `(AllocationDecision, ...)` e de novo estado.
- Nenhum campo específico de um algoritmo de escalonamento existe em nenhuma entidade de `radio_scheduler.domain`.
- Uma TTI em que mais de um UE recebe Resource Blocks é representável como múltiplos valores de `AllocationDecision` retornados de uma única chamada de etapa.

## Documentos relacionados

- [`docs/architecture_review.md`](../../architecture_review.md) — declaração original da questão em aberto de manutenção de estado do escalonador que esta ADR resolve.
- [`docs/adr/README.md`](../README.md) — nomeia a manutenção de estado do escalonador como exemplo canônico que justifica uma ADR.
- [`ADR-002`](ADR-002-closed-loop-simulation.md) — separação entre estado exógeno e dependente de decisão que molda `ObservableState`; propriedade do Laço de Simulação sobre as atualizações de Buffer/HARQState.
- [`ADR-003`](ADR-003-scheduling-pipeline-delay.md) — atraso de pipeline `d` como preocupação do Laço de Simulação, não exposto a `scheduling_interface`.
- [`ADR-005`](ADR-005-domain-module.md) — propriedade canônica única das entidades compartilhadas, que o estado específico de algoritmo não deve violar.
- [`ADR-006`](ADR-006-entity-representation-conventions.md) — formato já existente de `AllocationDecision`, de uma decisão por UE, reutilizado como está para TTIs com múltiplos UEs.
- [`ADR-007`](ADR-007-scenario-generator-reproducibility-contract.md) — precedente de estado explícito, não global, não escondido, estendido aqui ao estado do escalonador por escolha própria deste módulo (não exigido pela ADR-007).
- [`docs/specification/domain-model-v0.1.md`](../../specification/domain-model-v0.1.md) — Princípios de Design 2, 4, e 5 que motivam a rejeição das alternativas acima.
