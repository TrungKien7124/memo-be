# Prompt: Compatibility Cleanup And Hardening

Ban hay thuc hien wave don dep va hardening sau khi tat ca domain da duoc move.

## Muc tieu

- Gom route cho de doc hon.
- Don import path.
- Giu backward compatibility o muc can thiet.
- Chot lai phan wiring de codebase sach hon.

## Bat buoc doc truoc

- `be/apps/app_server/routes/__init__.py`
- `be/apps/app_server/routes/base/base_route.py`
- `be/apps/app_server/routes/implemented/*.py`
- toan bo domain moi trong `be/apps/app_server/`
- `be/memo_backend/urls.py`

## Cong viec

1. Gom route theo entrypoint moi, vi du `be/apps/app_server/routes.py`.
2. Giu route public khong doi.
3. Danh sach va don compatibility import khong con can thiet.
4. Giu compatibility import tam thoi cho nhung cho con caller cu.
5. Dung lai import path ve domain moi thay vi path cu o muc toi da co the.
6. Don bo cuc package de team de tim file hon.

## Rang buoc

- Khong doi endpoint public.
- Khong doi trailing slash behavior.
- Khong xoa compatibility import neu van con caller dang can.

## Dau ra mong muon

- Route aggregation sach hon
- Import path sach hon
- Compatibility layer duoc ghi ro giu cai nao, bo cai nao
