# Prompt: Wave 1 Refactor Low Risk Domains

Ban hay refactor cac domain co coupling thap hon truoc de pilot pattern moi va giam rui ro.

## Domain trong wave nay

- `users`
- `flashcards`
- `gamification`

## Ly do gom chung

- Deu nam chu yeu trong `app_server`.
- Co the huong loi tu common foundation va API pattern moi ngay lap tuc.
- It coupling hon so voi `curriculum + learning`, du van co dependency can giu.

## Bat buoc doc truoc

### Users
- `be/apps/app_server/models/implemented/iam_user_model.py`
- `be/apps/app_server/models/implemented/iam_user_profile_model.py`
- `be/apps/app_server/controllers/implemented/iam_auth_controller.py`
- `be/apps/app_server/controllers/implemented/iam_user_profile_controller.py`
- `be/apps/app_server/routes/implemented/iam_route.py`
- `be/apps/app_server/serializers/implemented/iam_auth_serializer.py`
- `be/apps/app_server/validators/implemented/iam_validators.py`

### Flashcards
- `be/apps/app_server/models/implemented/nfs_folder_model.py`
- `be/apps/app_server/models/implemented/nfs_flashcard_model.py`
- `be/apps/app_server/controllers/implemented/nfs_folder_controller.py`
- `be/apps/app_server/controllers/implemented/nfs_flashcard_controller.py`
- `be/apps/app_server/routes/implemented/nfs_route.py`
- `be/apps/app_server/serializers/implemented/nfs_folder_serializer.py`
- `be/apps/app_server/serializers/implemented/nfs_flashcard_serializer.py`
- `be/apps/srs/signals.py`

### Gamification
- `be/apps/app_server/models/implemented/gms_user_xp_model.py`
- `be/apps/app_server/models/implemented/gms_xp_transaction_model.py`
- `be/apps/app_server/controllers/implemented/gms_controller.py`
- `be/apps/app_server/routes/implemented/gms_route.py`
- `be/apps/app_server/serializers/implemented/gms_serializer.py`
- `be/apps/app_server/services/gms_xp_service.py`

## Cong viec

1. Tao package moi:
   - `users/`
   - `flashcards/`
   - `gamification/`
2. Move model, api, serializer, service, validator theo domain moi.
3. Ap dung pattern API moi day du, dac biet voi `flashcards` de lam domain mau.
4. Giu compatibility import neu can cho cac caller cu.
5. Giu route public cu.
6. Viet test regression cho tung domain.

## Rang buoc

- Khong doi custom user model behavior.
- Khong doi auth/JWT flow.
- Khong doi flashcard -> SRS signal behavior.
- Khong doi public API cua XP service neu domain khac dang goi.

## Dau ra mong muon

- 3 domain moi da duoc move va chay on dinh
- `flashcards` tro thanh domain mau cho pattern moi
- test regression pass
