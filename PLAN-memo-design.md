# MEMO – Tài Liệu Phân Tích & Thiết Kế Hệ Thống

> **Phiên bản:** 2.0 · **Ngày cập nhật:** 2026-03-10
> **Loại dự án:** Đồ án tốt nghiệp cá nhân · **Quy mô:** < 1.000 users

---

## 1. Tổng Quan

**MEMO** là nền tảng học tiếng Anh tích hợp AI, tập trung vào hai giá trị cốt lõi:

1. **Ghi nhớ dài hạn** – Flashcard + Spaced Repetition với thuật toán thông minh
2. **Luyện giao tiếp** – Hội thoại AI hai chiều, STT/TTS realtime

### 1.1 Mục Tiêu Hệ Thống

| Mục tiêu | Mô tả |
|-----------|--------|
| **Học có cấu trúc** | Khóa học → Module → Lesson (video/text/quiz) theo lộ trình |
| **Ghi nhớ hiệu quả** | Flashcard + SRS tự động lên lịch ôn tập |
| **Luyện nói AI** | Hội thoại tự do theo chủ đề, AI thích nghi theo ngữ cảnh |
| **Data-driven** | Log hành vi học tập, sẵn sàng cho ML optimization |
| **Đo lường** | Thời gian học thực tế (active time) làm thước đo chính |

### 1.2 Phạm Vi MVP

**Trong scope:**
- Auth (đăng ký/đăng nhập, phân quyền)
- Quản lý khóa học + theo dõi tiến độ
- Flashcard + Folder + Spaced Repetition
- Speaking practice (AI conversation)
- Gamification (XP + Leaderboard)
- Admin (Django Admin)

**Ngoài scope (giai đoạn sau):**
- Social learning (chia sẻ, follow)
- Payment/subscription
- Mobile app (chỉ web responsive)
- Notification push

---

## 2. Kiến Trúc Tổng Thể

### 2.1 Mô Hình Kiến Trúc

**Modular Monolith** – một codebase, tách module theo nghiệp vụ, dùng chung CORE layer.

```
┌─────────────────────────────────────────────────┐
│                    Client (ReactJS)              │
├──────────────────────┬──────────────────────────┤
│       REST API       │    WebSocket (Channels)   │
├──────────────────────┴──────────────────────────┤
│                  Django + DRF                    │
│  ┌────────────────────────────────────────────┐  │
│  │              CORE LAYER                    │  │
│  │  BaseModel · BaseController · Serializer   │  │
│  │  Normalizer · Pagination · Exception       │  │
│  └────────────────────────────────────────────┘  │
│  ┌──────────┐ ┌──────────┐ ┌────────────────┐   │
│  │   auth   │ │ learning │ │   flashcard    │   │
│  │  (IAM)   │ │(CMS+LMS) │ │ (NFS+SRS+RSE) │   │
│  └──────────┘ └──────────┘ └────────────────┘   │
│  ┌──────────┐ ┌──────────┐ ┌────────────────┐   │
│  │    ai    │ │   gami   │ │  notification  │   │
│  │(ACS+SPS) │ │  (GMS)   │ │    (NTS)       │   │
│  └──────────┘ └──────────┘ └────────────────┘   │
├─────────────────────────────────────────────────┤
│  PostgreSQL  │  Redis (Cache/Queue)  │  Celery   │
└─────────────────────────────────────────────────┘
```

### 2.2 Tổ Chức Django Apps

| App | Module cũ | Nhiệm vụ |
|-----|-----------|-----------|
| `app_server` | auth, learning, flashcard, gami, notification | Module chính + CORE layer |
| `srs` | SRS + RSE | Spaced Repetition engine (tách vì logic phức tạp) |
| `ai` | ACS + SPS | AI conversation & speaking (tách vì dependency riêng) |

> **Tại sao tách 3 app?** Dễ extract thành microservice sau này nếu AI hoặc SRS cần scale riêng.

---

## 3. Các Module Chính

### 3.1 Auth (Identity & Access Management)

**Chức năng:** Đăng ký, đăng nhập, phân quyền.

| Thành phần | Chi tiết |
|------------|----------|
| **User model** | Kế thừa `AbstractUser`, thêm field `role` |
| **Auth strategy** | JWT (access token 15 phút + refresh token 7 ngày) |
| **Roles** | `student`, `teacher`, `admin` |
| **Permissions** | Role-based (RolePermission) + Object-level (ObjectPermission) |

