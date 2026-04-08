from django.contrib import admin

from apps.srs.models.card_repetition_state_model import CardSRSState
from apps.srs.models.review_session_model import ReviewSession
from apps.srs.models.card_review_log_model import CardReviewLog


@admin.register(CardSRSState)
class CardSRSStateAdmin(admin.ModelAdmin):
    list_display = ['card', 'stage', 'interval_days', 'due_date', 'last_review']
    list_filter = ['stage']


@admin.register(ReviewSession)
class ReviewSessionAdmin(admin.ModelAdmin):
    list_display = ['user', 'started_at', 'ended_at']


@admin.register(CardReviewLog)
class CardReviewLogAdmin(admin.ModelAdmin):
    list_display = ['card', 'user', 'choice', 'reviewed_at', 'prev_stage', 'new_stage']
    list_filter = ['choice']
