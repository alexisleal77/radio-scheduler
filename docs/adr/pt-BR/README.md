# ADRs — pt-BR

Traduções em português brasileiro das Architecture Decision Records (ADRs) de Radio Scheduler.

## Finalidade

Estas traduções existem para acessibilidade e consulta em português. A versão em inglês em [`docs/adr/`](../) é a versão canônica de cada decisão — em caso de qualquer divergência entre uma tradução e o original em inglês correspondente, **o original em inglês prevalece**.

## Correspondência com os originais

Cada tradução usa exatamente o mesmo nome de arquivo do original em inglês (`ADR-NNN-slug.md`), preservando a numeração e a correspondência 1:1 entre as duas pastas. `docs/adr/pt-BR/ADR-000-template.md` é a tradução do modelo usado para criar novas ADRs — não é, ela mesma, um registro de decisão.

## Toda nova ADR precisa das duas versões

A partir desta política, toda ADR nova — e toda edição a uma ADR existente — deve atualizar as duas versões (inglês em `docs/adr/`, português em `docs/adr/pt-BR/`) no mesmo commit. Nenhuma versão pode ficar desatualizada em relação à outra. Ver [`docs/adr/README.md`](../README.md) para o processo completo de ADR.

## Valores de Status

O campo `Status`, no topo de cada ADR, mantém os valores controlados em inglês — `Proposed`, `Accepted`, `Superseded by ADR-NNN`, `Rejected` — mesmo nas traduções, para preservar correspondência mecânica exata com os originais; nenhuma tradução altera esse campo. Significado de cada valor:

- **Proposed** (Proposta) — a decisão foi escrita e está em discussão; ainda não foi colocada em prática.
- **Accepted** (Aceita) — a decisão foi adotada e deve ser tratada como orientação vigente.
- **Superseded by ADR-NNN** (Substituída pela ADR-NNN) — a decisão foi posteriormente substituída por outra ADR. O documento permanece como registro histórico e deve apontar para a ADR que a substitui.
- **Rejected** (Rejeitada) — a decisão foi considerada e explicitamente não adotada. Mantida como registro histórico para que a opção não seja reconsiderada sem informação nova.
