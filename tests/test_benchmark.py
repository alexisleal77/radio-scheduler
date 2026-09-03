import gc
import os
import platform
import tracemalloc
import unittest
from dataclasses import FrozenInstanceError, dataclass, fields
from unittest.mock import patch

import radio_scheduler.benchmark.measurement as measurement
from radio_scheduler.benchmark.measurement import (
    BenchmarkResult,
    RunMeasurement,
    benchmark_run,
    measure_run,
)
from radio_scheduler.domain import (
    ChannelQuality,
    QoSClass,
    ResourceBlock,
    Scenario,
    Scheduler,
    TrafficArrival,
    TTI,
    UE,
)
from radio_scheduler.reference_implementations import MaxCQI, ProportionalFair, RoundRobin
from radio_scheduler.scenario_generator import ScenarioGeneratorConfig, generate_scenario
from radio_scheduler.scheduling_interface import SchedulingStepResult
from radio_scheduler.simulation_loop import run as run_simulation

RUN_MEASUREMENT_FIELDS = (
    ("wall_time_ns", int),
    ("cpu_time_ns", int),
    ("peak_traced_memory_bytes", int),
    ("scenario_seed", int),
    ("scenario_num_ttis", int),
    ("scenario_num_ues", int),
    ("scenario_resource_blocks_per_tti", tuple[int, ...]),
    ("scheduler_name", str),
    ("scheduler_version", str),
    ("python_implementation", str),
    ("python_version", str),
    ("platform", str),
    ("machine", str),
    ("processor", str),
    ("cpu_count", int | None),
)

BENCHMARK_RESULT_FIELDS = (
    ("samples", tuple[RunMeasurement, ...]),
    ("median_wall_time_ns", float),
    ("median_cpu_time_ns", float),
    ("median_peak_traced_memory_bytes", float),
    ("scenario_seed", int),
    ("scenario_num_ttis", int),
    ("scenario_num_ues", int),
    ("scenario_resource_blocks_per_tti", tuple[int, ...]),
    ("scheduler_name", str),
    ("scheduler_version", str),
    ("python_implementation", str),
    ("python_version", str),
    ("platform", str),
    ("machine", str),
    ("processor", str),
    ("cpu_count", int | None),
)

# Radio-performance fields this module must never carry (ADR-010, Explicit
# Exclusions) — the exact field names of domain.SchedulingPerformanceMetric.
SCHEDULING_PERFORMANCE_METRIC_FIELDS = (
    "throughput_bps",
    "fairness_index",
    "average_latency_ttis",
)


def make_run_measurement(
    wall_time_ns=1_000,
    cpu_time_ns=900,
    peak_traced_memory_bytes=2_048,
    scenario_seed=42,
    scenario_num_ttis=3,
    scenario_num_ues=2,
    scenario_resource_blocks_per_tti=(1, 1, 1),
    scheduler_name="RoundRobin",
    scheduler_version="0.1",
    python_implementation="CPython",
    python_version="3.14.0",
    platform="Linux-6.17.0-x86_64",
    machine="x86_64",
    processor="",
    cpu_count=8,
):
    return RunMeasurement(
        wall_time_ns=wall_time_ns,
        cpu_time_ns=cpu_time_ns,
        peak_traced_memory_bytes=peak_traced_memory_bytes,
        scenario_seed=scenario_seed,
        scenario_num_ttis=scenario_num_ttis,
        scenario_num_ues=scenario_num_ues,
        scenario_resource_blocks_per_tti=scenario_resource_blocks_per_tti,
        scheduler_name=scheduler_name,
        scheduler_version=scheduler_version,
        python_implementation=python_implementation,
        python_version=python_version,
        platform=platform,
        machine=machine,
        processor=processor,
        cpu_count=cpu_count,
    )


