import os
import re
import json
import csv
from datetime import datetime
import mimetypes
from pathlib import Path
from typing import Optional, List, Dict, Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import yt_dlp
from google import genai
from google.genai import types
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent
DOWNLOAD_DIR = BASE_DIR / "downloads"
STATIC_DIR = BASE_DIR / "static"
CACHE_CSV_PATH = BASE_DIR / "transcripts_cache.csv"

DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)
STATIC_DIR.mkdir(parents=True, exist_ok=True)

CSV_FIELDNAMES = [
    "video_id",
    "url",
    "title",
    "channel",
    "duration",
    "thumbnail",
    "segments_json",
    "entities_json",
    "full_text",
    "created_at",
]


def init_csv_cache():
    """CSV 캐시 파일 초기화 및 기존 파일 컬럼 마이그레이션"""
    if not CACHE_CSV_PATH.exists():
        with open(CACHE_CSV_PATH, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.DictWriter(f, fieldnames=CSV_FIELDNAMES)
            writer.writeheader()
    else:
        # 기존 CSV 파일에 entities_json 컬럼이 없으면 마이그레이션
        try:
            with open(CACHE_CSV_PATH, "r", newline="", encoding="utf-8-sig") as f:
                reader = csv.DictReader(f)
                fieldnames = reader.fieldnames or []
                if "entities_json" not in fieldnames:
                    rows = list(reader)
                    for r in rows:
                        if "entities_json" not in r:
                            r["entities_json"] = "[]"
                    with open(CACHE_CSV_PATH, "w", newline="", encoding="utf-8-sig") as fw:
                        writer = csv.DictWriter(fw, fieldnames=CSV_FIELDNAMES)
                        writer.writeheader()
                        for r in rows:
                            # 새 필드만 필터링하여 기록
                            cleaned_row = {k: r.get(k, "") for k in CSV_FIELDNAMES}
                            writer.writerow(cleaned_row)
        except Exception as e:
            print(f"[CSV Migration Warning] {e}")


init_csv_cache()


def get_cached_transcript(video_id: str) -> Optional[dict]:
    """CSV 캐시 파일에서 해당 video_id의 트랜스크립트 및 핵심 색인 데이터 탐색"""
    if not CACHE_CSV_PATH.exists():
        return None

    try:
        with open(CACHE_CSV_PATH, "r", newline="", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row.get("video_id") == video_id:
                    entities_raw = row.get("entities_json", "[]")
                    try:
                        entities = json.loads(entities_raw) if entities_raw else []
                    except Exception:
                        entities = []

                    return {
                        "video_id": row["video_id"],
                        "url": row.get("url", ""),
                        "title": row.get("title", ""),
                        "channel": row.get("channel", ""),
                        "duration": int(row.get("duration", 0) or 0),
                        "thumbnail": row.get("thumbnail", ""),
                        "segments": json.loads(row.get("segments_json", "[]")),
                        "entities": entities,
                        "full_text": row.get("full_text", ""),
                        "created_at": row.get("created_at", ""),
                        "from_cache": True,
                    }
    except Exception as e:
        print(f"[CSV Cache Error] 캐시 조회 중 오류: {e}")
    return None


def save_transcript_to_cache(data: dict):
    """트랜스크립트 및 핵심 색인 분석 결과를 CSV 캐시 파일에 추가 저장"""
    init_csv_cache()
    try:
        row = {
            "video_id": data.get("video_id", ""),
            "url": data.get("url", ""),
            "title": data.get("title", ""),
            "channel": data.get("channel", ""),
            "duration": data.get("duration", 0),
            "thumbnail": data.get("thumbnail", ""),
            "segments_json": json.dumps(data.get("segments", []), ensure_ascii=False),
            "entities_json": json.dumps(data.get("entities", []), ensure_ascii=False),
            "full_text": data.get("full_text", ""),
            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }
        with open(CACHE_CSV_PATH, "a", newline="", encoding="utf-8-sig") as f:
            writer = csv.DictWriter(f, fieldnames=CSV_FIELDNAMES)
            writer.writerow(row)
        print(f"[CSV Cache Saved] '{row['title']}' 캐시 저장 완료 (-> transcripts_cache.csv)")
    except Exception as e:
        print(f"[CSV Cache Error] 캐시 저장 중 오류: {e}")


app = FastAPI(title="AI YouTube Searcher & Navigator", version="2.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


class ProcessRequest(BaseModel):
    url: str


class ChatRequest(BaseModel):
    question: str
    video_id: str
    transcript_summary: str
    segments: List[Dict[str, Any]] = []
    entities: List[Dict[str, Any]] = []


def extract_youtube_video_id(url: str) -> Optional[str]:
    """유튜브 링크에서 11자리 비디오 ID 추출"""
    patterns = [
        r"(?:v=|\/)([0-9A-Za-z_-]{11}).*",
        r"(?:embed\/|shorts\/|youtu\.be\/)([0-9A-Za-z_-]{11})",
    ]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    return None


def format_seconds(seconds: float) -> str:
    """초 단위를 MM:SS 형식으로 변환"""
    mins = int(seconds // 60)
    secs = int(seconds % 60)
    return f"{mins:02d}:{secs:02d}"


def get_audio_mime_type(file_path: Path) -> str:
    ext = file_path.suffix.lower()
    mime_map = {
        ".m4a": "audio/mp4",
        ".mp3": "audio/mp3",
        ".wav": "audio/wav",
        ".webm": "audio/webm",
        ".ogg": "audio/ogg",
        ".opus": "audio/ogg",
    }
    return mime_map.get(ext, mimetypes.guess_type(str(file_path))[0] or "audio/mp4")


def download_audio_stream(url: str) -> dict:
    """yt-dlp로 오디오 스트림 다운로드 및 메타데이터 추출"""
    ydl_opts = {
        "format": "m4a/bestaudio/best",
        "outtmpl": str(DOWNLOAD_DIR / "%(id)s.%(ext)s"),
        "noplaylist": True,
        "quiet": True,
        "no_warnings": True,
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            if info is None:
                raise ValueError("영상 정보를 불러올 수 없습니다.")

            video_id = info.get("id")
            title = info.get("title", "제목 없음")
            duration = info.get("duration", 0)
            thumbnail = info.get("thumbnail", "")
            channel = info.get("uploader", "알 수 없음")

            downloaded_files = list(DOWNLOAD_DIR.glob(f"{video_id}.*"))
            if not downloaded_files:
                raise FileNotFoundError("오디오 다운로드에 실패했습니다.")

            audio_file = downloaded_files[0]

            return {
                "id": video_id,
                "title": title,
                "duration": duration,
                "thumbnail": thumbnail,
                "channel": channel,
                "audio_path": audio_file,
            }
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"유튜브 다운로드 실패: {str(e)}"
        )


def transcribe_audio_detailed(audio_path: Path) -> dict:
    """Gemini를 활용하여 범용 핵심 색인(Entities/Chapters)과 전체 세부 대사를 구조화하여 동시 추출"""
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise HTTPException(status_code=500, detail="GEMINI_API_KEY 환경변수가 설정되지 않았습니다.")

    client = genai.Client(api_key=api_key)
    file_size = audio_path.stat().st_size
    mime_type = get_audio_mime_type(audio_path)

    try:
        if file_size > 20 * 1024 * 1024:
            audio_part = client.files.upload(file=str(audio_path))
        else:
            with open(audio_path, "rb") as f:
                audio_bytes = f.read()
            audio_part = types.Part.from_bytes(data=audio_bytes, mime_type=mime_type)

        prompt = """당신은 영상 및 오디오 심층 분석 전문가입니다.
주어진 오디오를 면밀히 청취 및 분석하여, 영상의 범용 핵심 색인/주제/등장요소(Entities & Chapters)와 전체 세부 대사(Transcript)를 추출해주세요.
특정 도메인(포켓몬, 건담 등)에 국한되지 않고, 요리, 테크 리뷰, 강의, 인터뷰, 대화 등 다양한 영상 장르에 맞춰 핵심 개체나 챕터/단계를 유연하게 식별해야 합니다.

반드시 아래 JSON 스키마 형식으로만 응답해주세요:
{
  "entities": [
    {
      "time_str": "00:00",
      "seconds": 0,
      "title": "주제/개체/챕터/인물/단계 이름",
      "summary": "해당 구간에 대한 명확한 핵심 1줄 설명"
    }
  ],
  "segments": [
    {
      "timestamp": "00:00",
      "start_seconds": 0,
      "speaker": "화자명",
      "text": "정확한 발화 대사 내용"
    }
  ]
}

[지침]
1. entities (핵심 색인 목록):
   - 영상의 흐름에 따라 등장하는 주요 대상(포켓몬/캐릭터, 인물, 제품명, 조리 단계/재료, 핵심 화두/소주제 등)을 시간 순서대로 3~8개 내외로 식별하세요.
   - time_str은 'MM:SS' 형식, seconds는 정수 초 단위여야 합니다.
   - 만약 영상이 매우 짧거나 단일 주제라 별도 소주제가 없다면 핵심 키워드 1~2개만 포함하세요.
2. segments (전체 대사 전문):
   - 영상에서 발화된 모든 음성(한국어, 영어, 인터뷰, 영화 대사, 배경 발화, 나레이션)을 빠짐없이 타임스탬프와 함께 기록하세요.
"""

        # 1차 시도: Gemini 구조화 JSON 출력 (entities + segments)
        try:
            response = client.models.generate_content(
                model="gemini-3.8-flash",
                contents=[audio_part, prompt],
                config=types.GenerateContentConfig(response_mime_type="application/json"),
            )

            if response.text:
                data = json.loads(response.text)
                entities = data.get("entities", [])
                segments = data.get("segments", [])

                # entities seconds 보정
                for e in entities:
                    if "seconds" not in e and "time_str" in e:
                        parts = e["time_str"].split(":")
                        try:
                            e["seconds"] = int(parts[0]) * 60 + int(parts[1])
                        except Exception:
                            e["seconds"] = 0

                # segments start_seconds 보정
                full_text_list = []
                for s in segments:
                    if "start_seconds" not in s and "timestamp" in s:
                        parts = s["timestamp"].split(":")
                        try:
                            s["start_seconds"] = int(parts[0]) * 60 + int(parts[1])
                        except Exception:
                            s["start_seconds"] = 0
                    full_text_list.append(f"[{s.get('timestamp', '00:00')}] [{s.get('speaker', '화자')}] {s.get('text', '')}")

                if len(segments) >= 3:
                    return {
                        "entities": entities,
                        "segments": segments,
                        "full_text": "\n".join(full_text_list),
                    }
        except Exception as json_err:
            print(f"[JSON Extraction Fallback] {json_err}")

        # 2차 시도 (텍스트 전사 파싱 Fallback)
        text_prompt = (
            "당신은 오디오 분석 전문가입니다. 오디오의 모든 음성을 타임스탬프와 함께 빠짐없이 기록해주세요.\n"
            "형식: [MM:SS] [화자] 대사 내용"
        )
        res_text = client.models.generate_content(
            model="gemini-3.8-flash",
            contents=[audio_part, text_prompt],
        )

        segments = []
        full_text_list = []
        if res_text.text:
            lines = [l.strip() for l in res_text.text.split("\n") if l.strip()]
            for line in lines:
                match = re.match(r"\[?(\d{1,2}:\d{2})\]?\s*(?:\[([^\]]+)\])?\s*(.+)", line)
                if match:
                    ts_str = match.group(1)
                    speaker_str = match.group(2) or "화자"
                    text_str = match.group(3).strip()
                    parts = ts_str.split(":")
                    try:
                        sec = int(parts[0]) * 60 + int(parts[1])
                    except ValueError:
                        sec = 0

                    segments.append({
                        "start_seconds": sec,
                        "timestamp": ts_str,
                        "speaker": speaker_str,
                        "text": text_str,
                    })
                    full_text_list.append(f"[{ts_str}] [{speaker_str}] {text_str}")

        return {
            "entities": [],
            "segments": segments,
            "full_text": "\n".join(full_text_list) or "트랜스크립트 내용이 없습니다.",
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"음성 전사 및 색인 추출 오류: {str(e)}"
        )


@app.get("/")
def index():
    index_file = STATIC_DIR / "index.html"
    if index_file.exists():
        return FileResponse(str(index_file))
    return {"message": "AI YouTube Searcher API is running."}


@app.post("/api/process")
def process_video(req: ProcessRequest):
    """1. 유튜브 영상 로드 및 트랜스크립트·핵심 색인 추출 (CSV 캐시 우선 조회)"""
    url = req.url.strip()
    if not url:
        raise HTTPException(status_code=400, detail="유튜브 URL을 입력해주세요.")

    video_id = extract_youtube_video_id(url)
    if not video_id:
        raise HTTPException(status_code=400, detail="올바른 유튜브 링크 형식이 아닙니다.")

    # 1. [CSV 캐시 확인] 이전에 이미 분석하여 CSV에 저장된 데이터가 있는지 확인
    cached_data = get_cached_transcript(video_id)
    if cached_data:
        print(f"[CACHE HIT] CSV 캐시에서 즉시 불러왔습니다: {cached_data.get('title')} ({video_id})")
        return {
            "success": True,
            "from_cache": True,
            **cached_data,
        }

    # 2. [신규 분석] 캐시가 없으면 오디오 다운로드 & Gemini 분석 진행
    print(f"[CACHE MISS] 신규 영상 분석 시작: {url}")
    info = download_audio_stream(url)

    # 3. Gemini를 통한 고정밀 타임스탬프, 세부 대사 및 범용 핵심 색인(Entities) 추출
    transcribe_result = transcribe_audio_detailed(info["audio_path"])

    result_payload = {
        "video_id": info["id"],
        "url": url,
        "title": info["title"],
        "duration": info["duration"],
        "thumbnail": info["thumbnail"],
        "channel": info["channel"],
        "entities": transcribe_result.get("entities", []),
        "segments": transcribe_result.get("segments", []),
        "full_text": transcribe_result.get("full_text", ""),
    }

    # 4. [CSV 캐시 저장] 다음 번 빠른 로딩을 위해 CSV 파일에 영구 저장
    save_transcript_to_cache(result_payload)

    return {
        "success": True,
        "from_cache": False,
        **result_payload,
    }


@app.post("/api/chat")
def chat_with_video(req: ChatRequest):
    """2. gemini-3.8-flash 모델을 사용하여 트랜스크립트 및 핵심 색인 기반 질의응답 및 위치 찾기"""
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise HTTPException(status_code=500, detail="GEMINI_API_KEY 환경변수가 설정되지 않았습니다.")

    client = genai.Client(api_key=api_key)

    # 핵심 색인 컨텍스트 구성
    entity_lines = []
    for e in req.entities:
        entity_lines.append(f"- [{e.get('time_str', '00:00')}] {e.get('title', '')}: {e.get('summary', '')}")
    entity_context = "\n".join(entity_lines) if entity_lines else "추출된 별도 색인 없음"

    # 타임스탬프 자막 컨텍스트 구성
    context_lines = []
    for s in req.segments:
        context_lines.append(f"[{s.get('timestamp')}] ({s.get('start_seconds')}초) {s.get('speaker', '')}: {s.get('text', '')}")

    transcript_context = "\n".join(context_lines) if context_lines else req.transcript_summary

    system_prompt = (
        "당신은 스마트 유튜브 영상 탐색 및 핵심 내용 분석 어시스턴트입니다.\n"
        "제공된 영상의 [핵심 색인/챕터 목록]과 [타임스탬프 자막(Transcript)]을 바탕으로 사용자의 질문에 정확하고 친절하게 답변해주세요.\n\n"
        "[중요 규칙]\n"
        "1. 사용자가 특정 내용, 장면, 인물, 대사, 주제를 물어보거나 찾을 경우, 반드시 해당 발화 지점의 타임스탬프를 `[MM:SS]` 형식으로 본문에 명시하세요.\n"
        "2. 답변에 언급된 타임스탬프는 사용자가 클릭하여 영상의 해당 위치로 바로 이동(`seekTo`)할 수 있습니다.\n"
        "3. 만약 자막에 없는 내용이라면 지어내지 말고 자막에 언급되지 않았다고 솔직히 말해주세요.\n"
        "4. 한국어로 가독성 높게 마크다운 서식을 활용하여 답변해주세요.\n\n"
        f"[영상 핵심 색인/주제]\n{entity_context}\n\n"
        f"[영상 자막 데이터]\n{transcript_context}"
    )

    try:
        response = client.models.generate_content(
            model="gemini-3.8-flash",
            contents=[system_prompt, f"사용자 질문: {req.question}"],
        )

        answer_text = response.text or "답변을 생성할 수 없습니다."

        # 응답 텍스트에서 시간 태그 [MM:SS] 또는 MM:SS 탐색하여 타임스탬프 목록 추출
        found_timestamps = []
        matches = re.findall(r"\[?(\d{1,2}:\d{2})\]?", answer_text)
        for m in matches:
            parts = m.split(":")
            try:
                seconds = int(parts[0]) * 60 + int(parts[1])
                found_timestamps.append({"label": m, "seconds": seconds})
            except ValueError:
                pass

        return {
            "success": True,
            "answer": answer_text,
            "timestamps": found_timestamps,
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Gemini 3.8 Flash 질의응답 실패: {str(e)}"
        )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="127.0.0.1", port=8001, reload=True)