**Auth flow:**
```
Register → POST /api/auth/register/ → tạo User + UserProfile → trả tokens
Login    → POST /api/auth/login/    → validate → trả access + refresh token
Refresh  → POST /api/auth/refresh/  → validate refresh → trả access mới
```

### 3.2 Learning (Course Management + Progress)

**Chức năng:** Quản lý khóa học, theo dõi tiến độ.

**Cấu trúc nội dung:**
```
Course → Module (ordered) → Lesson (video | text | quiz)
```

**Business rules:**
- `lesson_type=video`: dùng `video_url` + `min_watch_time`
- `lesson_type=text`: dùng `content_markdown`
- `lesson_type=quiz`: dùng `quiz_questions` (mỗi câu 4 đáp án, 1 đáp án đúng)
- Mỗi module chỉ có tối đa 1 bài kiểm tra cuối: `is_final=true` (chỉ áp dụng cho `lesson_type=quiz`)
- Rule mở khóa module: user phải pass final quiz của module hiện tại (>=80%) thì module kế tiếp mới mở.
- Lesson hoàn thành khi `watched_seconds >= min_watch_time` (mặc định 120s)
- Hoàn thành lesson → cộng XP
- Trang "tham gia khóa học" thiết kế sẵn cho payment (hiện miễn phí)

### 3.3 Flashcard (Note + SRS + Review Engine)

**Chức năng:** Tạo flashcard, tổ chức theo folder, ôn tập spaced repetition.

**Cấu trúc:**
```
User → Folder (flat, không lồng) → Flashcard → CardSRSState
```

**Flashcard fields:** `front_text`, `back_text`, `ipa`, `audio_url`, `image_url`, `card_type`

**SRS Algorithm (SM-2 simplified):**

| Phản hồi | Hành động | Interval mới |
|-----------|-----------|--------------|
| **EASY** | stage += 2 | interval × 2.5 |
| **GOOD** | stage += 1 | interval × 1.5 |
| **HARD** | stage = 0 | 1 ngày (ôn lại mai) |

**Review session rules:**
1. Tạo session → lấy cards có `due_date <= today`
2. Card mới tạo **không** xuất hiện trong session hiện tại
3. Card đã review trong session **không** lặp lại
4. Hết card → kết thúc session tự động
5. Ghi log đầy đủ: `prev_stage`, `new_stage`, `prev_interval`, `new_interval`

> **Mở rộng:** Stage/interval có thể được ML model quyết định thay vì formula cứng.

### 3.4 AI (Chat + Speaking Practice)

**Chức năng:** Hội thoại AI để luyện nói/viết tiếng Anh.

**Kiến trúc AI Pipeline:**
```
[Speaking Flow]
User Audio → STT (Whisper API) → Text → LLM (OpenAI/Gemini) → Response Text → TTS → Audio

[Chat Flow]  
User Text → LLM (OpenAI/Gemini) → Response Text
```

**Đặc điểm:**
- **Không kịch bản cứng** – AI tự thích nghi theo câu trả lời
- **Template chủ đề** – Có sẵn prompt template theo topic (ordering food, job interview, ...)
- **Feedback bằng text** – Không chấm điểm phát âm (ngoài scope MVP)
- **Context window** – Giữ lịch sử hội thoại trong session

**Error handling:**
- AI timeout/rate limit → retry 1 lần → trả message lỗi graceful
- STT fail → fallback sang text input
- Celery async cho các request AI nặng

### 3.5 Gamification

**Chức năng:** Tạo động lực học tập qua XP và leaderboard.

| Hoạt động | XP gợi ý |
|-----------|----------|
| Hoàn thành lesson video | 10 XP |
| Review session (SRS) | 15 XP |
| Quiz hoàn thành | 20 XP |
| Speaking session | 30 XP |

- Leaderboard: top users theo **XP** và **thời gian học tuần/tháng**
- XP history log cho ML analysis

### 3.6 Notification (Giai đoạn sau)

- Nhắc ôn tập khi có card đến hạn
- Nhắc khi bỏ học > 2 ngày
- Giai đoạn MVP: Email qua Celery. Push notification để sau.

---

## 4. Thiết Kế Database

### 4.1 Nguyên Tắc

- Mọi model kế thừa `BaseModel` → tự động có `id`, `created_at`, `updated_at`, `is_deleted`
- Soft delete cho mọi entity
- PostgreSQL, sử dụng index cho query thường xuyên

