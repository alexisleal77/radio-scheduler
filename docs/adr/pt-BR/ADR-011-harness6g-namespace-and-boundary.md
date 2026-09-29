# ADR-011: Namespace e fronteira do HARNESS6G dentro do Radio Scheduler

*Tradução de [`docs/adr/ADR-011-harness6g-namespace-and-boundary.md`](../ADR-011-harness6g-namespace-and-boundary.md) — a versão em inglês é a canônica.*

## Status

Accepted

## Data

2026-09-29

## Contexto

A proposta HARNESS6G exige uma integração de engineering harness cujas responsabilidades — validar um manifesto de tarefa, materializar um algoritmo de escalonamento candidato dentro de um escopo restrito, executar verificações expostas contra ele, registrar observações estruturadas, congelar um candidato terminal e entregá-lo a um avaliador separado — são distintas tanto:

1. do *componente* de escalonamento (`reference_implementations`, construído sobre o contrato `scheduling_interface`, ADR-008), quanto
2. do *ambiente* experimental que o exercita (`scenario_generator`, `simulation_loop`, `benchmark`).

Isso espelha a distinção que o orientador principal levantou na reunião de orientação de 11/09/2026 (carro vs. estrada/pista): o harness é uma terceira coisa — não é o algoritmo, e não é o ambiente que executa o algoritmo; é a maquinaria que produz e barra um candidato *antes* de o ambiente sequer vê-lo. O coorientador pediu, separadamente, que os documentos parassem de misturar componentes, arquitetura geral, funcionalidade e implementação; o mesmo pedido vale para a organização do código, não só para a prosa.

Ao mesmo tempo, o empacotamento do `radio-scheduler` é deliberadamente minimalista (ADR-004): um único pacote distribuível, `src/radio_scheduler/`, sem lista explícita de pacotes em `[tool.hatch.build]` no `pyproject.toml` (o Hatchling detecta automaticamente o único pacote existente). Introduzir um segundo pacote distribuível de nível superior (`src/harness6g/`) exigiria uma mudança explícita de configuração de build multi-pacote, sem nenhum consumidor externo atual que justifique essa separação — o HARNESS6G v0.1 é usado apenas de dentro deste repositório (scripts/testes), não instalado independentemente em outro lugar.

## Decisão

**`harness6g` é um subpacote do pacote existente: `src/radio_scheduler/harness6g/`.** Não é um novo pacote distribuível de nível superior, e não é incorporado a `scheduling_interface`, `simulation_loop`, `reference_implementations` ou `benchmark`.

A direção de dependência é de mão única e mantida por convenção (verificada pelos critérios de validação abaixo, não por uma fronteira imposta em tempo de build):

- `radio_scheduler.harness6g` pode importar de `domain`, `scheduling_interface`, `simulation_loop`, `reference_implementations` e `benchmark`.
- Nenhum de `domain`, `scheduling_interface`, `simulation_loop`, `reference_implementations` ou `benchmark` pode importar de `harness6g`.

Um algoritmo de escalonamento candidato materializado e congelado pelo `harness6g` precisa continuar satisfazendo o contrato `SchedulingAlgorithm` existente (ADR-008), sem alterações. O `harness6g` não define um contrato concorrente ou mais frouxo para candidatos — ele só adiciona maquinaria de materialização, verificação e proveniência *ao redor* desse mesmo contrato.

Os testes do próprio `harness6g` ficam em `tests/test_harness6g.py`, junto com os testes de todos os outros módulos, sob a mesma raiz de descoberta `unittest discover -s tests` (`CLAUDE.md`) — sem executor ou raiz de descoberta separados.

## Alternativas consideradas

- **Pacote/distribuição separada de nível superior (`src/harness6g/`).** Rejeitada para v0.1: exigiria configuração explícita de build multi-pacote no Hatchling e metadados de empacotamento próprios, sem nenhum consumidor externo atual. Revisitar se o HARNESS6G algum dia precisar ser instalado ou versionado independentemente do `radio-scheduler`.
- **Repositório git separado.** Rejeitada: a própria orientação da proposta enquadra a separação componente/ambiente/harness como lógica e documental, não física ("não exige mover todos os arquivos ou criar repositórios diferentes"). Um repositório separado ou duplicaria os tipos de `domain`/`scheduling_interface`, ou assumiria uma dependência rígida entre repositórios, adicionando uma sobrecarga de coordenação de releases desproporcional ao escopo do v0.1.
- **Incorporar a maquinaria do harness em `scheduling_interface` ou `simulation_loop`.** Rejeitada: confunde o contrato que um candidato implementa (o que o algoritmo *é*) com a maquinaria que gera, verifica, congela e avalia candidatos (o que acontece *ao redor* do algoritmo antes de o ambiente sequer executá-lo) — exatamente a confusão que a distinção carro/harness alerta para evitar.

## Consequências

- Adicionar `harness6g` não exige nenhuma mudança na configuração de build do `pyproject.toml`, já que ele vive dentro da árvore `radio_scheduler` já empacotada.
- Uma futura divisão para um pacote de nível superior genuinamente separado continua possível sem alterar a regra de dependência de mão única — apenas os caminhos de importação mudariam.
- Qualquer importação de `radio_scheduler.harness6g` a partir de `domain`, `scheduling_interface`, `reference_implementations`, `simulation_loop` ou `benchmark` é uma violação arquitetural sob esta ADR, ainda que nada a imponha mecanicamente hoje (ver Critérios de validação).
- Fixtures do `harness6g` (candidatos de demonstração/replay, manifestos de tarefa de exemplo) são fixtures técnicas para exercitar o harness, não artefatos científicos — nunca devem ser descritas como candidatos gerados por um modelo especializado qualificado (ver `docs/design.md` e `docs/demo.md`).

## Critérios de validação

- `grep -rl "harness6g" src/radio_scheduler/domain src/radio_scheduler/scheduling_interface src/radio_scheduler/reference_implementations src/radio_scheduler/simulation_loop src/radio_scheduler/benchmark` não retorna nada.
- Todo candidato aceito pelo carregador de candidatos do `harness6g` satisfaz a mesma verificação estrutural (assinaturas de `initial_state`/`allocate`) que `scheduling_interface.SchedulingAlgorithm` já define — nenhum Protocol paralelo ou mais frouxo é introduzido.
- Os testes do `harness6g` são executados e descobertos pelo mesmo comando `uv run python -m unittest discover -s tests -v` que os de todos os outros módulos, sem configuração separada.

## Documentos relacionados

- [`ADR-004`](ADR-004-implementation-language-and-tooling.md) — o layout Hatchling de pacote único que esta decisão preserva.
- [`ADR-005`](ADR-005-domain-module.md) — `domain` como proprietário das entidades compartilhadas do qual `harness6g` depende, como qualquer outro módulo.
- [`ADR-008`](ADR-008-scheduler-statefulness.md) — o contrato `SchedulingAlgorithm` que os candidatos precisam satisfazer; `harness6g` adiciona maquinaria ao redor dele, não uma alternativa a ele.
- [`docs/design.md`](../../design.md) — a separação entre arquitetura do componente, do ambiente experimental e do HARNESS6G que esta ADR torna concreta no código.
