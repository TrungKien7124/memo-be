from datetime import timedelta

from django.test import TestCase
from django.utils import timezone

from apps.srs.services.srs_review_service import calculate_srs_update


class SRSAlgorithmTest(TestCase):
    def test_easy_increases_stage_by_2_and_multiplies_interval(self):
        new_stage, new_interval, new_due = calculate_srs_update(
            current_stage=1, current_interval=4, choice='EASY'
        )
        self.assertEqual(new_stage, 3)
        self.assertEqual(new_interval, 10)
        expected_due = timezone.now().date() + timedelta(days=10)
        self.assertEqual(new_due, expected_due)

    def test_good_increases_stage_by_1_and_multiplies_interval(self):
        new_stage, new_interval, new_due = calculate_srs_update(
            current_stage=2, current_interval=4, choice='GOOD'
        )
        self.assertEqual(new_stage, 3)
        self.assertEqual(new_interval, 6)
        expected_due = timezone.now().date() + timedelta(days=6)
        self.assertEqual(new_due, expected_due)

    def test_hard_resets_stage_and_sets_interval_to_1(self):
        new_stage, new_interval, new_due = calculate_srs_update(
            current_stage=5, current_interval=30, choice='HARD'
        )
        self.assertEqual(new_stage, 0)
        self.assertEqual(new_interval, 1)
        expected_due = timezone.now().date() + timedelta(days=1)
        self.assertEqual(new_due, expected_due)

    def test_easy_from_initial_state(self):
        new_stage, new_interval, _ = calculate_srs_update(
            current_stage=0, current_interval=1, choice='EASY'
        )
        self.assertEqual(new_stage, 2)
        self.assertEqual(new_interval, 3)

    def test_good_from_initial_state(self):
        new_stage, new_interval, _ = calculate_srs_update(
            current_stage=0, current_interval=1, choice='GOOD'
        )
        self.assertEqual(new_stage, 1)
        self.assertEqual(new_interval, 2)

    def test_interval_minimum_is_1(self):
        new_stage, new_interval, _ = calculate_srs_update(
            current_stage=0, current_interval=0, choice='GOOD'
        )
        self.assertGreaterEqual(new_interval, 1)
