from datetime import timedelta

from rest_framework import status
from rest_framework.test import APITestCase
from django.test import TestCase
from django.utils import timezone

from apps.app_server.models.implemented.iam_user_model import ROLE_STUDENT, User
from apps.app_server.models.implemented.nfs_flashcard_model import Flashcard
from apps.app_server.models.implemented.nfs_folder_model import Folder
from apps.app_server.services.gms_xp_service import XP_AMOUNTS
from apps.srs.models.rse_review_session_model import ReviewSession
from apps.srs.models.rse_card_review_log_model import CardReviewLog
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

    def test_due_card_list_includes_real_flashcard_display_data(self):
        response = self.client.get('/api/srs/card-srs/', {'due_date__lte': timezone.now().date().isoformat()})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        payload = response.data['data']
        self.assertGreaterEqual(len(payload), 1)
        first = payload[0]

        self.assertIn('card_detail', first)
        self.assertEqual(first['card_detail']['front_text'], self.flashcard.front_text)
        self.assertEqual(first['card_detail']['back_text'], self.flashcard.back_text)
        self.assertEqual(first['card_detail']['card_type'], self.flashcard.card_type)

    def test_due_card_list_excludes_non_due_cards(self):
        tomorrow = timezone.now().date() + timedelta(days=1)
        due_card_srs_state = self.flashcard.srs_state

        non_due_flashcard = Flashcard.objects.create(
            user=self.user,
            folder=self.folder,
            front_text='non-due',
            back_text='non-due-back',
        )
        non_due_srs_state = non_due_flashcard.srs_state
        non_due_srs_state.due_date = tomorrow
        non_due_srs_state.save(update_fields=['due_date', 'updated_at'])

        response = self.client.get('/api/srs/card-srs/', {'due_date__lte': timezone.now().date().isoformat()})
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        card_ids = {item['card'] for item in response.data['data']}
        self.assertIn(str(due_card_srs_state.card.id), card_ids)
        self.assertNotIn(str(non_due_flashcard.id), card_ids)

    def test_due_card_list_is_user-scoped(self):
        other_user = User.objects.create_user(
            email='other-srs-user@example.com',
            username='other-srs-user',
            password='Password@123',
            role=ROLE_STUDENT,
        )
        other_folder = Folder.objects.create(user=other_user, name='Other Folder')
        other_flashcard = Flashcard.objects.create(
            user=other_user,
            folder=other_folder,
            front_text='other-front',
            back_text='other-back',
        )
        other_srs_state = other_flashcard.srs_state
        other_srs_state.due_date = timezone.now().date()
        other_srs_state.save(update_fields=['due_date', 'updated_at'])

        response = self.client.get('/api/srs/card-srs/', {'due_date__lte': timezone.now().date().isoformat()})
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        returned_card_ids = {item['card'] for item in response.data['data']}
        self.assertIn(str(self.flashcard.id), returned_card_ids)
        self.assertNotIn(str(other_flashcard.id), returned_card_ids)

    def test_folder_crud_contract_and_ownership(self):
        # Create
        response = self.client.post(
            '/api/nfs/folders/',
            {'name': 'New Folder'},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn('data', response.data)
        self.assertEqual(response.data['data']['name'], 'New Folder')
        self.assertIn('flashcard_count', response.data['data'])

        folder_id = response.data['data']['id']

        # List (canonical list envelope)
        list_response = self.client.get('/api/nfs/folders/')
        self.assertEqual(list_response.status_code, status.HTTP_200_OK)
        self.assertIn('data', list_response.data)
        self.assertIn('meta', list_response.data)
        self.assertIsInstance(list_response.data['data'], list)

        # Patch
        patch_response = self.client.patch(
            f'/api/nfs/folders/{folder_id}/',
            {'name': 'Updated Folder'},
            format='json',
        )
        self.assertEqual(patch_response.status_code, status.HTTP_200_OK)
        self.assertIn('data', patch_response.data)
        self.assertEqual(patch_response.data['data']['name'], 'Updated Folder')

        # Delete (soft delete)
        delete_response = self.client.delete(f'/api/nfs/folders/{folder_id}/')
        self.assertEqual(delete_response.status_code, status.HTTP_204_NO_CONTENT)

        folder = Folder.all_objects.get(id=folder_id)
        self.assertTrue(folder.is_deleted)

        # Ownership enforcement: other user cannot delete
        other_user = User.objects.create_user(
            email='folders-other@example.com',
            username='folders-other',
            password='Password@123',
            role=ROLE_STUDENT,
        )
        other_client = self.client
        self.client.force_authenticate(user=other_user)

        # Recreate a fresh folder for deletion attempt.
        target_folder = Folder.objects.create(user=self.user, name='Owner Folder')
        forbidden_response = other_client.delete(f'/api/nfs/folders/{target_folder.id}/')
        self.assertEqual(forbidden_response.status_code, status.HTTP_404_NOT_FOUND)

    def test_flashcard_crud_contract_and_folder_scoping(self):
        other_folder = Folder.objects.create(user=self.user, name='Other Folder')

        # Create
        response = self.client.post(
            '/api/nfs/flashcards/',
            {
                'folder': str(other_folder.id),
                'front_text': 'front',
                'back_text': 'back',
            },
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn('data', response.data)
        self.assertEqual(response.data['data']['folder'], str(other_folder.id))

        flashcard_id = response.data['data']['id']

        # List by folder
        list_response = self.client.get('/api/nfs/flashcards/', {'folder': str(other_folder.id)})
        self.assertEqual(list_response.status_code, status.HTTP_200_OK)
        self.assertIn('data', list_response.data)
        self.assertIn('meta', list_response.data)
        self.assertTrue(all(item['folder'] == str(other_folder.id) for item in list_response.data['data']))

        # Patch
        patch_response = self.client.patch(
            f'/api/nfs/flashcards/{flashcard_id}/',
            {'front_text': 'front-updated'},
            format='json',
        )
        self.assertEqual(patch_response.status_code, status.HTTP_200_OK)
        self.assertEqual(patch_response.data['data']['front_text'], 'front-updated')

        # Delete (soft delete)
        delete_response = self.client.delete(f'/api/nfs/flashcards/{flashcard_id}/')
        self.assertEqual(delete_response.status_code, status.HTTP_204_NO_CONTENT)

        flashcard = Flashcard.all_objects.get(id=flashcard_id)
        self.assertTrue(flashcard.is_deleted)

        # Ownership enforcement: other user cannot delete
        other_user = User.objects.create_user(
            email='flashcards-other@example.com',
            username='flashcards-other',
            password='Password@123',
            role=ROLE_STUDENT,
        )
        self.client.force_authenticate(user=other_user)
        target_flashcard = Flashcard.objects.create(
            user=self.user,
            folder=self.folder,
            front_text='owner',
            back_text='owner-back',
        )
        forbidden_response = self.client.delete(f'/api/nfs/flashcards/{target_flashcard.id}/')
        self.assertEqual(forbidden_response.status_code, status.HTTP_404_NOT_FOUND)

    def test_review_session_summary_fields_are_real_and_non_fake(self):
        session = ReviewSession.objects.create(user=self.user)

        # Review once.
        self.client.post(
            '/api/rse/card-review-logs/',
            {
                'session': str(session.id),
                'card': str(self.flashcard.id),
                'choice': 'GOOD',
            },
            format='json',
        )

        response = self.client.get('/api/rse/review-sessions/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('meta', response.data)
        sessions_payload = response.data['data']

        session_items = [item for item in sessions_payload if str(item['id']) == str(session.id)]
        self.assertEqual(len(session_items), 1)
        item = session_items[0]

        self.assertIn('cards_reviewed', item)
        self.assertIn('xp_earned', item)
        self.assertEqual(item['cards_reviewed'], 1)
        self.assertEqual(item['xp_earned'], XP_AMOUNTS['review'])

    def test_review_session_create_returns_canonical_envelope_and_initial_summary(self):
        response = self.client.post('/api/rse/review-sessions/', {}, format='json')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn('data', response.data)
        payload = response.data['data']

        self.assertIsNotNone(payload.get('started_at'))
        self.assertIn('cards_reviewed', payload)
        self.assertIn('xp_earned', payload)
        self.assertEqual(payload['cards_reviewed'], 0)
        self.assertEqual(payload['xp_earned'], 0)

    def test_card_review_create_rejects_invalid_choice(self):
        session = ReviewSession.objects.create(user=self.user)

        response = self.client.post(
            '/api/rse/card-review-logs/',
            {
                'session': str(session.id),
                'card': str(self.flashcard.id),
                'choice': 'INVALID',
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('choice', response.data.get('error', response.data))

    def test_review_session_end_session_sets_ended_at_and_returns_envelope(self):
        session = ReviewSession.objects.create(user=self.user)

        response = self.client.patch(
            f'/api/rse/review-sessions/{session.id}/',
            {},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('data', response.data)
        self.assertIsNotNone(response.data['data']['ended_at'])

    def test_card_review_create_updates_srs_state_and_returns_canonical_detail(self):
        session = ReviewSession.objects.create(user=self.user)
        srs_state_before = CardSRSState.objects.select_related('card').get(card=self.flashcard)

        response = self.client.post(
            '/api/rse/card-review-logs/',
            {
                'session': str(session.id),
                'card': str(self.flashcard.id),
                'choice': 'EASY',
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn('data', response.data)
        payload = response.data['data']

        self.assertEqual(payload['choice'], 'EASY')
        self.assertIsNotNone(payload['new_due_date'])
        self.assertIsNotNone(payload['new_stage'])

        srs_state_before_stage = srs_state_before.stage
        srs_state_before_interval = srs_state_before.interval_days
        expected_stage, expected_interval, expected_due = calculate_srs_update(
            current_stage=srs_state_before_stage,
            current_interval=srs_state_before_interval,
            choice='EASY',
        )

        srs_state_after = CardSRSState.objects.select_related('card').get(card=self.flashcard)
        self.assertEqual(srs_state_after.stage, expected_stage)
        self.assertEqual(srs_state_after.interval_days, expected_interval)
        self.assertEqual(srs_state_after.due_date, expected_due)

        # Ensure a real review log exists (no fake success).
        logs = CardReviewLog.objects.filter(session=session, card=self.flashcard, user=self.user)
        self.assertEqual(logs.count(), 1)

    def test_card_review_create_rejects_session_ownership_mismatch(self):
        other_user_session = ReviewSession.objects.create(user=User.objects.create_user(
            email='session-owner@example.com',
            username='session-owner',
            password='Password@123',
            role=ROLE_STUDENT,
        ))

        response = self.client.post(
            '/api/rse/card-review-logs/',
            {
                'session': str(other_user_session.id),
                'card': str(self.flashcard.id),
                'choice': 'GOOD',
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

        # SRS state should remain unchanged on rejection.
        srs_state_after = CardSRSState.objects.select_related('card').get(card=self.flashcard)
        self.assertEqual(srs_state_after.stage, 0)
