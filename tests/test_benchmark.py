import unittest
from dataclasses import FrozenInstanceError, fields

from radio_scheduler.benchmark.measurement import BenchmarkResult, RunMeasurement

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


if __name__ == "__main__":
    unittest.main()
