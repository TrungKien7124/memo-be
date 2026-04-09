# Prompt: Wave 2 Refactor Coupled Learning Domains

Ban hay refactor cac domain coupling cao cung nhau trong cung mot wave de tranh move nua roi lai sua lai vi dependency cheo.

## Domain trong wave nay

- `curriculum`
- `learning`

## Ly do gom chung

- `Lesson`, `Module`, `Course`, `LessonProgress`, unlock logic va quiz logic lien quan chat che.
- `Lesson` con co side effect voi `les` ingestion.
- Neu tach 2 domain nay thanh 2 dot le, kha nang import chong cheo va compatibility layer tam thoi se cao hon.

## Bat buoc doc truoc

### Curriculum
- `be/apps/app_server/models/implemented/cms_course_model.py`
- `be/apps/app_server/models/implemented/cms_module_model.py`
- `be/apps/app_server/models/implemented/cms_lesson_model.py`
- `be/apps/app_server/controllers/implemented/cms_course_controller.py`
- `be/apps/app_server/controllers/implemented/cms_module_controller.py`
- `be/apps/app_server/controllers/implemented/cms_lesson_controller.py`
- `be/apps/app_server/routes/implemented/cms_route.py`
- `be/apps/app_server/serializers/implemented/cms_*.py`
- `be/apps/les/services/lesson_ingestion_scheduling_service.py`

### Learning
- `be/apps/app_server/models/implemented/lms_lesson_progress_model.py`
- `be/apps/app_server/controllers/implemented/lms_lesson_progress_controller.py`
- `be/apps/app_server/routes/implemented/lms_route.py`
- `be/apps/app_server/serializers/implemented/lms_lesson_progress_serializer.py`
- `be/apps/app_server/services/lms_progress_service.py`
- `be/apps/app_server/services/lms_unlock_service.py`
- `be/apps/app_server/services/gms_xp_service.py`

## Cong viec

1. Tao package moi:
   - `curriculum/`
   - `learning/`
2. Move model, api, serializer, service, selector theo domain.
3. Giu nguyen toan bo side effect nhay cam:
   - lesson create -> ingestion
   - lesson update -> reingestion neu can
   - lesson delete -> delete index scheduling
   - lesson progress -> XP
   - quiz runtime rule
   - unlock state rule
4. Giam coupling xau bang cach:
   - dat write workflow vao service
   - dat read/query state vao selector neu can
5. Viet test regression cho:
   - course/module/lesson CRUD
   - lesson side effects
   - video/text/quiz progress
   - unlock flow

## Rang buoc

- Khong doi DB table name.
- Khong doi route public.
- Khong doi ingestion scheduling logic.
- Khong doi XP awarding logic.
- Khong doi response payload cua progress API.

## Dau ra mong muon

- `curriculum` va `learning` duoc move on dinh
- coupling ro rang hon
- regression test pass