class RunMeasurementFieldShapeTests(unittest.TestCase):
    def test_field_names_and_order_match_specification(self):
        actual = tuple(f.name for f in fields(RunMeasurement))
        expected = tuple(name for name, _ in RUN_MEASUREMENT_FIELDS)
        self.assertEqual(actual, expected)

    def test_field_types_match_specification(self):
        actual = {f.name: f.type for f in fields(RunMeasurement)}
        for name, expected_type in RUN_MEASUREMENT_FIELDS:
            self.assertEqual(actual[name], expected_type, msg=f"field {name!r}")

    def test_no_scheduling_performance_metric_fields(self):
        field_names = {f.name for f in fields(RunMeasurement)}
        for forbidden in SCHEDULING_PERFORMANCE_METRIC_FIELDS:
            self.assertNotIn(forbidden, field_names)

    def test_is_immutable(self):
        measurement = make_run_measurement()
        with self.assertRaises(FrozenInstanceError):
            measurement.wall_time_ns = 0

    def test_time_and_memory_samples_are_int(self):
        measurement = make_run_measurement(
            wall_time_ns=123, cpu_time_ns=456, peak_traced_memory_bytes=789
        )
        self.assertIsInstance(measurement.wall_time_ns, int)
        self.assertIsInstance(measurement.cpu_time_ns, int)
        self.assertIsInstance(measurement.peak_traced_memory_bytes, int)

    def test_cpu_count_accepts_int(self):
        measurement = make_run_measurement(cpu_count=16)
        self.assertEqual(measurement.cpu_count, 16)

    def test_cpu_count_accepts_none(self):
        measurement = make_run_measurement(cpu_count=None)
        self.assertIsNone(measurement.cpu_count)

    def test_scenario_resource_blocks_per_tti_preserves_non_uniform_tuple(self):
        measurement = make_run_measurement(scenario_resource_blocks_per_tti=(1, 3, 2))
        self.assertEqual(measurement.scenario_resource_blocks_per_tti, (1, 3, 2))
        self.assertIsInstance(measurement.scenario_resource_blocks_per_tti, tuple)


class BenchmarkResultFieldShapeTests(unittest.TestCase):
    def test_field_names_and_order_match_specification(self):
        actual = tuple(f.name for f in fields(BenchmarkResult))
        expected = tuple(name for name, _ in BENCHMARK_RESULT_FIELDS)
        self.assertEqual(actual, expected)

    def test_field_types_match_specification(self):
        actual = {f.name: f.type for f in fields(BenchmarkResult)}
        for name, expected_type in BENCHMARK_RESULT_FIELDS:
            self.assertEqual(actual[name], expected_type, msg=f"field {name!r}")

    def test_no_scheduling_performance_metric_fields(self):
        field_names = {f.name for f in fields(BenchmarkResult)}
        for forbidden in SCHEDULING_PERFORMANCE_METRIC_FIELDS:
            self.assertNotIn(forbidden, field_names)

    def test_is_immutable(self):
        result = BenchmarkResult(
            samples=(),
            median_wall_time_ns=0.0,
            median_cpu_time_ns=0.0,
            median_peak_traced_memory_bytes=0.0,
            scenario_seed=1,
            scenario_num_ttis=1,
            scenario_num_ues=1,
            scenario_resource_blocks_per_tti=(1,),
            scheduler_name="RoundRobin",
            scheduler_version="0.1",
            python_implementation="CPython",
            python_version="3.14.0",
            platform="Linux",
            machine="x86_64",
            processor="",
            cpu_count=4,
        )
        with self.assertRaises(FrozenInstanceError):
            result.median_wall_time_ns = 1.0

    def test_stores_all_samples_in_full(self):
        samples = tuple(
            make_run_measurement(wall_time_ns=n) for n in (100, 200, 300, 400, 500)
        )
        result = BenchmarkResult(
            samples=samples,
            median_wall_time_ns=300.0,
            median_cpu_time_ns=300.0,
            median_peak_traced_memory_bytes=300.0,
            scenario_seed=1,
            scenario_num_ttis=1,
            scenario_num_ues=1,
            scenario_resource_blocks_per_tti=(1,),
            scheduler_name="RoundRobin",
            scheduler_version="0.1",
            python_implementation="CPython",
            python_version="3.14.0",
            platform="Linux",
            machine="x86_64",
            processor="",
            cpu_count=4,
        )
        self.assertEqual(result.samples, samples)
        self.assertEqual(len(result.samples), 5)
        self.assertEqual(
            tuple(sample.wall_time_ns for sample in result.samples),
            (100, 200, 300, 400, 500),
        )

    def test_medians_accept_float_values(self):
        result = BenchmarkResult(
            samples=(),
            median_wall_time_ns=123.5,
            median_cpu_time_ns=456.5,
            median_peak_traced_memory_bytes=789.5,
            scenario_seed=1,
            scenario_num_ttis=1,
            scenario_num_ues=1,
            scenario_resource_blocks_per_tti=(1,),
            scheduler_name="RoundRobin",
            scheduler_version="0.1",
            python_implementation="CPython",
            python_version="3.14.0",
            platform="Linux",
            machine="x86_64",
            processor="",
            cpu_count=4,
        )
        self.assertIsInstance(result.median_wall_time_ns, float)
        self.assertIsInstance(result.median_cpu_time_ns, float)
        self.assertIsInstance(result.median_peak_traced_memory_bytes, float)
        self.assertEqual(result.median_wall_time_ns, 123.5)
        self.assertEqual(result.median_cpu_time_ns, 456.5)
        self.assertEqual(result.median_peak_traced_memory_bytes, 789.5)

    def test_cpu_count_accepts_int_and_none(self):
        for value in (8, None):
            result = BenchmarkResult(
                samples=(),
                median_wall_time_ns=0.0,
                median_cpu_time_ns=0.0,
                median_peak_traced_memory_bytes=0.0,
                scenario_seed=1,
                scenario_num_ttis=1,
                scenario_num_ues=1,
                scenario_resource_blocks_per_tti=(1,),
                scheduler_name="RoundRobin",
                scheduler_version="0.1",
                python_implementation="CPython",
                python_version="3.14.0",
                platform="Linux",
                machine="x86_64",
                processor="",
                cpu_count=value,
            )
            self.assertEqual(result.cpu_count, value)

    def test_scenario_resource_blocks_per_tti_preserves_non_uniform_tuple(self):
        result = BenchmarkResult(
            samples=(),
            median_wall_time_ns=0.0,
            median_cpu_time_ns=0.0,
            median_peak_traced_memory_bytes=0.0,
            scenario_seed=1,
            scenario_num_ttis=3,
            scenario_num_ues=1,
            scenario_resource_blocks_per_tti=(1, 3, 2),
            scheduler_name="RoundRobin",
            scheduler_version="0.1",
            python_implementation="CPython",
            python_version="3.14.0",
            platform="Linux",
            machine="x86_64",
            processor="",
            cpu_count=4,
        )
        self.assertEqual(result.scenario_resource_blocks_per_tti, (1, 3, 2))
        self.assertIsInstance(result.scenario_resource_blocks_per_tti, tuple)


