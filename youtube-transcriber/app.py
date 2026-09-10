import os
import re
import mimetypes
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, HttpUrl
import yt_dlp
from google import genai
from google.genai import types
from dotenv import load_dotenv

# 환경변수 로드
load_dotenv()

BASE_DIR = Path(__file__).resolve().parent
DOWNLOAD_DIR = BASE_DIR / "downloads"
STATIC_DIR = BASE_DIR / "static"

# 필수 디렉터리 생성
DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)
STATIC_DIR.mkdir(parents=True, exist_ok=True)

app = FastAPI(title="YouTube Audio Transcriber", version="1.0.0")

# CORS 허용
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 정적 파일 서빙
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


class TranscribeRequest(BaseModel):
    url: str
    model: Optional[str] = "gemini-3.6-flash"


def get_audio_mime_type(file_path: Path) -> str:
    """확장자에 따른 오디오 MIME 타입 반환"""
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


def download_youtube_audio(url: str) -> dict:
    """yt-dlp를 이용해 유튜브 영상에서 오디오 추출 및 메타데이터 반환"""
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
                raise ValueError("영상 정보를 가져올 수 없습니다.")

            video_id = info.get("id")
            title = info.get("title", "제목 없음")
            duration = info.get("duration", 0)
            thumbnail = info.get("thumbnail", "")
            channel = info.get("uploader", "알 수 없음")

            # 실제 저장된 오디오 파일 찾기
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
                "file_path": audio_file,
                "file_name": audio_file.name,
            }
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"유튜브 오디오 다운로드 중 오류 발생: {str(e)}",
        )


def transcribe_audio_with_gemini(audio_path: Path, model_name: str = "gemini-3.6-flash") -> str:
    """Gemini API를 호출하여 오디오 트랜스크립트 및 요약 추출"""
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise HTTPException(
            status_code=500,
            detail="GEMINI_API_KEY 환경변수가 설정되지 않았습니다.",
        )

    # 구형/지원 중단된 모델명 자동 보정
    if "2.5-flash" in model_name or "2.0-flash" in model_name:
        model_name = "gemini-3.6-flash"

    client = genai.Client(api_key=api_key)
    file_size = audio_path.stat().st_size
    mime_type = get_audio_mime_type(audio_path)

    try:
        # 20MB를 초과하는 대용량 파일은 File API로 업로드, 이하는 인라인 바이트 전달
        if file_size > 20 * 1024 * 1024:
            print(f"[Gemini] 대용량 파일 ({file_size / (1024 * 1024):.1f}MB) 업로드 중...")
            audio_content = client.files.upload(file=str(audio_path))
        else:
            print(f"[Gemini] 오디오 바이트 인라인 전달 ({file_size / 1024:.1f}KB)...")
            with open(audio_path, "rb") as f:
                audio_bytes = f.read()
            audio_content = types.Part.from_bytes(data=audio_bytes, mime_type=mime_type)

        prompt = (
            "당신은 오디오 분석 및 전문 음성 전사(Transcription) 전문가입니다. "
            "주어진 오디오 음성을 면밀히 청취하고 한국어로 가독성 높게 트랜스크립트를 작성해주세요.\n\n"
            "반드시 아래 마크다운 양식에 맞추어 출력해주세요:\n"
            "### 📌 핵심 요약 (Summary)\n"
            "- 영상의 핵심 주제와 요점을 3~5줄로 명확하게 요약\n\n"
            "### ⏱️ 타임스탬프 & 주요 맥락 (Timestamps)\n"
            "- [00:00] 주요 장면 또는 발화 요약\n"
            "- [분:초] 형식으로 시간 순서대로 기록\n\n"
            "### 📜 전체 대사 전문 (Full Transcript)\n"
            "(화자 구분이 가능하다면 [화자 1], [화자 2] 등으로 표시하고, 실제 발화된 모든 대사를 누락 없이 상세히 기록)"
        )

        response = client.models.generate_content(
            model=model_name,
            contents=[audio_content, prompt],
        )

        # 1. response.text가 있는 경우 (gemini-3.6-flash 등 LLM 모델)
        if response.text and response.text.strip():
            return response.text.strip()

        # 2. parts에 audio_transcription 객체가 있는 경우 (gemini-3.5-transcribe 전용 모델 등)
        extracted_texts = []
        if response.candidates:
            for candidate in response.candidates:
                if not candidate.content or not candidate.content.parts:
                    continue
                for part in candidate.content.parts:
                    if getattr(part, "text", None):
                        extracted_texts.append(part.text)
                    elif getattr(part, "audio_transcription", None):
                        at = part.audio_transcription
                        text_val = getattr(at, "text", "")
                        speaker = f"[{at.speaker_label}] " if getattr(at, "speaker_label", None) else ""
                        if text_val:
                            extracted_texts.append(f"{speaker}{text_val}")

        if extracted_texts:
            return "\n\n".join(extracted_texts).strip()

        return "트랜스크립트 생성 결과가 비어 있습니다."
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Gemini 음성 전사 처리 중 오류 발생: {str(e)}",
        )


@app.get("/")
def index():
    """메인 웹 UI 페이지 서빙"""
    index_file = STATIC_DIR / "index.html"
    if index_file.exists():
        return FileResponse(str(index_file))
    return {"message": "YouTube Audio Transcriber API is running."}


@app.post("/api/transcribe")
def transcribe(req: TranscribeRequest):
    """유튜브 URL을 받아 오디오 다운로드 후 트랜스크립트 반환"""
    url = req.url.strip()
    if not url:
        raise HTTPException(status_code=400, detail="유튜브 URL을 입력해주세요.")

    # 1. 유튜브 오디오 다운로드
    info = download_youtube_audio(url)

    # 2. Gemini STT 전사 추출
    transcript = transcribe_audio_with_gemini(info["file_path"], req.model or "gemini-2.5-flash")

    return {
        "success": True,
        "id": info["id"],
        "title": info["title"],
        "duration": info["duration"],
        "thumbnail": info["thumbnail"],
        "channel": info["channel"],
        "audio_url": f"/api/audio/{info['file_name']}",
        "transcript": transcript,
    }


@app.get("/api/audio/{filename}")
def get_audio(filename: str):
    """다운로드된 오디오 파일 스트리밍 서빙 (브라우저 플레이어 재생용)"""
    file_path = DOWNLOAD_DIR / filename
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="오디오 파일을 찾을 수 없습니다.")

    mime_type = get_audio_mime_type(file_path)
    return FileResponse(str(file_path), media_type=mime_type, filename=filename)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="127.0.0.1", port=8000, reload=True)
