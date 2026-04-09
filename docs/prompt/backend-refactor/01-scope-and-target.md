# Prompt: Scope And Target Architecture

Ban dang thuc hien mot initiative refactor backend lon, nhung pham vi duoc gioi han ro rang.

## Muc tieu

- Giu modular cap he thong hien tai: `app_server`, `ai`, `srs`, `les`.
- Chi refactor noi bo `be/apps/app_server`.
- Chuyen bo cuc tu technical-layer + prefix naming sang domain package de doc hon.
- Khong doi behavior, route public, DB table, app label trong phase dau.

## Bat buoc doc truoc

- Toan bo `be/apps/app_server/`
- `be/memo_backend/settings.py`
- `be/memo_backend/urls.py`
- `be/apps/les/services/lesson_ingestion_scheduling_service.py`
- `be/apps/ai/controllers/acs_chat_controller.py`
- `be/apps/srs/signals.py`

## Target structure mong muon

```text
be/apps/app_server/
├── common/
├── users/
├── curriculum/
├── learning/
├── flashcards/
├── gamification/
└── routes.py
```

## Mapping domain

- `iam_*` -> `users`
- `cms_*` -> `curriculum`
- `lms_*` -> `learning`
- `nfs_*` -> `flashcards`
- `gms_*` -> `gamification`

## Cong viec

1. Audit hien trang `app_server`.
2. Lap bang mapping file cu -> file moi.
3. Chi ra flow nhay cam can bao toan:
   - auth va profile
   - course/module/lesson
   - lesson ingestion side effects
   - lesson progress/quiz/unlock
   - flashcard -> SRS signal
   - XP service callers
4. Chot naming convention moi cho file, class, serializer, service, selector.
5. Chot cac compatibility import can co tam thoi.

## Dau ra mong muon

- 1 tai lieu target architecture ngan gon
- 1 bang mapping file cu -> file moi
- 1 danh sach flow/rui ro nhay cam
- 1 naming convention de team theo