def make_scenario(
    num_ues=2,
    num_ttis=2,
    resource_blocks_per_tti=1,
    cqi=10,
    arrival_size_bytes=100,
    seed=0,
):
    """Hand-built Scenario (not via generate_scenario) with uniform
    per-TTI Resource Block counts, for tests where the exact Resource
    Block layout does not matter."""
    ttis = tuple(TTI(index=i) for i in range(num_ttis))
    ues = tuple(
        UE(ue_id=f"ue-{i}", qos_class=QoSClass(name="GBR")) for i in range(num_ues)
    )
    resource_blocks = tuple(
        ResourceBlock(tti=tti, block_id=f"rb-{tti.index}-{j}")
        for tti in ttis
        for j in range(resource_blocks_per_tti)
    )
    channel_qualities = tuple(
        ChannelQuality(tti=tti, ue_id=ue.ue_id, cqi=cqi) for tti in ttis for ue in ues
    )
    traffic_arrivals = tuple(
        TrafficArrival(tti=tti, ue_id=ue.ue_id, size_bytes=arrival_size_bytes)
        for tti in ttis
        for ue in ues
    )
    return Scenario(
        seed=seed,
        ttis=ttis,
        ues=ues,
        resource_blocks=resource_blocks,
        channel_qualities=channel_qualities,
        traffic_arrivals=traffic_arrivals,
    )


def make_scenario_with_resource_block_counts(counts, seed=0):
    """Hand-built Scenario with exactly `counts[i]` ResourceBlocks at TTI
    i, for tests exercising non-uniform Resource-Block-per-TTI provenance."""
    ttis = tuple(TTI(index=i) for i in range(len(counts)))
    ues = (UE(ue_id="ue-0", qos_class=QoSClass(name="GBR")),)
    resource_blocks = tuple(
        ResourceBlock(tti=tti, block_id=f"rb-{tti.index}-{j}")
        for tti, count in zip(ttis, counts)
        for j in range(count)
    )
    channel_qualities = tuple(
        ChannelQuality(tti=tti, ue_id=ue.ue_id, cqi=10) for tti in ttis for ue in ues
    )
    traffic_arrivals = tuple(
        TrafficArrival(tti=tti, ue_id=ue.ue_id, size_bytes=100)
        for tti in ttis
        for ue in ues
    )
    return Scenario(
        seed=seed,
        ttis=ttis,
        ues=ues,
        resource_blocks=resource_blocks,
        channel_qualities=channel_qualities,
        traffic_arrivals=traffic_arrivals,
    )


