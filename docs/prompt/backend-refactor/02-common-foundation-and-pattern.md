# Prompt: Build Common Foundation And Standardize API Pattern

Ban hay thuc hien mot wave refactor nen tang dung chung cho `app_server`.

## Muc tieu

- Tao `app_server/common/` cho shared foundation.
- Chuan hoa flow xu ly request de dung duoc cho moi domain.
- Dat nen tang 1 lan de cac wave sau chi can move domain va ap pattern.

## Bat buoc doc truoc

- `be/apps/app_server/controllers/base/base_controller.py`
- `be/apps/app_server/serializers/base/base_serializer.py`
- `be/apps/app_server/pagination/standard_pagination.py`
- `be/apps/app_server/exceptions/exception_handler.py`
- `be/apps/app_server/permissions/role_permission.py`
- `be/apps/app_server/normalizers/base/base_normalizer.py`
- `be/apps/app_server/controllers/implemented/nfs_flashcard_controller.py`
- `be/apps/app_server/serializers/implemented/*.py`

## Cong viec

1. Tao `be/apps/app_server/common/` va move shared code vao day:
   - `api/`
   - `serializers/`
   - `normalizers/`
   - `permissions/`
   - `pagination/`
   - `exceptions/`
2. Chuan hoa convention:
   - `view` chi xu ly HTTP gateway
   - `normalizer` chi xu ly input coercion nhe
   - `input serializer` validate schema request
   - `output serializer` shape response
   - `service` xu ly write workflow va side effects
   - `selector` xu ly read/query phuc tap
3. Tao hoac cap nhat base classes de support flow:
   - `normalizer_class`
   - `input_serializer_class`
   - `output_serializer_class`
4. Ghi lai convention ngan cho team:
   - khi nao can normalizer
   - khi nao khong can normalizer
   - khi nao can service
   - khi nao can selector

## Rang buoc

- Khong dua business rule vao normalizer.
- Khong tao framework qua magic.
- Khong doi response format chung.
- Khong doi behavior route hien tai.

## Dau ra mong muon

- Shared foundation moi trong `common/`
- Base pattern moi cho API flow
- 1 file convention ngan de domain wave sau follow
