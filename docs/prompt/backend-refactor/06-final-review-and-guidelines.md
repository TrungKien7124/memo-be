# Prompt: Final Review And Team Guidelines

Ban hay thuc hien review tong the cho toan bo initiative refactor backend nay.

## Muc tieu

- Xac nhan refactor di dung target architecture.
- Xac nhan backward compatibility van duoc bao toan.
- Chot coding guideline de team phat trien feature moi theo style moi.

## Checklist review

- Modular cap he thong van giu: `app_server`, `ai`, `srs`, `les`
- `app_server` da duoc chia domain ro rang:
  - `common`
  - `users`
  - `curriculum`
  - `learning`
  - `flashcards`
  - `gamification`
- Naming Python da ro rang hon, khong con le thuoc vao prefix `iam/cms/lms/nfs/gms` ngoai compatibility layer neu co
- View khong om business logic lon
- Normalizer chi xu ly coercion nhe
- Serializer xu ly schema validation
- Service xu ly write workflow va side effects
- Selector xu ly read/query phuc tap
- Route public khong doi
- DB table va app label khong doi ngoai chu y
- Khong co circular import moi
- Test regression quan trong da co

## Cong viec

1. Review tat ca domain sau move.
2. Lap danh sach issue theo muc do uu tien.
3. Viet coding guideline sau refactor:
   - naming convention
   - khi nao tao normalizer
   - khi nao tao input/output serializer
   - khi nao tao service
   - khi nao tao selector
   - anti-pattern can tranh
4. Viet checklist review code cho cac feature moi de team follow.

## Dau ra mong muon

- 1 bao cao review tong hop
- 1 coding guideline ngan gon, thuc dung, ap dung ngay duoc