@dataclass(frozen=True)
class _CountingState:
    pass


class _CountingAlgorithm:
    """Test double satisfying SchedulingAlgorithm: counts calls to
    initial_state()/allocate() without producing any decisions."""

    def __init__(self):
        self.initial_state_calls = 0
        self.allocate_calls = 0

    def initial_state(self):
        self.initial_state_calls += 1
        return _CountingState()

    def allocate(self, observable_state, scheduler_state):
        self.allocate_calls += 1
        return SchedulingStepResult(decisions=(), scheduler_state=scheduler_state)


class _TracemallocStartingAlgorithm:
    """Test double: starts tracemalloc as a side effect of allocate(), to
    simulate external tracing being activated between measure_run()'s two
    passes."""

    def initial_state(self):
        return _CountingState()

    def allocate(self, observable_state, scheduler_state):
        if not tracemalloc.is_tracing():
            tracemalloc.start()
        return SchedulingStepResult(decisions=(), scheduler_state=scheduler_state)


class _FailingOnSecondRunAlgorithm:
    """Test double: succeeds through every TTI of measure_run()'s first
    execution (pass a) and raises on the first TTI of the second (pass
    b), to exercise tracemalloc.stop() running via `finally` after a
    failed memory pass."""

    def __init__(self, num_ttis):
        self._num_ttis = num_ttis
        self.allocate_calls = 0

    def initial_state(self):
        return _CountingState()

    def allocate(self, observable_state, scheduler_state):
        self.allocate_calls += 1
        if self.allocate_calls > self._num_ttis:
            raise RuntimeError("boom: simulated failure during pass (b)")
        return SchedulingStepResult(decisions=(), scheduler_state=scheduler_state)


class _GCStateRecordingAlgorithm:
    """Test double: records gc.isenabled() every time allocate() is
    called, to verify garbage collection remains enabled during measured
    executions of simulation_loop.run()."""

    def __init__(self):
        self.gc_enabled_observations = []

    def initial_state(self):
        return _CountingState()

    def allocate(self, observable_state, scheduler_state):
        self.gc_enabled_observations.append(gc.isenabled())
        return SchedulingStepResult(decisions=(), scheduler_state=scheduler_state)


