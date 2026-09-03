# ADR-003: Atraso configurável do pipeline de escalonamento no Laço de Simulação

*Tradução de [`docs/adr/ADR-003-scheduling-pipeline-delay.md`](../ADR-003-scheduling-pipeline-delay.md) — a versão em inglês é a canônica.*

## Status

Accepted

## Data

2026-07-27

## Contexto

A ADR-002 estabeleceu a simulação em malha fechada e dividiu o estado de rede em estado exógeno (produzido por `scenario_generator`) e estado dependente de decisão (ocupação de buffer, HARQ), atualizado pelo Laço de Simulação com base nas decisões do escalonador. Ela deixou em aberto exatamente *quando*, em relação à TTI para a qual uma decisão foi computada, essa decisão é aplicada para atualizar o estado dependente de decisão.

Duas ordenações foram consideradas:

- **Aplicação imediata**: a decisão computada para a TTI *n* é aplicada (transmissão executada, buffer/HARQ atualizados) dentro da própria *n*. O escalonador nunca observa um estado que omita o efeito de sua própria decisão mais recente.
- **Aplicação atrasada**: a decisão computada para a TTI *n* só é aplicada na TTI *n+1* (ou depois). O escalonador sempre observa estado dependente de decisão que está atrasado em relação à sua própria decisão mais recente por algum número de TTIs.

Para decidir entre elas, verificamos se alguma das ordenações corresponde à forma como sistemas reais baseados em 3GPP e seus simuladores são estruturados, já que Radio Scheduler busca algoritmos de escalonamento e resultados conceitualmente comparáveis a implantações reais:

- **Especificação 3GPP NR**: decisões de escalonamento e sua execução são explicitamente separadas por parâmetros de offset de slot — K0 (offset DCI-para-PDSCH), K2 (offset DCI-para-PUSCH, que *nunca* é zero — uma concessão de UL nunca pode ser executada no mesmo slot em que foi emitida), e K1 (offset PDSCH-para-feedback-HARQ). Isso é um pipeline no nível da especificação, não um detalhe de implementação de uma ferramenta específica.
- **Módulo NR do ns-3**: implementa um atributo `MacToChannelDelay` (padrão de 2 slots) — o MAC/escalonador deliberadamente trabalha à frente da PHY para modelar a latência de processamento real entre uma decisão e sua execução.
- **srsRAN**: o low-PHY processa amostras de downlink vários slots antes da transmissão real (offset de ~3 slots), e preserva a temporização clássica de feedback HARQ n+4 do LTE.
- **OpenAirInterface**: implementa os mesmos offsets de concessão-para-transmissão baseados em K0/K2 nativamente através de sua interface FAPI MAC-PHY (DL_TTI.request / UL_DCI.request precedem a transmissão correspondente pelo offset especificado).

Nas três ferramentas, o offset é um *parâmetro configurável*, não uma constante fixa no código — implantações reais e seus simuladores variam K0/K1/K2 e atrasos equivalentes dependendo da capacidade de processamento e do caso de uso.

## Decisão

O Laço de Simulação aplica a decisão de um escalonador para a TTI *n* ao estado dependente de decisão (atualização de buffer/HARQ, execução da transmissão) após um **atraso de pipeline configurável de `d` TTIs**, com padrão de **`d = 1`**.

Isso é uma abstração arquitetural da separação real entre decisão e execução em sistemas reais (K0/K1/K2 e seus equivalentes em simuladores), não um detalhe de implementação fixo no código. `d` é um parâmetro do Laço de Simulação, não uma constante fixa embutida em seu fluxo de controle — `d = 0` (aplicação imediata) permanece uma configuração válida e suportada, e `d > 1` não é excluído.

## Alternativas consideradas

- **Somente aplicação imediata (`d` fixo em 0)** — mais simples de raciocinar e implementar, e o escalonador sempre age sobre o estado totalmente atual. Rejeitada como o único comportamento/padrão porque não tem contrapartida em sistemas reais baseados em 3GPP ou seus simuladores, todos os quais separam decisão de execução por pelo menos uma etapa de processamento; usá-la como única opção tornaria os resultados do Radio Scheduler estruturalmente incomparáveis a sistemas reais ou realisticamente simulados.
- **Atraso fixo, embutido no código em exatamente 1 TTI** — corresponde ao caso padrão comum (ex.: o atraso padrão de 2 slots do ns-3 é próximo em espírito, o offset de ~3 slots do srsRAN, a temporização HARQ n+4 do LTE) mas impede estudar como algoritmos se comportam à medida que o atraso cresce, algo que sistemas reais mostram variar com a capacidade de processamento. Rejeitada em favor de um parâmetro configurável com `d = 1` apenas como *padrão*, preservando a capacidade de estudar a sensibilidade ao atraso como uma questão de pesquisa mais adiante.

## Consequências

- O Laço de Simulação precisa manter em buffer pelo menos `d` TTIs de decisões pendentes (computadas mas ainda não aplicadas), em vez de aplicar os efeitos de uma decisão de forma síncrona dentro da mesma etapa em que foi produzida.
- A questão de manutenção de estado/ciclo de vida do escalonador (ainda em aberto conforme a ADR-002) agora precisa levar em conta que um escalonador decidindo para a TTI *n* não vai observar o resultado dessa decisão até a TTI *n+d* — qualquer estado interno corrente que o escalonador mantenha (ex.: a média de throughput do Proportional Fair) precisa ser atualizado com base no que ele decidiu, não em um resultado que ele ainda não pode ver.
- `d` se torna um parâmetro de cenário/execução de primeira classe, ao lado do próprio cenário: duas execuções com o mesmo cenário e escalonador mas `d` diferente devem produzir trajetórias de estado dependente de decisão diferentes, e comparações entre algoritmos precisam manter `d` fixo para serem significativas.
- Isso abre um novo eixo de pesquisa explicitamente suportado pelo framework: medir quão robusto um algoritmo de escalonamento é ao aumento do atraso de pipeline, o que espelha uma questão real e praticamente relevante no design de escalonadores 5G/6G.
- `d = 0` permanece disponível como uma simplificação para desenvolvimento inicial, depuração e testes de correção simples, sem exigir um caminho de código separado — é apenas o caso degenerado do mesmo mecanismo.

## Critérios de validação

- Com `d = 0`, o comportamento do Laço de Simulação é idêntico à ordenação de aplicação imediata (a decisão para *n* está totalmente refletida no estado ao final de *n*).
- Com o padrão `d = 1`, o estado dependente de decisão observado pelo escalonador na TTI *n+1* reflete a decisão computada na TTI *n*, e não a decisão computada em *n+1* — correspondendo à linha do tempo de aplicação atrasada discutida para esta decisão.
- Alterar `d` não exige nenhuma mudança no próprio contrato de `scheduling_interface` — só no buffering interno do Laço de Simulação — confirmando que o atraso de pipeline é uma preocupação do Laço de Simulação, não algo exposto ao escalonador.

## Documentos relacionados

- [`ADR-002`](ADR-002-closed-loop-simulation.md) — simulação em malha fechada e a separação entre estado exógeno e estado dependente de decisão sobre a qual esta decisão se apoia.
- [`docs/architecture_review.md`](../../architecture_review.md) — identificação original do módulo de Laço de Simulação ausente e da questão em aberto de manutenção de estado do escalonador com a qual esta ADR interage.