### 4.2 Schema

```
┌──────────────┐     ┌────────────────┐
│    users     │────▶│  user_profile  │
│──────────────│     │────────────────│
│ id (PK)      │     │ user_id (PK,FK)│
│ email (UQ)   │     │ display_name   │
│ password_hash│     │ avatar_url     │
│ role         │     │ timezone       │
│ created_at   │     └────────────────┘
└──────┬───────┘
       │
       ├──────────────────────────────────────┐
       │                                      │
       ▼                                      ▼
┌──────────────┐     ┌──────────────┐  ┌──────────────┐
│   courses    │────▶│   modules    │  │   folders    │
│──────────────│     │──────────────│  │──────────────│
│ id (PK)      │     │ id (PK)      │  │ id (PK)      │
│ title        │     │ course_id(FK)│  │ user_id (FK) │
│ description  │     │ title        │  │ name         │
│ status       │     │ order_index  │  └──────┬───────┘
│ created_by   │     └──────┬───────┘         │
└──────────────┘            │                 ▼
                            ▼          ┌──────────────┐
                     ┌──────────────┐  │  flashcards  │
                     │   lessons    │  │──────────────│
                     │──────────────│  │ id (PK)      │
                     │ id (PK)      │  │ user_id (FK) │
                     │ module_id(FK)│  │ folder_id(FK)│
                     │ title        │  │ front_text   │
                     │ lesson_type  │  │ back_text    │
                     │ video_url    │  │ ipa          │
                     │ content_md   │  │              │
                     │ quiz_questions│ │              │
                     │ is_final     │  │              │
                     │ min_watch_time│ │              │
                     └──────┬───────┘  │ audio_url    │
                            │          │ image_url    │
                            ▼          │ card_type    │
                     ┌────────────────┐└──────┬───────┘
                     │lesson_progress │       │
                     │────────────────│       ▼
                     │ user_id (FK)   │┌────────────────┐
                     │ lesson_id (FK) ││ card_srs_state │
                     │ watched_seconds││────────────────│
                     │ completed      ││ card_id(PK,FK) │
                     │ completed_at   ││ stage          │
                     │ PK: (user,less)││ interval_days  │
                     └────────────────┘│ due_date  ◄─IDX│
                                       │ last_review    │
                                       └────────────────┘

┌──────────────────┐     ┌────────────────────┐
│ review_sessions  │     │  card_review_log   │
│──────────────────│     │────────────────────│
│ id (PK)          │     │ id (PK)            │
│ user_id (FK)     │     │ card_id (FK)       │
│ started_at       │     │ user_id (FK)       │
│ ended_at         │     │ session_id (FK)    │
│                  │     │ choice (EASY/GOOD/ │
└──────────────────┘     │          HARD)     │
                          │ reviewed_at       │
                          │ prev/new_stage    │
                          │ prev/new_interval │
                          │ prev/new_due_date │
                          └────────────────────┘
```

### 4.3 Index Strategy

| Table | Column(s) | Lý do |
|-------|-----------|-------|
| `card_srs_state` | `due_date` | Query card đến hạn hàng ngày |
| `flashcards` | `user_id, folder_id` | Filter theo user + folder |
| `lesson_progress` | `user_id` | Dashboard tiến độ |
| `card_review_log` | `user_id, reviewed_at` | Thống kê học tập |
| `review_sessions` | `user_id, started_at` | Lịch sử ôn tập |

---

## 5. CORE Layer (Framework nội bộ)

CORE cung cấp các thành phần dùng chung, giúp giảm boilerplate:

| Component | Chức năng |
|-----------|-----------|
| `BaseModel` | Abstract model: `id`, `created_at`, `updated_at`, `is_deleted`, soft delete queryset |
| `CoreModelViewSet` | CRUD controller chuẩn: `list`, `retrieve`, `create`, `update`, `delete` |
| `CoreModelSerializer` | Cấu hình `field_list`, `ignore_fields`, `validation_rules` |
| `Normalizer` | Chuẩn hóa input từ FE trước khi validate |
| `Pagination` | Response format chuẩn với `data` + `meta` |
| `ExceptionHandler` | Format error thống nhất |

**Response formats:**

