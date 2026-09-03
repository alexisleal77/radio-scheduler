# ADR-004: Linguagem de implementação e ferramental de dependências — Python + uv

*Tradução de [`docs/adr/ADR-004-implementation-language-and-tooling.md`](../ADR-004-implementation-language-and-tooling.md) — a versão em inglês é a canônica.*

## Status

Accepted

## Data

2026-07-28

## Contexto

`docs/architecture_review.md` deliberadamente adiou a linguagem de implementação, listando-a como uma decisão em aberto a ser tomada só depois que as questões arquiteturalmente significativas das quais ela depende estivessem resolvidas. `docs/adr/README.md` nomeia a linguagem de implementação explicitamente como exemplo de decisão que justifica uma ADR.

Até este ponto, o modelo de simulação em malha fechada (ADR-002), o atraso configurável do pipeline de escalonamento (ADR-003), o formato canônico de serialização (ADR-001), e o modelo de domínio (`docs/specification/domain-model-v0.1.md`) já estão todos definidos. A implementação do primeiro módulo, `scenario_generator`, exige uma linguagem concreta e uma forma de gerenciar dependências e ambientes — incluindo uma decisão sobre como esse ambiente é reproduzido entre máquinas e contribuidores, já que reprodutibilidade é um princípio de design declarado do projeto (`docs/architecture.md`, e o Princípio de Design 4 do modelo de domínio).

## Decisão

Radio Scheduler é implementado em **Python**, usando **uv** para gerenciamento de dependências e ambiente (criação de ambiente virtual mais um lockfile versionado).

## Alternativas consideradas

- **Go** (linguagem) — desempenho bruto e tipagem estática mais fortes, bom para a meta de benchmark de custo de sistema. Rejeitada porque seu ecossistema científico/numérico (sem equivalente ao NumPy) é bem mais fraco, e a prototipagem de algoritmos é mais verbosa — um mau encaixe para um projeto cujas implementações de referência também servem como exemplos legíveis.
- **Rust** (linguagem) — o melhor desempenho bruto e segurança de memória entre os candidatos considerados, ideal para medição precisa de custo de sistema. Rejeitada por causa de sua curva de aprendizado acentuada e velocidade de prototipagem mais lenta, o que atrapalharia o estilo de desenvolvimento incremental e em pequenos passos do projeto, e reduziria a legibilidade das implementações de referência como exemplos para futuras contribuições de algoritmos (inclusive gerados por IA).
- **Poetry** (ferramental) — uma alternativa madura e amplamente usada, oferecendo a mesma capacidade central (resolução de dependências, lockfile, empacotamento). Rejeitada em favor da velocidade do uv e de sua ascensão como o padrão moderno para novos projetos Python, embora permaneça uma alternativa razoável caso o uv se mostre inadequado.
- **pip + venv + requirements.txt** (ferramental) — a opção mais simples, sem exigir ferramenta adicional. Rejeitada porque um `requirements.txt` simples não garante, por si só, um lockfile totalmente resolvido e com hash das dependências transitivas — enfraquecendo a garantia de reprodutibilidade já assumida em outros pontos do projeto.

## Consequências

- O ecossistema científico do Python (NumPy, SciPy, pandas, etc.) se torna disponível para geração de cenários, cálculo de métricas e geração de relatórios de benchmark.
- O desempenho de runtime do Python é mais fraco que o de Go ou Rust; o benchmark de custo de sistema (tempo de execução, CPU, memória — metas explícitas do projeto) precisa levar isso em conta ao interpretar números absolutos, por exemplo através de vetorização ou de uma metodologia de medição explícita e documentada, em vez de tratar o tempo de parede bruto como diretamente comparável a uma referência em linguagem compilada.
- `uv` se torna a ferramenta padrão para configurar o ambiente de desenvolvimento; a seção "Commands" do `CLAUDE.md` (atualmente um placeholder) deve ser atualizada com comandos `uv` concretos assim que o projeto for inicializado.
- Um `pyproject.toml` e um `uv.lock` versionado passam a fazer parte do repositório, dando a cada contribuidor (humano, CI, ou outro) um ambiente resolvido idêntico.
- Como as implementações de referência devem ser exemplos legíveis — inclusive para futuros algoritmos gerados por IA — espera-se que a legibilidade do Python reduza a barreira para essa meta declarada do projeto.

## Critérios de validação

Duas máquinas diferentes executando `uv sync` a partir do lockfile versionado produzem ambientes com versões de pacote resolvidas idênticas; a saída da geração de cenário é reproduzível entre esses ambientes dada a mesma seed.

## Documentos relacionados

- [`docs/architecture_review.md`](../../architecture_review.md) — adiamento original da decisão sobre a linguagem de implementação.
- [`docs/adr/README.md`](../README.md) — linguagem de implementação nomeada como exemplo canônico que justifica uma ADR.
- [`docs/specification/domain-model-v0.1.md`](../../specification/domain-model-v0.1.md) — Princípio de Design 4 (determinismo), ao qual a exigência de lockfile desta decisão serve diretamente.
- [`ADR-001`](ADR-001-json-as-scenario-format.md) — formato canônico de serialização que a saída do Scenario Generator precisa seguir.
