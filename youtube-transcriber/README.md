# 🎙️ YouTube Audio Transcriber & Summarizer Web Service

유튜브 영상 URL을 입력하면 고음질 오디오를 자동으로 추출·다운로드하고, **Google Gemini API**를 활용하여 **핵심 요약, 타임스탬프, 전체 대사 전문(트랜스크립트)**을 생성해 주는 풀스택 웹 서비스입니다.

---

## 🌟 주요 기능

1. **유튜브 오디오 자동 추출 (`yt-dlp`)**
   - 유튜브 영상 링크(`youtube.com`, `youtu.be`)를 입력하면 최적의 오디오 스트림(`m4a`/`mp3` 등)을 자동 다운로드.
   - 영상 제목, 썸네일, 재생 시간 등 메타데이터 자동 파싱.
2. **Gemini AI 고정밀 음성 전사 (STT)**
   - `gemini-2.5-flash` 모델을 기본 사용하여 초고속 응답 및 한국어/다국어 완벽 지원.
   - 단순 텍스트 변환뿐만 아니라 **핵심 요약(Summary)**과 **시간별 타임스탬프([00:00])**를 구조화하여 제공.
   - 20MB 이하 오디오는 인라인 전송, 20MB 초과 대용량 파일은 Gemini File API로 자동 전환하여 파일 크기 제한 극복.
3. **편리한 웹 대시보드 UI**
   - **오디오 플레이어**: 추출된 오디오를 브라우저에서 바로 청취 가능.
   - **1-Click 복사 & 다운로드**: 트랜스크립트 텍스트 복사 및 `.txt` 파일 다운로드 기능.

---

## 📂 디렉터리 구조

```text
youtube-transcriber/
├── app.py                 # FastAPI 백엔드 (yt-dlp 오디오 다운로더 & Gemini STT 엔드포인트)
├── static/
│   └── index.html         # TailwindCSS 기반 반응형 모던 웹 UI
├── downloads/             # 다운로드된 오디오 파일 저장소
├── requirements.txt       # 필수 파이썬 패키지 목록
└── README.md              # 프로젝트 가이드
```

---

## 🚀 실행 방법

### 1. 가상환경 활성화 및 패키지 설치
```bash
conda activate myenv
pip install -r requirements.txt
```

### 2. Gemini API Key 환경변수 확인
시스템 환경변수에 `GEMINI_API_KEY`가 등록되어 있거나, 상위 폴더 또는 현재 폴더의 `.env` 파일에 아래와 같이 등록되어 있어야 합니다:
```env
GEMINI_API_KEY="your_api_key_here"
```

### 3. 웹 서버 실행
```bash
cd youtube-transcriber
python app.py
```
또는
```bash
uvicorn app:app --host 127.0.0.1 --port 8000 --reload
```

### 4. 웹 브라우저 접속
브라우저 주소창에 아래 주소를 입력하고 접속합니다:
👉 **[http://localhost:8000](http://localhost:8000)**

---

## 🛠️ API 엔드포인트

* `GET /`: 웹 대시보드 UI (`static/index.html`)
* `POST /api/transcribe`: 유튜브 URL을 전송하여 오디오 다운로드 및 트랜스크립트 생성
  * Request: `{"url": "https://www.youtube.com/watch?v=...", "model": "gemini-2.5-flash"}`
  * Response: `{"success": true, "title": "...", "duration": 120, "audio_url": "/api/audio/...", "transcript": "..."}`
* `GET /api/audio/{filename}`: 다운로드된 오디오 파일 스트리밍 서빙
