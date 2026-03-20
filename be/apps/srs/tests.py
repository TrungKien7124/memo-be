from datetime import timedelta

from rest_framework import status
from rest_framework.test import APITestCase
from django.test import TestCase
from django.utils import timezone

from apps.app_server.models.implemented.iam_user_model import ROLE_STUDENT, User
from apps.app_server.models.implemented.nfs_flashcard_model import Flashcard
from apps.app_server.models.implemented.nfs_folder_model import Folder
from apps.srs.models.rse_review_session_model import ReviewSession
from apps.srs.models.srs_card_srs_state_model import CardSRSState
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


class SRSContractAPITestCase(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email='srs-user@example.com',
            username='srs-user',
            password='Password@123',
            role=ROLE_STUDENT,
        )
        self.client.force_authenticate(user=self.user)

        self.folder = Folder.objects.create(user=self.user, name='Default Folder')
        self.flashcard = Flashcard.objects.create(
            user=self.user,
            folder=self.folder,
            front_text='hello',
            back_text='xin chao',
        )
        card_srs_state = self.flashcard.srs_state
        card_srs_state.stage = 0
        card_srs_state.interval_days = 1
        card_srs_state.due_date = timezone.now().date()
        card_srs_state.save(update_fields=['stage', 'interval_days', 'due_date', 'updated_at'])

    def test_review_session_create_uses_data_envelope(self):
        response = self.client.post('/api/rse/review-sessions/', {}, format='json')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn('data', response.data)
        self.assertIn('id', response.data['data'])

    def test_review_session_list_uses_data_meta_envelope(self):
        ReviewSession.objects.create(user=self.user)
        response = self.client.get('/api/rse/review-sessions/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('data', response.data)
        self.assertIn('meta', response.data)
        self.assertIsInstance(response.data['data'], list)

    def test_review_session_patch_uses_data_envelope(self):
        session = ReviewSession.objects.create(user=self.user)
        response = self.client.patch(f'/api/rse/review-sessions/{session.id}/', {}, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('data', response.data)
        self.assertIsNotNone(response.data['data']['ended_at'])

    def test_card_review_create_uses_data_envelope(self):
        session = ReviewSession.objects.create(user=self.user)
        response = self.client.post(
            '/api/rse/card-review-logs/',
            {
                'session': str(session.id),
                'card': str(self.flashcard.id),
                'choice': 'GOOD',
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn('data', response.data)
        self.assertEqual(response.data['data']['choice'], 'GOOD')

    def test_due_card_list_uses_data_meta_envelope(self):
        response = self.client.get('/api/srs/card-srs/', {'due_date__lte': timezone.now().date().isoformat()})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('data', response.data)
        self.assertIn('meta', response.data)
        self.assertIsInstance(response.data['data'], list)