```json
// Success (list)
{ "data": [...], "meta": { "count": 50, "page": 1, "page_size": 20, "next": "...", "previous": "..." } }

// Success (detail)
{ "data": { ... } }

// Error (standardized)
{
  "message": "Validation failed",
  "old_data": { "email": "alice@example.com", "username": "alice" },
  "error": {
    "email": ["A user with this email already exists."],
    "username": ["A user with this username already exists."]
  }
}
```

### 5.1 Error Contract (BE -> FE)

Mọi lỗi API phải trả về đúng schema sau:

```json
{
  "message": "Error summary for alert/toast",
  "old_data": { "field": "value user entered before error" },
  "error": {
    "field_name": ["error 1", "error 2"],
    "non_field_errors": ["general error"]
  }
}
```

**Ý nghĩa từng field:**
- `message`: message tổng quát hiển thị toast/alert.
- `old_data`: dữ liệu user vừa gửi để FE restore form (không chứa dữ liệu nhạy cảm như password/token).
- `error`: map lỗi theo field để FE highlight input tương ứng.

**Quy tắc triển khai:**
- Dùng `custom_exception_handler` cho mọi lỗi DRF chuẩn (`ValidationError`, `NotFound`, ...).
- Với lỗi trả thủ công trong controller/service phải dùng helper trả lỗi cùng schema.
- Không trả format lỗi cũ dạng `{ "error": { "type": "...", "details": ... } }`.

---

## 6. Cấu Trúc Thư Mục Backend

```
memo-be/be/
├── memo_backend/
│   ├── settings.py       # Django, DRF, CORS, Celery, Channels
│   ├── urls.py           # Router gốc
│   ├── asgi.py           # ASGI entrypoint (Channels)
│   ├── wsgi.py           # WSGI entrypoint
│   ├── celery.py         # Celery config
│   └── routing.py        # WebSocket routes
├── apps/
│   ├── app_server/       # Module chính + CORE
│   │   ├── models/       # {base, implemented, extended}
│   │   ├── controllers/  # {base, implemented, extended}
│   │   ├── serializers/  # {base, implemented, extended}
│   │   ├── normalizers/  # {base, implemented, extended}
│   │   ├── validators/   # {base, implemented, extended}
│   │   ├── services/     # ← CẦN THÊM: business logic
│   │   ├── routes/       # {base, implemented, extended}
│   │   ├── pagination/
│   │   ├── exceptions/
│   │   └── management/commands/
│   ├── srs/              # SRS engine
│   │   ├── models/
│   │   ├── controllers/
│   │   ├── serializers/
│   │   ├── normalizers/
│   │   ├── services/     # ← CẦN THÊM: SRS algorithm
│   │   └── routes/
│   └── ai/               # AI conversation
│       ├── models/
│       ├── controllers/
│       ├── services/     # ← CẦN THÊM: AI pipeline
│       └── routes/
├── manage.py
└── requirements.txt
```

**Quy ước đặt tên:**
- Model: `<domain>_<entity>_model.py` (vd: `iam_user_model.py`)
- Controller: `<domain>_<entity>_controller.py`
- Serializer: `<domain>_<entity>_serializer.py`
- Service: `<domain>_<usecase>_service.py` (vd: `srs_review_service.py`)

---

## 7. API Design

### 7.1 API Routes

| Domain | Endpoints |
|--------|-----------|
| **Auth** | `POST /api/auth/register/` · `POST /api/auth/login/` · `POST /api/auth/refresh/` |
| **User** | `GET/PUT /api/iam/profiles/` · `GET /api/iam/users/` |
| **Course** | `CRUD /api/cms/courses/` · `CRUD /api/cms/modules/` · `CRUD /api/cms/lessons/` |
| **Progress** | `CRUD /api/lms/lesson-progress/` |
| **Flashcard** | `CRUD /api/nfs/folders/` · `CRUD /api/nfs/flashcards/` |
| **SRS** | `GET /api/srs/card-srs/?due_date__lte=today` · `PUT /api/srs/card-srs/{id}/` |
| **Review** | `POST /api/rse/review-sessions/` · `POST /api/rse/card-review-logs/` |
| **AI Chat** | `POST /api/acs/chat/` · `GET /api/acs/history/` |
| **Speaking** | `POST /api/sps/sessions/` · `POST /api/sps/speak/` |
| **Gamification** | `GET /api/gms/xp/` · `GET /api/gms/leaderboard/` |
| **Health** | `GET /health/` · `GET /api/<domain>/health/` |

### 7.2 Sequence Flows

