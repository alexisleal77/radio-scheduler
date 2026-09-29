from radio_scheduler.demo.runner import DemoRunResult

LIMITATIONS_PT = (
    "- `pipeline_delay` só suporta 0 nesta versão (ADR-009); `d >= 1` é trabalho "
    "futuro, não uma funcionalidade já implementada.\n"
    "- O drenamento de `Buffer` é binário (zera tudo se a UE recebeu ao menos um "
    "Resource Block; carrega tudo adiante caso contrário) — não é um modelo de "
    "capacidade física de transmissão (ADR-009).\n"
    "- `HARQState` nunca é populado nesta versão — não existe modelo de falha de "
    "transmissão do qual derivá-lo (ADR-009).\n"
    "- `ChannelQuality.cqi` é um índice ordinal (0-15), sem conversão para "
    "taxa/capacidade física por Resource Block (ADR-006); Proportional Fair usa "
    "CQI como aproximação de throughput alcançado em sua média móvel interna, "
    "nunca como uma medição real de taxa.\n"
    "- O benchmark mede apenas custo computacional — tempo de relógio, tempo de "
    "CPU, pico de memória rastreada pelo Python (ADR-010). Vazão, fairness de "
    "taxa e latência de pacotes/QoS continuam fora de escopo nesta entrega.\n"
)


def decisions_trace(decisions: tuple) -> dict[int, list[dict]]:
    """Groups `AllocationDecision` values by TTI index, sorted by (tti, ue_id),
    for a small, human-readable trace of who received which Resource Blocks
    in each TTI."""
    trace: dict[int, list[dict]] = {}
    for decision in sorted(decisions, key=lambda d: (d.tti.index, d.ue_id)):
        trace.setdefault(decision.tti.index, []).append(
            {
                "ue_id": decision.ue_id,
                "resource_block_ids": list(decision.resource_block_ids),
            }
        )
    return trace


def result_to_dict(result: DemoRunResult) -> dict:
    """Structured, JSON-serializable view of one `DemoRunResult`: scenario
    identity, per-TTI decision trace, and every benchmark provenance/median
    field — no metric is invented or defaulted to zero for anything the
    project does not measure."""
    benchmark = result.benchmark
    return {
        "scenario_id": result.scenario_id,
        "scenario_description": result.scenario_description,
        "scheduler_name": result.scheduler_name,
        "scheduler_version": result.scheduler_version,
        "decisions_by_tti": decisions_trace(result.decisions),
        "benchmark": {
            "repetitions": len(benchmark.samples),
            "median_wall_time_ns": benchmark.median_wall_time_ns,
            "median_cpu_time_ns": benchmark.median_cpu_time_ns,
            "median_peak_traced_memory_bytes": benchmark.median_peak_traced_memory_bytes,
            "scenario_seed": benchmark.scenario_seed,
            "scenario_num_ttis": benchmark.scenario_num_ttis,
            "scenario_num_ues": benchmark.scenario_num_ues,
            "scenario_resource_blocks_per_tti": list(
                benchmark.scenario_resource_blocks_per_tti
            ),
            "python_implementation": benchmark.python_implementation,
            "python_version": benchmark.python_version,
            "platform": benchmark.platform,
            "machine": benchmark.machine,
            "processor": benchmark.processor,
            "cpu_count": benchmark.cpu_count,
        },
    }


def render_report_pt(results: tuple, metadata: dict) -> str:
    """Renders a Portuguese-language Markdown report grouping results by
    scenario, one decision-trace table plus computational-cost summary per
    (scenario, algorithm) pair, closing with this version's known,
    documented limitations."""
    lines: list[str] = []
    lines.append("# Radio Scheduler — relatório de demonstração (Entrega A)")
    lines.append("")
    lines.append(f"- Commit: `{metadata.get('commit', 'unknown')}`")
    lines.append(f"- Comando: `{metadata.get('command', 'unknown')}`")
    lines.append(f"- Gerado em: {metadata.get('generated_at', 'unknown')}")
    lines.append("")
    lines.append(
        "Executa Round Robin, Proportional Fair e MaxCQI sobre os mesmos cenários "
        "exógenos (pequenos, construídos à mão para ter oráculo verificável — ver "
        "`src/radio_scheduler/demo/scenarios.py`), com estado inicial independente "
        "por algoritmo, e mede custo computacional via `benchmark.benchmark_run()`. "
        "Ver `docs/design.md` seções 1-2 para a distinção entre o componente de "
        "escalonamento e o ambiente experimental que o exercita."
    )
    lines.append("")

    by_scenario: dict[str, list] = {}
    for result in results:
        by_scenario.setdefault(result.scenario_id, []).append(result)

    for scenario_id, scenario_results in by_scenario.items():
        description = scenario_results[0].scenario_description
        lines.append(f"## Cenário: `{scenario_id}`")
        lines.append("")
        lines.append(description)
        lines.append("")
        for result in scenario_results:
            lines.append(f"### {result.scheduler_name} v{result.scheduler_version}")
            lines.append("")
            trace = decisions_trace(result.decisions)
            if not trace:
                lines.append(
                    "Nenhuma decisão de alocação em nenhuma TTI (sem UE elegível "
                    "e/ou sem Resource Block disponível nesse cenário)."
                )
            else:
                lines.append("| TTI | UE | Resource Blocks |")
                lines.append("|---|---|---|")
                for tti_index in sorted(trace):
                    for entry in trace[tti_index]:
                        rbs = ", ".join(entry["resource_block_ids"]) or "—"
                        lines.append(f"| {tti_index} | {entry['ue_id']} | {rbs} |")
            lines.append("")
            b = result.benchmark
            lines.append(
                f"Custo computacional (mediana de {len(b.samples)} repetições): "
                f"{b.median_wall_time_ns / 1e6:.3f} ms tempo de relógio, "
                f"{b.median_cpu_time_ns / 1e6:.3f} ms CPU, "
                f"{b.median_peak_traced_memory_bytes / 1024:.1f} KiB pico de memória."
            )
            lines.append("")

    lines.append("## Limitações conhecidas (v0.1)")
    lines.append("")
    lines.append(LIMITATIONS_PT)
    return "\n".join(lines)