class MeasureRunBehaviorTests(unittest.TestCase):
    def test_measure_run_executes_simulation_loop_exactly_twice(self):
        scenario = make_scenario()
        algorithm = RoundRobin()
        scheduler = Scheduler(name="RoundRobin", version="0.1")
        with patch.object(measurement, "run", wraps=measurement.run) as mock_run:
            measure_run(scenario, scheduler, algorithm)
        self.assertEqual(mock_run.call_count, 2)

    def test_measure_run_rejects_already_active_tracemalloc_at_entry(self):
        scenario = make_scenario()
        algorithm = _CountingAlgorithm()
        scheduler = Scheduler(name="Counting", version="0.1")
        tracemalloc.start()
        try:
            with self.assertRaises(RuntimeError):
                measure_run(scenario, scheduler, algorithm)
        finally:
            tracemalloc.stop()
        self.assertEqual(algorithm.initial_state_calls, 0)
        self.assertEqual(algorithm.allocate_calls, 0)

    def test_measure_run_rejects_tracemalloc_activated_between_passes(self):
        scenario = make_scenario(num_ttis=1)
        algorithm = _TracemallocStartingAlgorithm()
        scheduler = Scheduler(name="TracemallocStarting", version="0.1")
        with patch.object(measurement, "run", wraps=measurement.run) as mock_run:
            try:
                with self.assertRaises(RuntimeError):
                    measure_run(scenario, scheduler, algorithm)
                self.assertEqual(mock_run.call_count, 1)
                self.assertTrue(tracemalloc.is_tracing())
            finally:
                if tracemalloc.is_tracing():
                    tracemalloc.stop()

    def test_tracemalloc_stopped_after_successful_measurement(self):
        scenario = make_scenario()
        algorithm = RoundRobin()
        scheduler = Scheduler(name="RoundRobin", version="0.1")
        self.assertFalse(tracemalloc.is_tracing())
        measure_run(scenario, scheduler, algorithm)
        self.assertFalse(tracemalloc.is_tracing())

    def test_tracemalloc_stopped_after_failed_measurement(self):
        scenario = make_scenario(num_ttis=2)
        algorithm = _FailingOnSecondRunAlgorithm(num_ttis=2)
        scheduler = Scheduler(name="Failing", version="0.1")
        self.assertFalse(tracemalloc.is_tracing())
        with self.assertRaises(RuntimeError):
            measure_run(scenario, scheduler, algorithm)
        self.assertFalse(tracemalloc.is_tracing())

    def test_gc_collect_runs_before_each_pass(self):
        scenario = make_scenario()
        algorithm = RoundRobin()
        scheduler = Scheduler(name="RoundRobin", version="0.1")
        events = []
        original_gc_collect = measurement.gc.collect
        original_run = measurement.run

        def recording_gc_collect(*args, **kwargs):
            events.append("gc.collect")
            return original_gc_collect(*args, **kwargs)

        def recording_run(*args, **kwargs):
            events.append("run")
            return original_run(*args, **kwargs)

        with patch.object(
            measurement.gc, "collect", side_effect=recording_gc_collect
        ) as mock_collect, patch.object(
            measurement, "run", side_effect=recording_run
        ) as mock_run:
            measure_run(scenario, scheduler, algorithm)

        self.assertEqual(mock_collect.call_count, 2)
        self.assertEqual(mock_run.call_count, 2)
        self.assertEqual(events, ["gc.collect", "run", "gc.collect", "run"])

    def test_garbage_collection_remains_enabled_during_measured_calls(self):
        scenario = make_scenario()
        algorithm = _GCStateRecordingAlgorithm()
        scheduler = Scheduler(name="GCRecording", version="0.1")
        self.assertTrue(gc.isenabled())
        measure_run(scenario, scheduler, algorithm)
        self.assertTrue(algorithm.gc_enabled_observations)
        self.assertTrue(all(algorithm.gc_enabled_observations))

    def test_run_measurement_fields_are_non_negative_integers(self):
        scenario = make_scenario()
        algorithm = RoundRobin()
        scheduler = Scheduler(name="RoundRobin", version="0.1")
        result = measure_run(scenario, scheduler, algorithm)
        for value in (
            result.wall_time_ns,
            result.cpu_time_ns,
            result.peak_traced_memory_bytes,
        ):
            self.assertIsInstance(value, int)
            self.assertGreaterEqual(value, 0)

    def test_measure_run_provenance_fields_populated_correctly(self):
        config = ScenarioGeneratorConfig(
            seed=7,
            num_ues=3,
            num_ttis=4,
            resource_blocks_per_tti=2,
            qos_class_names=("GBR",),
        )
        scenario = generate_scenario(config)
        algorithm = RoundRobin()
        scheduler = Scheduler(name="RoundRobin", version="0.1")
        result = measure_run(scenario, scheduler, algorithm)
        self.assertEqual(result.scenario_seed, 7)
        self.assertEqual(result.scenario_num_ttis, 4)
        self.assertEqual(result.scenario_num_ues, 3)
        self.assertEqual(result.scenario_resource_blocks_per_tti, (2, 2, 2, 2))
        self.assertEqual(result.scheduler_name, "RoundRobin")
        self.assertEqual(result.scheduler_version, "0.1")
        self.assertEqual(
            result.python_implementation, platform.python_implementation()
        )
        self.assertEqual(result.python_version, platform.python_version())
        self.assertEqual(result.platform, platform.platform())
        self.assertEqual(result.machine, platform.machine())
        self.assertEqual(result.processor, platform.processor())
        self.assertEqual(result.cpu_count, os.cpu_count())

    def test_measure_run_scenario_resource_blocks_per_tti_reflects_non_uniform_counts(
        self,
    ):
        scenario = make_scenario_with_resource_block_counts((1, 3, 2))
        algorithm = RoundRobin()
        scheduler = Scheduler(name="RoundRobin", version="0.1")
        result = measure_run(scenario, scheduler, algorithm)
        self.assertEqual(result.scenario_resource_blocks_per_tti, (1, 3, 2))

    def test_scheduler_identity_mismatch_is_not_verified(self):
        scenario = make_scenario()
        algorithm = RoundRobin()
        mismatched_scheduler = Scheduler(name="NotRoundRobin", version="99.9")
        result = measure_run(scenario, mismatched_scheduler, algorithm)
        self.assertEqual(result.scheduler_name, "NotRoundRobin")
        self.assertEqual(result.scheduler_version, "99.9")

    def test_measure_run_does_not_alter_decisions_for_reference_algorithms(self):
        config = ScenarioGeneratorConfig(
            seed=11,
            num_ues=3,
            num_ttis=3,
            resource_blocks_per_tti=2,
            qos_class_names=("GBR", "Best Effort"),
        )
        scenario = generate_scenario(config)
        for algorithm, name in (
            (RoundRobin(), "RoundRobin"),
            (ProportionalFair(), "ProportionalFair"),
            (MaxCQI(), "MaxCQI"),
        ):
            with self.subTest(algorithm=name):
                baseline = run_simulation(scenario, algorithm)
                measure_run(scenario, Scheduler(name=name, version="0.1"), algorithm)
                after = run_simulation(scenario, algorithm)
                self.assertEqual(after.decisions, baseline.decisions)


