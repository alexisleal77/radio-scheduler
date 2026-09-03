# ADR-005: Módulo de domínio central (`radio_scheduler.domain`) para entidades compartilhadas

*Tradução de [`docs/adr/ADR-005-domain-module.md`](../ADR-005-domain-module.md) — a versão em inglês é a canônica.*

## Status

Accepted

## Data

2026-07-28

## Contexto

`docs/architecture_review.md` identificou a ausência de um "módulo Core/domínio" canônico como uma peça faltante da arquitetura: `scenario_generator`, `scheduling_interface`, `reference_implementations`, e `benchmark` referenciam todos conceitos compartilhados (UE, Resource Block, Scenario, Allocation Decision, QoS Class, etc.) pelo nome, mas nenhum módulo foi declarado dono de seu formato — deixando cada módulo livre para inventar informalmente o seu próprio, reintroduzindo silenciosamente o acoplamento que a arquitetura pretende evitar.

`docs/specification/domain-model-v0.1.md` posteriormente resolveu o lado *conceitual* dessa lacuna — Princípios de Design, Entidades Centrais e seus relacionamentos agora estão definidos — mas não decidiu onde, no código, essas entidades seriam de fato implementadas. Essa decisão agora é necessária para começar a implementar `scenario_generator`, que precisa de tipos concretos de `Scenario`, `TTI`, `UE`, e relacionados para produzir sua saída.

## Decisão

Criar um novo subpacote, **`src/radio_scheduler/domain/`**, contendo somente as dataclasses correspondentes às entidades definidas na seção de Entidades Centrais de `docs/specification/domain-model-v0.1.md`. `scenario_generator`, `scheduling_interface`, `reference_implementations`, e `benchmark` importam todos de `domain`. `domain` não importa de nenhum deles — uma dependência de mão única, prevenindo ciclos de importação e mantendo-o como a única fundação compartilhada sobre a qual os outros quatro módulos são construídos.

## Alternativas consideradas

- **Colocar as entidades dentro de `scheduling_interface`** (com base no raciocínio de que `docs/architecture.md` já o chama de "a única coisa que `scenario_generator` e `reference_implementations` têm em comum"). Rejeitada: o papel de `scheduling_interface` é o contrato comportamental (dado um estado, retornar uma decisão), não a propriedade de tipos de dados. Confundir os dois tornaria um módulo responsável por duas preocupações distintas.
- **Colocar as entidades dentro de `scenario_generator`** (o primeiro módulo a ser implementado, e o produtor natural dos dados de `Scenario`). Rejeitada: inverteria a direção de dependência pretendida — `scheduling_interface`, `reference_implementations`, e `benchmark` passariam todos a depender de `scenario_generator` só para obter tipos básicos, mesmo que `docs/architecture.md` declare explicitamente que `scenario_generator` não tem nenhum conhecimento de algoritmos de escalonamento.
- **Deixar cada módulo definir seus próprios tipos locais** para os conceitos de que precisa. Rejeitada categoricamente — é precisamente o risco de acoplamento que `docs/architecture_review.md` e o Princípio de Design 1 do modelo de domínio ("propriedade canônica única") existem para prevenir.

## Consequências

- Um novo subpacote `src/radio_scheduler/domain/` é adicionado, contendo somente dataclasses — nenhuma lógica de geração, escalonamento ou benchmark — consistente com o Princípio de Design 3 do modelo de domínio ("entidades são dados puros").
- `scenario_generator`, `scheduling_interface`, `reference_implementations`, e `benchmark` passam todos a depender de `domain`; `domain` nunca deve importar de nenhum deles.
- O próximo passo de implementação — traduzir as Entidades Centrais de `domain-model-v0.1.md` em dataclasses reais — agora tem um lugar concreto.
- Futuros fixtures de teste e verificações de conformidade (um item em aberto de `docs/architecture_review.md`) vão importar os formatos de entidade de `domain` como sua única fonte de verdade.

## Critérios de validação

Nenhum módulo além de `domain` define sua própria versão de um tipo de Entidade Central; `radio_scheduler.domain` tem zero importações de `scenario_generator`, `scheduling_interface`, `reference_implementations`, ou `benchmark`.

## Documentos relacionados

- [`docs/architecture_review.md`](../../architecture_review.md) — identificação original do módulo Core/domínio ausente.
- [`docs/specification/domain-model-v0.1.md`](../../specification/domain-model-v0.1.md) — definições conceituais que este módulo implementa.
- [`ADR-004`](ADR-004-implementation-language-and-tooling.md) — fundação Python/uv sobre a qual este módulo é construído.
