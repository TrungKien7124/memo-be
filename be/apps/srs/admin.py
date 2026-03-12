from django.contrib import admin

from apps.srs.models.srs_card_srs_state_model import CardSRSState
from apps.srs.models.rse_review_session_model import ReviewSession
from apps.srs.models.rse_card_review_log_model import CardReviewLog


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