class BenchmarkRunBehaviorTests(unittest.TestCase):
    def test_benchmark_run_rejects_zero_and_negative_repetitions(self):
        scenario = make_scenario()
        algorithm = RoundRobin()
        scheduler = Scheduler(name="RoundRobin", version="0.1")
        for repetitions in (0, -1, -5):
            with self.subTest(repetitions=repetitions):
                with patch.object(measurement, "run") as mock_run, patch.object(
                    measurement, "measure_run"
                ) as mock_measure_run:
                    with self.assertRaises(ValueError):
                        benchmark_run(
                            scenario, scheduler, algorithm, repetitions=repetitions
                        )
                mock_run.assert_not_called()
                mock_measure_run.assert_not_called()

    def test_benchmark_run_default_repetitions_is_ten(self):
        scenario = make_scenario()
        algorithm = RoundRobin()
        scheduler = Scheduler(name="RoundRobin", version="0.1")
        fake_samples = [make_run_measurement(wall_time_ns=n) for n in range(10)]
        with patch.object(measurement, "run"), patch.object(
            measurement, "measure_run", side_effect=fake_samples
        ) as mock_measure_run:
            result = benchmark_run(scenario, scheduler, algorithm)
        self.assertEqual(mock_measure_run.call_count, 10)
        self.assertEqual(len(result.samples), 10)

    def test_benchmark_run_executes_exactly_one_warmup(self):
        scenario = make_scenario()
        algorithm = RoundRobin()
        scheduler = Scheduler(name="RoundRobin", version="0.1")
        fake_samples = [make_run_measurement(wall_time_ns=n) for n in range(3)]
        with patch.object(measurement, "run") as mock_run, patch.object(
            measurement, "measure_run", side_effect=fake_samples
        ):
            benchmark_run(scenario, scheduler, algorithm, repetitions=3)
        self.assertEqual(mock_run.call_count, 1)

    def test_benchmark_run_calls_measure_run_exactly_repetitions_times(self):
        scenario = make_scenario()
        algorithm = RoundRobin()
        scheduler = Scheduler(name="RoundRobin", version="0.1")
        for repetitions in (1, 3, 7):
            with self.subTest(repetitions=repetitions):
                fake_samples = [
                    make_run_measurement(wall_time_ns=n) for n in range(repetitions)
                ]
                with patch.object(measurement, "run"), patch.object(
                    measurement, "measure_run", side_effect=fake_samples
                ) as mock_measure_run:
                    benchmark_run(
                        scenario, scheduler, algorithm, repetitions=repetitions
                    )
                self.assertEqual(mock_measure_run.call_count, repetitions)

    def test_benchmark_run_executes_simulation_loop_1_plus_2n_times(self):
        scenario = make_scenario(num_ues=2, num_ttis=1, resource_blocks_per_tti=1)
        algorithm = RoundRobin()
        scheduler = Scheduler(name="RoundRobin", version="0.1")
        for repetitions in (1, 3, 5):
            with self.subTest(repetitions=repetitions):
                with patch.object(
                    measurement, "run", wraps=measurement.run
                ) as mock_run:
                    benchmark_run(
                        scenario, scheduler, algorithm, repetitions=repetitions
                    )
                self.assertEqual(mock_run.call_count, 1 + 2 * repetitions)

    def test_benchmark_run_executes_simulation_loop_21_times_for_default_repetitions(
        self,
    ):
        scenario = make_scenario(num_ues=2, num_ttis=1, resource_blocks_per_tti=1)
        algorithm = RoundRobin()
        scheduler = Scheduler(name="RoundRobin", version="0.1")
        with patch.object(measurement, "run", wraps=measurement.run) as mock_run:
            benchmark_run(scenario, scheduler, algorithm)
        self.assertEqual(mock_run.call_count, 21)

    def test_warmup_result_not_included_in_samples_or_medians(self):
        scenario = make_scenario()
        algorithm = RoundRobin()
        scheduler = Scheduler(name="RoundRobin", version="0.1")
        fake_samples = [
            make_run_measurement(wall_time_ns=v)
            for v in (1_000_000, 2_000_000, 3_000_000)
        ]
        with patch.object(measurement, "run") as mock_run, patch.object(
            measurement, "measure_run", side_effect=fake_samples
        ):
            result = benchmark_run(scenario, scheduler, algorithm, repetitions=3)
        self.assertEqual(result.samples, tuple(fake_samples))
        self.assertEqual(result.median_wall_time_ns, 2_000_000.0)
        mock_run.assert_called_once()

    def test_len_samples_equals_repetitions_for_multiple_values(self):
        scenario = make_scenario()
        algorithm = RoundRobin()
        scheduler = Scheduler(name="RoundRobin", version="0.1")
        for repetitions in (1, 2, 5, 10):
            with self.subTest(repetitions=repetitions):
                fake_samples = [
                    make_run_measurement(wall_time_ns=n) for n in range(repetitions)
                ]
                with patch.object(measurement, "run"), patch.object(
                    measurement, "measure_run", side_effect=fake_samples
                ):
                    result = benchmark_run(
                        scenario, scheduler, algorithm, repetitions=repetitions
                    )
                self.assertEqual(len(result.samples), repetitions)

    def test_samples_preserve_order_and_identity_from_measure_run(self):
        scenario = make_scenario()
        algorithm = RoundRobin()
        scheduler = Scheduler(name="RoundRobin", version="0.1")
        fake_samples = [make_run_measurement(wall_time_ns=n) for n in (5, 1, 9, 3)]
        with patch.object(measurement, "run"), patch.object(
            measurement, "measure_run", side_effect=fake_samples
        ):
            result = benchmark_run(scenario, scheduler, algorithm, repetitions=4)
        self.assertEqual(result.samples, tuple(fake_samples))
        for expected, actual in zip(fake_samples, result.samples):
            self.assertIs(expected, actual)

    def test_benchmark_run_median_correct_for_even_repetitions(self):
        scenario = make_scenario()
        algorithm = RoundRobin()
        scheduler = Scheduler(name="RoundRobin", version="0.1")
        values = (100, 200, 300, 400)
        fake_samples = [
            make_run_measurement(
                wall_time_ns=v, cpu_time_ns=v * 2, peak_traced_memory_bytes=v * 3
            )
            for v in values
        ]
        with patch.object(measurement, "run"), patch.object(
            measurement, "measure_run", side_effect=fake_samples
        ):
            result = benchmark_run(scenario, scheduler, algorithm, repetitions=4)
        self.assertEqual(result.median_wall_time_ns, 250.0)
        self.assertEqual(result.median_cpu_time_ns, 500.0)
        self.assertEqual(result.median_peak_traced_memory_bytes, 750.0)
        self.assertIsInstance(result.median_wall_time_ns, float)
        self.assertIsInstance(result.median_cpu_time_ns, float)
        self.assertIsInstance(result.median_peak_traced_memory_bytes, float)

    def test_benchmark_run_median_correct_for_odd_repetitions(self):
        scenario = make_scenario()
        algorithm = RoundRobin()
        scheduler = Scheduler(name="RoundRobin", version="0.1")
        values = (100, 200, 300)
        fake_samples = [
            make_run_measurement(
                wall_time_ns=v, cpu_time_ns=v * 2, peak_traced_memory_bytes=v * 3
            )
            for v in values
        ]
        with patch.object(measurement, "run"), patch.object(
            measurement, "measure_run", side_effect=fake_samples
        ):
            result = benchmark_run(scenario, scheduler, algorithm, repetitions=3)
        # statistics.median([100, 200, 300]) returns the middle element
        # itself (int 200) — benchmark_run must still convert it to float.
        self.assertEqual(result.median_wall_time_ns, 200.0)
        self.assertEqual(result.median_cpu_time_ns, 400.0)
        self.assertEqual(result.median_peak_traced_memory_bytes, 600.0)
        self.assertIsInstance(result.median_wall_time_ns, float)
        self.assertIsInstance(result.median_cpu_time_ns, float)
        self.assertIsInstance(result.median_peak_traced_memory_bytes, float)

    def test_benchmark_result_provenance_matches_samples_provenance(self):
        scenario = make_scenario(num_ues=2, num_ttis=1, resource_blocks_per_tti=1)
        algorithm = RoundRobin()
        scheduler = Scheduler(name="RoundRobin", version="0.1")
        result = benchmark_run(scenario, scheduler, algorithm, repetitions=2)
        provenance_fields = (
            "scenario_seed",
            "scenario_num_ttis",
            "scenario_num_ues",
            "scenario_resource_blocks_per_tti",
            "scheduler_name",
            "scheduler_version",
            "python_implementation",
            "python_version",
            "platform",
            "machine",
            "processor",
            "cpu_count",
        )
        for field in provenance_fields:
            with self.subTest(field=field):
                for sample in result.samples:
                    self.assertEqual(getattr(result, field), getattr(sample, field))

    def test_benchmark_run_propagates_warmup_exception_without_calling_measure_run(
        self,
    ):
        scenario = make_scenario()
        algorithm = RoundRobin()
        scheduler = Scheduler(name="RoundRobin", version="0.1")
        with patch.object(
            measurement, "run", side_effect=RuntimeError("boom: warm-up failure")
        ) as mock_run, patch.object(measurement, "measure_run") as mock_measure_run:
            with self.assertRaises(RuntimeError):
                benchmark_run(scenario, scheduler, algorithm, repetitions=3)
        self.assertEqual(mock_run.call_count, 1)
        mock_measure_run.assert_not_called()

    def test_benchmark_run_propagates_measure_run_exception_without_partial_result(
        self,
    ):
        scenario = make_scenario()
        algorithm = RoundRobin()
        scheduler = Scheduler(name="RoundRobin", version="0.1")
        good_samples = [make_run_measurement(wall_time_ns=n) for n in (100, 200)]
        side_effect = good_samples + [RuntimeError("boom: failing repetition")]
        with patch.object(measurement, "run") as mock_run, patch.object(
            measurement, "measure_run", side_effect=side_effect
        ) as mock_measure_run:
            with self.assertRaises(RuntimeError):
                benchmark_run(scenario, scheduler, algorithm, repetitions=3)
        self.assertEqual(mock_run.call_count, 1)
        self.assertEqual(mock_measure_run.call_count, 3)

    def test_benchmark_run_end_to_end_for_reference_algorithms(self):
        config = ScenarioGeneratorConfig(
            seed=13,
            num_ues=3,
            num_ttis=2,
            resource_blocks_per_tti=2,
            qos_class_names=("GBR", "Best Effort"),
        )
        scenario = generate_scenario(config)
        for algorithm, name in (
            (RoundRobin(), "RoundRobin"),
            (ProportionalFair(), "ProportionalFair"),
            (MaxCQI(), "MaxCQI"),
        ):
            with self.subTest(algorithm=name):
                result = benchmark_run(
                    scenario,
                    Scheduler(name=name, version="0.1"),
                    algorithm,
                    repetitions=2,
                )
                self.assertEqual(len(result.samples), 2)
                self.assertIsInstance(result.median_wall_time_ns, float)
                self.assertIsInstance(result.median_cpu_time_ns, float)
                self.assertIsInstance(result.median_peak_traced_memory_bytes, float)


if __name__ == "__main__":
    unittest.main()
