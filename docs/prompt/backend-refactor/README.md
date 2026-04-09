# Backend Refactor Prompt Pack

Day la bo prompt cho **1 task lon duy nhat**: refactor backend hien tai, trong tam la `be/apps/app_server`.

Muc tieu:

- giu modular cap he thong hien tai: `app_server`, `ai`, `srs`, `les`;
- khong refactor toan bo repo theo cookiecutter shell;
- refactor noi bo `app_server` de de doc hon;
- bo naming prefix kho doc nhu `iam/cms/lms/nfs/gms` o bo cuc Python;
- chuan hoa flow `normalizer -> serializer -> service -> selector` theo kieu Django de su dung thong nhat.

Nguyen tac:

- Khong doi DB table name o giai doan dau.
- Khong doi app label o giai doan dau.
- Khong doi API public contract o giai doan dau.
- Khong lam big-bang rewrite.
- Refactor theo tung wave de co the review va rollback logic de dang.

Thu tu thuc hien:

1. `01-scope-and-target.md`
2. `02-common-foundation-and-pattern.md`
3. `03-wave-1-low-risk-domains.md`
4. `04-wave-2-coupled-learning-domains.md`
5. `05-compatibility-cleanup-and-hardening.md`
6. `06-final-review-and-guidelines.md`

Ly do chia nhu vay:

- Step 1 chot huong va mapping.
- Step 2 xay nen tang dung chung 1 lan cho tat ca domain.
- Step 3 gom cac domain it coupling hon de pilot pattern moi.
- Step 4 gom cac domain coupling cao de xu ly chung trong cung mot wave.
- Step 5 gom viec don route, compatibility, import path, hardening.
- Step 6 review tong va chot guideline de team code feature moi.
