# ADR-007: Contrato de reprodutibilidade do Scenario Generator (`random.Random` com seed, ordem de iteração fixa)

*Tradução de [`docs/adr/ADR-007-scenario-generator-reproducibility-contract.md`](../ADR-007-scenario-generator-reproducibility-contract.md) — a versão em inglês é a canônica.*

## Status

Accepted

## Data

2026-08-13

## Contexto

Implementar `scenario_generator` exige decidir como o campo `seed` de `Scenario` é de fato honrado. Sem um contrato fixo e documentado de como a pseudo-aleatoriedade é consumida, "mesma seed" não garante, por si só, "mesmo `Scenario`" — a mesma seed alimentada através de uma ordem diferente de sorteios aleatórios produz um resultado diferente. Isso afeta diretamente a garantia de reprodutibilidade já assumida na ADR-002 e no Princípio de Design 4 de `docs/specification/domain-model-v0.1.md` ("o valor de uma entidade precisa ser inteiramente rastreável a partir de informação contida no próprio modelo... nunca a partir de computação ou estado escondido fora do modelo").

Pelos critérios de `docs/adr/README.md`, esta decisão afeta "garantias de reprodutibilidade" nominalmente e seria cara de reverter silenciosamente: qualquer mudança acidental na ordem de sorteio do Scenario Generator ou no escopo do PRNG invalidaria silenciosamente toda seed ou fixture previamente registrada que dependa de sua saída. Isso justifica uma ADR — restrita estritamente ao mecanismo de reprodutibilidade do próprio Scenario Generator, não ao formato concreto de configuração ou às distribuições de geração (detalhes de implementação comuns e reversíveis), e não a como qualquer outro módulo possa alcançar reprodutibilidade para sua própria aleatoriedade.

## Decisão

1. **Somente PRNG local.** `generate_scenario()` cria sua própria instância `random.Random(seed)`, restrita àquela única chamada. Ela nunca lê nem redefine o estado do módulo `random` global, e nunca aceita uma instância `Random` compartilhada externamente. O determinismo permanece rastreável às próprias entradas da chamada, não a estado externo escondido.

2. **Ordem de iteração fixa e documentada.** Toda aleatoriedade é sorteada exatamente nesta ordem: TTIs em ordem ascendente por índice, depois UEs em ordem ascendente por índice dentro de cada TTI; para cada par (TTI, UE), o valor de Channel Quality é sorteado antes do valor de Traffic Arrival correspondente. UEs, atribuição de QoS Class, TTIs, e Resource Blocks são gerados deterministicamente e não consomem aleatoriedade, então sua ordem de geração não tem efeito sobre a reprodutibilidade.

3. **Garantia de reprodutibilidade.** Para uma versão fixa do gerador, chamar `generate_scenario(config)` duas vezes com o mesmo `ScenarioGeneratorConfig` (incluindo a mesma `seed`) produz dois valores de `Scenario` que são estruturalmente iguais (`==`), como consequência dos pontos 1–2 combinados com o fato de as entidades de domínio já serem dataclasses congeladas sobre tuplas (ADR-006).

4. **Nenhuma garantia de reprodutibilidade entre versões.** Esta ADR garante reprodutibilidade somente dentro de uma versão fixa do gerador (algoritmo fixo e ordem de iteração fixa). Ela não garante que uma dada seed reproduza o mesmo `Scenario` em diferentes versões do gerador; espera-se que mudar o algoritmo de geração ou a ordem de iteração altere a saída para uma seed usada anteriormente.

5. **Mudanças que afetam a sequência são mudanças de comportamento observável.** Qualquer mudança no gerador que possa alterar a sequência de valores sorteados do PRNG — reordenar a iteração, adicionar ou remover um sorteio, ou mover um campo de fixo para sorteado aleatoriamente ou vice-versa — precisa ser tratada como uma mudança de comportamento observável, não uma refatoração interna. Tais mudanças precisam ser sinalizadas explicitamente em revisão de código/mensagens de commit, e se forem invalidar seeds ou fixtures previamente registradas usadas em outros pontos do projeto, precisam ser registradas por meio de uma ADR nova ou substituta, em vez de embutidas silenciosamente em uma mudança não relacionada.

6. **A independência do Scenario em relação ao escalonamento é preservada.** Esta ADR não relaxa a ADR-002. `generate_scenario()` produz somente estado exógeno (TTI, UE, QoSClass, ResourceBlock, ChannelQuality, TrafficArrival) e não recebe nenhum escalonador, decisão, ou Run como entrada. Este contrato rege *como* os valores são sorteados, nunca *o que* é sorteado, e não pode ser usado para introduzir estado dependente de escalonamento.