**Ôn tập SRS:**
```
1. POST /api/rse/review-sessions/           → Tạo session mới
2. GET  /api/srs/card-srs/?due_date__lte=today  → Lấy cards đến hạn
3. [User review từng card]
4. POST /api/rse/card-review-logs/          → Ghi log (choice: EASY/GOOD/HARD)
   → Service tự động update CardSRSState
5. PATCH /api/rse/review-sessions/{id}/     → Set ended_at khi hết card
```

**Hoàn thành Lesson:**
```
1. User xem video → FE gửi watched_seconds (debounced)
2. PUT /api/lms/lesson-progress/            → Update watched_seconds
3. Khi watched_seconds >= min_watch_time    → completed = true, cộng XP
```

**Quiz lesson (bao gồm final module quiz):**
```
1. Admin tạo lesson_type=quiz với quiz_questions
2. (Tùy chọn) set is_final=true để đánh dấu bài kiểm tra cuối module
3. FE submit selected_answers, BE chấm điểm và lưu score/attempt/pass
4. Nếu quiz là final quiz và đạt >=80% thì mở khóa module kế tiếp
```

**Speaking Practice:**
```
1. POST /api/sps/sessions/          → Tạo speaking session (chọn topic)
2. POST /api/sps/speak/             → Gửi audio
   → STT (Whisper) → Text → LLM → Response → TTS → Audio response
3. Repeat step 2 cho multi-turn conversation
4. Kết thúc → ghi log + cộng XP
```

---

## 8. Công Nghệ Sử Dụng

| Layer | Công nghệ | Lý do |
|-------|-----------|-------|
| **Frontend** | ReactJS | SPA, component-based, ecosystem lớn |
| **Backend** | Django 4.2 + DRF | Nhanh phát triển, ORM mạnh, admin sẵn |
| **Database** | PostgreSQL | ACID, JSON support, full-text search |
| **Cache** | Redis | Session cache, SRS query cache, Celery broker |
| **Async** | Celery | AI requests, email notifications, XP calculation |
| **Realtime** | Django Channels | WebSocket cho speaking practice |
| **AI** | OpenAI/Gemini API | LLM cho conversation |
| **STT** | Whisper API | Speech-to-text cho speaking |
| **TTS** | OpenAI TTS / Google TTS | Text-to-speech cho AI response |

---

## 9. Quyết Định Thiết Kế Quan Trọng

| # | Quyết định | Lý do | Trade-off |
|---|-----------|-------|-----------|
| 1 | **Modular Monolith** thay vì microservice | Đồ án cá nhân, < 1000 users, dễ deploy | Khó scale riêng từng module |
| 2 | **CORE layer tự build** thay vì dùng DRF thuần | Thể hiện tư duy framework, giảm boilerplate | Thêm abstraction layer |
| 3 | **Tách app `srs` và `ai` riêng** | Logic phức tạp, dependency khác, dễ extract sau | Thêm config |
| 4 | **JWT auth** thay vì session | Stateless, phù hợp SPA, dễ integrate mobile sau | Cần handle refresh |
| 5 | **Soft delete** cho mọi entity | Khôi phục dữ liệu, audit trail | Query phải filter `is_deleted` |
| 6 | **3-level SRS** (EASY/GOOD/HARD) | Cân bằng giữa đơn giản và hiệu quả | Chưa chi tiết bằng SM-2 gốc |
| 7 | **AI không chấm điểm phát âm** | Ngoài scope MVP, cần tech phức tạp | Thiếu pronunciation feedback |

---

## 10. Lưu Ý Khi Phát Triển

> [!IMPORTANT]
> **Service Layer:** Mọi business logic phải nằm trong `services/`, controller chỉ xử lý request/response.

> [!WARNING]
> **AI Error Handling:** Luôn có timeout (30s) và retry (1 lần) cho AI API calls. Không để user chờ vô hạn.

- **Thứ tự triển khai gợi ý:** Auth → Learning → Flashcard + SRS → Gamification → AI
- **Seed data:** `python manage.py seed_demo` – tạo dữ liệu mẫu cho test
- **Thêm model mới:** Tạo model → serializer → normalizer → controller → route → makemigrations → migrate
- **Cache:** Cache kết quả SRS query (`due cards`) với TTL 5 phút, invalidate khi user review
- **Media:** Upload avatar/image flashcard lên S3/MinIO, lưu URL trong DB
- **Testing:** Viết unit test cho SRS algorithm trước, integration test cho API sau
