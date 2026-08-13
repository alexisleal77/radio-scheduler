import random
import unittest
from dataclasses import FrozenInstanceError

from radio_scheduler.scenario_generator.generator import (
    ScenarioGeneratorConfig,
    generate_scenario,
)


def make_config(**overrides):
    defaults = dict(
        seed=42,
        num_ues=2,
        num_ttis=3,
        resource_blocks_per_tti=2,
        qos_class_names=("GBR", "Best Effort"),
    )
    defaults.update(overrides)
    return ScenarioGeneratorConfig(**defaults)


class ScenarioGeneratorConfigValidationTests(unittest.TestCase):
    def test_rejects_non_positive_quantities(self):
        for field in ("num_ues", "num_ttis", "resource_blocks_per_tti"):
            with self.subTest(field=field):
                with self.assertRaises(ValueError):
                    make_config(**{field: 0})

    def test_rejects_empty_qos_class_names(self):
        with self.assertRaises(ValueError):
            make_config(qos_class_names=())

    def test_rejects_empty_or_whitespace_qos_class_name(self):
        for bad in ("", "   "):
            with self.subTest(bad=repr(bad)):
                with self.assertRaises(ValueError):
                    make_config(qos_class_names=("GBR", bad))

    def test_rejects_non_string_qos_class_name(self):
        with self.assertRaises(ValueError):
            make_config(qos_class_names=("GBR", 123))

    def test_rejects_cqi_bounds_outside_0_15(self):
        with self.assertRaises(ValueError):
            make_config(cqi_min=-1)
        with self.assertRaises(ValueError):
            make_config(cqi_max=16)

    def test_rejects_cqi_min_greater_than_cqi_max(self):
        with self.assertRaises(ValueError):
            make_config(cqi_min=10, cqi_max=5)

    def test_rejects_negative_traffic_bounds(self):
        with self.assertRaises(ValueError):
            make_config(traffic_arrival_min_bytes=-1)
        with self.assertRaises(ValueError):
            make_config(traffic_arrival_min_bytes=-5, traffic_arrival_max_bytes=-1)

    def test_rejects_traffic_min_greater_than_max(self):
        with self.assertRaises(ValueError):
            make_config(traffic_arrival_min_bytes=100, traffic_arrival_max_bytes=10)

    def test_config_is_immutable(self):
        config = make_config()
        with self.assertRaises(FrozenInstanceError):
            config.num_ues = 99