7. **Escolhas concretas de geração estão fora de escopo.** Faixas numéricas padrão (ex.: limites de CQI, limites de tamanho de tráfego), a distribuição de probabilidade usada para CQI e Traffic Arrival, e a lista completa de campos de `ScenarioGeneratorConfig` são detalhes de implementação reversíveis, locais a `scenario_generator`, regidos pelo código e seu README — não por esta ADR.

8. **A verificação usa `unittest`.** A garantia de determinismo no ponto 3 é inicialmente verificada com o `unittest` da biblioteca padrão do Python, evitando uma nova dependência (ex.: `pytest`) nesta etapa, consistente com o escopo de ferramental da ADR-004 e o `dependencies = []` atual do `pyproject.toml`.

## Alternativas consideradas

- **Usar o módulo `random` global** (chamadas em nível de módulo como `random.randint`) em vez de uma instância local `random.Random(seed)`. Rejeitada: ler/redefinir estado global cria estado compartilhado escondido entre chamadas e execuções de teste, conflitando diretamente com o Princípio de Design 4 e arriscando contaminação entre testes.
- **Deixar a ordem de iteração não especificada.** Rejeitada: sem uma ordem fixa e documentada, duas implementações de outra forma corretas (ou duas refatorações da mesma) poderiam produzir sequências diferentes para a mesma seed, quebrando silenciosamente a garantia de reprodutibilidade já assumida em outros pontos.
- **Garantir estabilidade de seed entre versões do gerador.** Rejeitada: prometer que uma seed reproduz identicamente para sempre, mesmo à medida que o algoritmo evolui, congelaria prematuramente os internos do gerador e conflita com o princípio de desenvolvimento incremental deste projeto (`CLAUDE.md`). A reprodutibilidade é restrita a "mesma versão"; mudanças que quebram versão são tratadas como uma obrigação de processo explícita (ponto 5) em vez disso.
- **Adotar `pytest` agora** para o teste de determinismo. Rejeitada nesta etapa: seria a primeira dependência de terceiros do projeto, e o `unittest` da biblioteca padrão é suficiente para o teste de igualdade estrutural que essa garantia exige.

## Consequências

- A aleatoriedade usada para gerar um `Scenario` fica confinada a `scenario_generator`: todo sorteio passa pela única instância `Random` local, na ordem documentada, e o gerador nem lê nem modifica o estado pseudoaleatório global do Python. Isso torna mudanças que afetam a ordem algo que a revisão de código é especificamente responsável por capturar.
- Fixtures de teste ou cenários de exemplo registrados contra uma versão do gerador permanecem válidos somente para aquela versão; se o algoritmo ou a ordem de iteração mudar, fixtures de "`Scenario` esperado para a seed X" registradas anteriormente precisam ser regeneradas, não presumidas estáveis.
- Módulos futuros que precisem de reprodutibilidade para sua própria pseudo-aleatoriedade (ex.: um Laço de Simulação, ou testes repetidos de `benchmark`) podem adotar uma decisão equivalente — uma instância `Random` local com seed e uma ordem de consumo documentada — mas essa escolha pertence ao contexto de cada módulo e não é obrigada por esta ADR.
- Ajustar distribuições concretas ou faixas padrão (ponto 7) nunca exige revisitar esta ADR; só uma mudança no próprio mecanismo (escopo da instância, ordem de iteração, ou a sequência de sorteio observável) exige.
- Adotar `unittest` agora não impede adotar `pytest` depois, se a suíte de testes crescer de formas que o `unittest` lida mal — isso permanece uma decisão separada e reversível.

## Critérios de validação

- Duas chamadas a `generate_scenario` com um `ScenarioGeneratorConfig` idêntico (mesma seed) produzem valores de `Scenario` que comparam como iguais (`==`).
- A aleatoriedade de `scenario_generator` nunca toca nas funções em nível de módulo ou no estado global de `random`.
- A ordem de iteração documentada no ponto 2 corresponde à ordem de fato implementada em `generate_scenario()`.

## Documentos relacionados

- [`ADR-002`](ADR-002-closed-loop-simulation.md) — independência do estado exógeno que esta ADR herda e não relaxa.
- [`ADR-004`](ADR-004-implementation-language-and-tooling.md) — Python/uv, base de ferramental priorizando a biblioteca padrão que justifica escolher `unittest` aqui.
- [`ADR-006`](ADR-006-entity-representation-conventions.md) — dataclasses congeladas e coleções em tupla que tornam a igualdade estrutural `==` suficiente para a garantia de reprodutibilidade.
- [`docs/specification/domain-model-v0.1.md`](../../specification/domain-model-v0.1.md) — Princípio de Design 4 (determinismo como propriedade intrínseca dos dados).
- [`docs/adr/README.md`](../README.md) — critérios aplicados para justificar o escopo restrito desta ADR.
