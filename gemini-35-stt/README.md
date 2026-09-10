# Gemini 3.5 Transcribe STT (Speech-to-Text) 코드 라인별 해설서

이 문서는 Google AI Studio에서 제공하는 최신 음성 전사(STT) 모델인 `gemini-3.5-transcribe`를 사용하여 로컬 WAV 음성 파일(`output.wav`)을 텍스트로 변환하고 단어별 타임스탬프와 화자 분리(Diarization) 결과를 출력하는 [gemini-35-stt-example.py](gemini-35-stt-example.py)의 **Line-by-Line(한 줄 한 줄)** 상세 해설서입니다.

---

## 1. 전체 소스 코드

```python
# To run this code you need to install the following dependencies:
# pip install google-genai

import base64
import os
from google import genai
from google.genai import types


def generate():
    client = genai.Client(
        api_key=os.environ.get("GEMINI_API_KEY"),
    )

    model = "gemini-3.5-transcribe"
    audio_path = "output.wav"
    if not os.path.exists(audio_path):
        raise FileNotFoundError(f"'{audio_path}' 파일을 찾을 수 없습니다. 경로를 확인해주세요.")

    with open(audio_path, "rb") as f:
        audio_bytes = f.read()

    contents = [
        types.Content(
            role="user",
            parts=[
                types.Part.from_bytes(
                    data=audio_bytes,
                    mime_type="audio/wav",
                ),
            ],
        ),
    ]
    generate_content_config = types.GenerateContentConfig(
        audio_transcription_config=types.AudioTranscriptionConfig(
            word_timestamp=True,
            diarization=True,
        ),
    )

    for chunk in client.models.generate_content_stream(
        model=model,
        contents=contents,
        config=generate_content_config,
    ):
        if text := chunk.text:
            print(text, end="")

if __name__ == "__main__":
    generate()
```

---

## 2. Line-by-Line 상세 해설

### 📌 1~8행: 의존성 주석 및 라이브러리 임포트
```python
1: # To run this code you need to install the following dependencies:
2: # pip install google-genai
3: 
4: import base64
5: import os
6: from google import genai
7: from google.genai import types
```
* **Line 1~2:** 필요한 공식 Google GenAI 라이브러리(`google-genai`) 설치 안내 주석입니다.
* **Line 4 (`base64`):** 바이너리 인코딩/디코딩 모듈입니다.
* **Line 5 (`os`):** 운영체제 파일 경로 검사(`os.path.exists`) 및 시스템 환경변수(`GEMINI_API_KEY`) 로드를 위해 사용합니다.
* **Line 6~7 (`genai`, `types`):** 최신 공식 구글 SDK의 클라이언트 및 전송 데이터 객체 규격(Content, Part, Config 등)을 임포트합니다.

---

### 📌 10~13행: 메인 함수 정의 및 API 클라이언트 초기화
```python
10: def generate():
11:     client = genai.Client(
12:         api_key=os.environ.get("GEMINI_API_KEY"),
13:     )
```
* **Line 10:** STT 처리를 수행할 `generate()` 함수를 정의합니다.
* **Line 11~13:** `genai.Client` 인스턴스를 초기화합니다. `api_key=os.environ.get("GEMINI_API_KEY")`를 통해 시스템 환경변수에 등록된 API 키를 읽어와 인증을 통과합니다.

---

### 📌 15~22행: 모델 지정 및 음성 파일(`output.wav`) 바이너리 로드
```python
15:     model = "gemini-3.5-transcribe"
16:     audio_path = "output.wav"
17:     if not os.path.exists(audio_path):
18:         raise FileNotFoundError(f"'{audio_path}' 파일을 찾을 수 없습니다. 경로를 확인해주세요.")
19: 
20:     with open(audio_path, "rb") as f:
21:         audio_bytes = f.read()
```
* **Line 15:** 구글의 고성능 전사(STT) 전용 모델인 `"gemini-3.5-transcribe"`를 모델명으로 지정합니다.
* **Line 16:** 인식할 음성 파일 경로(`"output.wav"`)를 변수에 저장합니다.
* **Line 17~18 (`os.path.exists`):** 전사할 파일이 현재 폴더에 존재하는지 사전에 검증합니다. 만약 파일이 없다면 명확한 에러 메시지와 함께 실행을 중단하여 디버깅을 돕습니다.
* **Line 20~21 (`with open(..., "rb")`):** `output.wav` 파일을 **바이너리 읽기 모드(`"rb"`)**로 열어 순수 바이트 데이터(`audio_bytes`)를 메모리로 읽어옵니다.

---

### 📌 23~33행: 모델 입력 페이로드 구성 (`contents`)
```python
23:     contents = [
24:         types.Content(
25:             role="user",
26:             parts=[
27:                 types.Part.from_bytes(
28:                     data=audio_bytes,
29:                     mime_type="audio/wav",
30:                 ),
31:             ],
32:         ),
33:     ]
```
* **Line 23~26:** 사용자 역할(`user`)의 멀티모달 컨텐츠 객체를 생성합니다.
* **Line 27~30 (`types.Part.from_bytes`):** 바이너리 데이터를 직접 모델 입력으로 넘기는 핵심 메서드입니다:
  * `data=audio_bytes`: 위에서 읽어온 순수 WAV 음성 바이트 데이터입니다.
  * `mime_type="audio/wav"`: 데이터의 포맷이 표준 WAV 오디오임을 선언합니다.

---

### 📌 34~39행: STT 전용 고급 옵션 구성 (`GenerateContentConfig`)
```python
34:     generate_content_config = types.GenerateContentConfig(
35:         audio_transcription_config=types.AudioTranscriptionConfig(
36:             word_timestamp=True,
37:             diarization=True,
38:         ),
39:     )
```
* **Line 34~35:** 일반 텍스트 생성이 아닌 **음성 전사 전용 설정(`AudioTranscriptionConfig`)**을 적용합니다.
* **Line 36 (`word_timestamp=True`):** 단순 텍스트 변환뿐만 아니라, **각 단어가 오디오의 몇 초(시작~끝)에 발화되었는지 정확한 타임스탬프 정보**를 함께 반환하도록 요청합니다.
* **Line 37 (`diarization=True`):** **화자 분리(Speaker Diarization)** 기능입니다. 오디오 속 목소리가 여러 명일 경우 화자 1(Speaker 1), 화자 2(Speaker 2) 등으로 구분하여 전사합니다.

---

### 📌 41~47행: 실시간 스트리밍 전사 결과 수신 및 출력
```python
41:     for chunk in client.models.generate_content_stream(
42:         model=model,
43:         contents=contents,
44:         config=generate_content_config,
45:     ):
46:         if text := chunk.text:
47:             print(text, end="")
```
* **Line 41~45:** `client.models.generate_content_stream(...)`을 호출하여 API가 음성을 실시간으로 인식하면서 생성되는 텍스트 결과를 스트리밍 형태로 전송받습니다.
* **Line 46~47 (`walrus operator :=`):** `chunk.text`에 내용이 존재하면 변수 `text`에 할당하고, `end=""` 옵션을 주어 줄바꿈 없이 콘솔에 실시간 타이핑되듯 즉시 출력합니다.

---

### 📌 49~50행: 실행 진입점 (`__main__`)
```python
49: if __name__ == "__main__":
50:     generate()
```
* **Line 49~50:** 파이썬 파일이 직접 실행(`python gemini-35-stt-example.py`)될 때 `generate()` 함수를 호출하여 STT 음성 인식을 실행합니다.