class GenerateScenarioTests(unittest.TestCase):
    def test_structural_counts(self):
        config = make_config(num_ues=2, num_ttis=3, resource_blocks_per_tti=2)
        scenario = generate_scenario(config)
        self.assertEqual(len(scenario.ttis), 3)
        self.assertEqual(len(scenario.ues), 2)
        self.assertEqual(len(scenario.resource_blocks), 3 * 2)
        self.assertEqual(len(scenario.channel_qualities), 3 * 2)
        self.assertEqual(len(scenario.traffic_arrivals), 3 * 2)

    def test_determinism_same_config_same_seed(self):
        config = make_config()
        self.assertEqual(generate_scenario(config), generate_scenario(config))

    def test_channel_quality_order_is_tti_outer_ue_inner(self):
        config = make_config(num_ues=2, num_ttis=3)
        scenario = generate_scenario(config)
        expected_pairs = [
            (tti_index, f"ue-{ue_index}")
            for tti_index in range(config.num_ttis)
            for ue_index in range(config.num_ues)
        ]
        actual_pairs = [(cq.tti.index, cq.ue_id) for cq in scenario.channel_qualities]
        self.assertEqual(actual_pairs, expected_pairs)

    def test_traffic_arrival_order_is_tti_outer_ue_inner(self):
        config = make_config(num_ues=2, num_ttis=3)
        scenario = generate_scenario(config)
        expected_pairs = [
            (tti_index, f"ue-{ue_index}")
            for tti_index in range(config.num_ttis)
            for ue_index in range(config.num_ues)
        ]
        actual_pairs = [(ta.tti.index, ta.ue_id) for ta in scenario.traffic_arrivals]
        self.assertEqual(actual_pairs, expected_pairs)

    def test_resource_blocks_grouped_by_tti_and_ordered_within(self):
        config = make_config(num_ttis=3, resource_blocks_per_tti=2)
        scenario = generate_scenario(config)
        expected_ids = [
            f"rb-{tti_index}-{block_index}"
            for tti_index in range(config.num_ttis)
            for block_index in range(config.resource_blocks_per_tti)
        ]
        expected_ttis = [
            tti_index
            for tti_index in range(config.num_ttis)
            for _ in range(config.resource_blocks_per_tti)
        ]
        actual_ids = [rb.block_id for rb in scenario.resource_blocks]
        actual_ttis = [rb.tti.index for rb in scenario.resource_blocks]
        self.assertEqual(actual_ids, expected_ids)
        self.assertEqual(actual_ttis, expected_ttis)

    def test_ue_ids_are_unique_and_follow_convention(self):
        config = make_config(num_ues=4)
        scenario = generate_scenario(config)
        ue_ids = [ue.ue_id for ue in scenario.ues]
        self.assertEqual(len(ue_ids), len(set(ue_ids)))
        self.assertEqual(ue_ids, [f"ue-{i}" for i in range(config.num_ues)])

    def test_resource_block_ids_are_globally_unique(self):
        config = make_config(num_ttis=4, resource_blocks_per_tti=3)
        scenario = generate_scenario(config)
        block_ids = [rb.block_id for rb in scenario.resource_blocks]
        self.assertEqual(len(block_ids), len(set(block_ids)))

    def test_qos_class_round_robin_assignment(self):
        qos_names = ("GBR", "Best Effort", "Voice")
        config = make_config(num_ues=5, qos_class_names=qos_names)
        scenario = generate_scenario(config)
        assigned = [ue.qos_class.name for ue in scenario.ues]
        expected = [qos_names[i % len(qos_names)] for i in range(config.num_ues)]
        self.assertEqual(assigned, expected)

    def test_channel_quality_within_configured_bounds(self):
        config = make_config(num_ues=5, num_ttis=5, cqi_min=3, cqi_max=9)
        scenario = generate_scenario(config)
        for cq in scenario.channel_qualities:
            self.assertGreaterEqual(cq.cqi, config.cqi_min)
            self.assertLessEqual(cq.cqi, config.cqi_max)

    def test_traffic_arrival_within_configured_bounds(self):
        config = make_config(
            num_ues=5,
            num_ttis=5,
            traffic_arrival_min_bytes=100,
            traffic_arrival_max_bytes=200,
        )
        scenario = generate_scenario(config)
        for ta in scenario.traffic_arrivals:
            self.assertGreaterEqual(ta.size_bytes, config.traffic_arrival_min_bytes)
            self.assertLessEqual(ta.size_bytes, config.traffic_arrival_max_bytes)

    def test_cqi_min_equals_cqi_max_forces_single_value(self):
        config = make_config(num_ues=3, num_ttis=3, cqi_min=7, cqi_max=7)
        scenario = generate_scenario(config)
        self.assertTrue(all(cq.cqi == 7 for cq in scenario.channel_qualities))

    def test_traffic_bounds_zero_zero_produce_explicit_zero_records(self):
        config = make_config(
            num_ues=2,
            num_ttis=3,
            traffic_arrival_min_bytes=0,
            traffic_arrival_max_bytes=0,
        )
        scenario = generate_scenario(config)
        self.assertEqual(
            len(scenario.traffic_arrivals), config.num_ttis * config.num_ues
        )
        self.assertTrue(all(ta.size_bytes == 0 for ta in scenario.traffic_arrivals))

    def test_does_not_mutate_global_random_state(self):
        config = make_config()
        state_before = random.getstate()
        generate_scenario(config)
        state_after = random.getstate()
        self.assertEqual(state_before, state_after)


if __name__ == "__main__":
    unittest.main()
