# Gemini 3.1 Flash TTS (Text-to-Speech) 코드 라인별 해설서

이 문서는 Google AI Studio에서 제공하는 음성 합성 모델인 `gemini-3.1-flash-tts-preview`를 사용하여 텍스트 대본을 고품질 WAV 음성 파일로 생성하는 [gemini-31-tts-example.py](gemini-31-tts-example.py)의 **Line-by-Line(한 줄 한 줄)** 상세 해설서입니다.

---

## 1. 전체 소스 코드

```python
# To run this code you need to install the following dependencies:
# pip install google-genai

import mimetypes
import os
import re
import struct
from google import genai
from google.genai import types


def save_binary_file(file_name, data):
    f = open(file_name, "wb")
    f.write(data)
    f.close()
    print(f"File saved to to: {file_name}")


def generate():
    client = genai.Client(
        api_key=os.environ.get("GEMINI_API_KEY"),
    )

    model = "gemini-3.1-flash-tts-preview"
    contents = [
        types.Content(
            role="user",
            parts=[
                types.Part.from_text(text="""Read the following transcript based on the audio profile.

# Audio Profile
warm

## Scene:
A professional high-tech news studio with breaking news graphics and alert chimes playing in the background.

## Sample Context:
The news anchor is urgently cutting in to report a shocking price disruption announcement from Google in the AI industry.

## Transcript:
[urgent] 테크 긴급 속보입니다! [excited] 구글이 차세대 플래그십 모델인 '제미나이 4.0 Pro'를 전격 공개했습니다. 

[astonished] 그런데 놀라운 점은 성능뿐만이 아닙니다. 이번 제미나이 4.0 Pro의 가격이 기존 1.5 Pro 모델 대비 무려 90% 이상 대폭 인하된 파격적인 수준으로 책정되었습니다! 

[confident] 고성능 멀티모달 추론 능력을 갖추고도 백만 토큰당 단 몇 센트에 불과한 요금 체계를 선보이면서, 업계에서는 'AI 가격 파괴의 정점'이라는 반응이 쏟아지고 있습니다. [chuckles] 이제 누구나 부담 없이 최첨단 프론티어 AI를 구축할 수 있게 되었습니다."""),
            ],
        ),
    ]
    generate_content_config = types.GenerateContentConfig(
        temperature=1,
        response_modalities=[
            "audio",
        ],
        speech_config=types.SpeechConfig(
            voice_config=types.VoiceConfig(
                prebuilt_voice_config=types.PrebuiltVoiceConfig(
                    voice_name="Kore"
                )
            )
        ),
    )

    audio_chunks = []
    mime_type = "audio/wav"

    for chunk in client.models.generate_content_stream(
        model=model,
        contents=contents,
        config=generate_content_config,
    ):
        if chunk.parts is None:
            continue
        for part in chunk.parts:
            if part.inline_data and part.inline_data.data:
                audio_chunks.append(part.inline_data.data)
                if part.inline_data.mime_type:
                    mime_type = part.inline_data.mime_type
            elif part.text:
                print(part.text)

    # 스트리밍이 완료된 후 하나로 합쳐서 1개의 파일로 저장
    if audio_chunks:
        full_audio_data = b"".join(audio_chunks)
        file_name = "output"  # 원하는 파일명으로 변경 가능
        file_extension = mimetypes.guess_extension(mime_type)
        if file_extension is None:
            file_extension = ".wav"
            full_audio_data = convert_to_wav(full_audio_data, mime_type)
        save_binary_file(f"{file_name}{file_extension}", full_audio_data)

def convert_to_wav(audio_data: bytes, mime_type: str) -> bytes:
    """Generates a WAV file header for the given audio data and parameters.

    Args:
        audio_data: The raw audio data as a bytes object.
        mime_type: Mime type of the audio data.

    Returns:
        A bytes object representing the WAV file header.
    """
    parameters = parse_audio_mime_type(mime_type)
    bits_per_sample = parameters["bits_per_sample"]
    sample_rate = parameters["rate"]
    num_channels = 1
    data_size = len(audio_data)
    bytes_per_sample = bits_per_sample // 8
    block_align = num_channels * bytes_per_sample
    byte_rate = sample_rate * block_align
    chunk_size = 36 + data_size  # 36 bytes for header fields before data chunk size

    # http://soundfile.sapp.org/doc/WaveFormat/

    header = struct.pack(
        "<4sI4s4sIHHIIHH4sI",
        b"RIFF",          # ChunkID
        chunk_size,       # ChunkSize (total file size - 8 bytes)
        b"WAVE",          # Format
        b"fmt ",          # Subchunk1ID
        16,               # Subchunk1Size (16 for PCM)
        1,                # AudioFormat (1 for PCM)
        num_channels,     # NumChannels
        sample_rate,      # SampleRate
        byte_rate,        # ByteRate
        block_align,      # BlockAlign
        bits_per_sample,  # BitsPerSample
        b"data",          # Subchunk2ID
        data_size         # Subchunk2Size (size of audio data)
    )
    return header + audio_data

def parse_audio_mime_type(mime_type: str) -> dict[str, int]:
    """Parses bits per sample and rate from an audio MIME type string.

    Assumes bits per sample is encoded like "L16" and rate as "rate=xxxxx".

    Args:
        mime_type: The audio MIME type string (e.g., "audio/L16;rate=24000").

    Returns:
        A dictionary with "bits_per_sample" and "rate" keys. Values will be
        integers if found, otherwise None.
    """
    bits_per_sample = 16
    rate = 24000

    # Extract rate from parameters
    parts = mime_type.split(";")
    for param in parts: # Skip the main type part
        param = param.strip()
        if param.lower().startswith("rate="):
            try:
                rate_str = param.split("=", 1)[1]
                rate = int(rate_str)
            except (ValueError, IndexError):
                # Handle cases like "rate=" with no value or non-integer value
                pass # Keep rate as default
        elif param.startswith("audio/L"):
            try:
                bits_per_sample = int(param.split("L", 1)[1])
            except (ValueError, IndexError):
                pass # Keep bits_per_sample as default if conversion fails

    return {"bits_per_sample": bits_per_sample, "rate": rate}


if __name__ == "__main__":
    generate()
```

---

## 2. Line-by-Line 상세 해설

### 📌 1~10행: 라이브러리 임포트 (Dependencies)
```python
1: # To run this code you need to install the following dependencies:
2: # pip install google-genai
3: 
4: import mimetypes
5: import os
6: import re
7: import struct
8: from google import genai
9: from google.genai import types
```
* **Line 1~2:** 필요한 외부 패키지(`google-genai`) 설치 안내 주석입니다.
* **Line 4 (`mimetypes`):** MIME 타입(예: `audio/wav`)을 기반으로 표준 확장자(`.wav`)를 추론하는 파이썬 표준 라이브러리입니다.
* **Line 5 (`os`):** 운영체제의 환경변수(`GEMINI_API_KEY`)를 읽어오기 위해 사용합니다.
* **Line 6 (`re`):** 정규표현식 모듈입니다.
* **Line 7 (`struct`):** C 구조체 형태의 이진 바이너리 데이터(WAV 헤더 등)를 생성/패킹할 때 사용하는 필수 모듈입니다.
* **Line 8~9 (`genai`, `types`):** 최신 구글 공식 GenAI SDK의 클라이언트 및 데이터 규격(타입) 모듈입니다.

---

### 📌 12~16행: 바이너리 파일 저장 함수 (`save_binary_file`)
```python
12: def save_binary_file(file_name, data):
13:     f = open(file_name, "wb")
14:     f.write(data)
15:     f.close()
16:     print(f"File saved to to: {file_name}")
```
* **Line 12:** 파일 이름과 이진 데이터(`bytes`)를 인자로 받아 파일로 저장하는 헬퍼 함수를 정의합니다.
* **Line 13:** `open(file_name, "wb")`로 파일을 엽니다. `"wb"`는 **Write Binary(이진 쓰기 모드)**를 의미하며, 텍스트가 아닌 음성/이미지 바이트 데이터를 쓸 때 필수적입니다.
* **Line 14:** 전달받은 오디오 바이트(`data`)를 파일에 기록합니다.
* **Line 15:** 파일 핸들을 닫아 리소스를 안전하게 반환합니다.
* **Line 16:** 콘솔에 저장이 완료된 파일 경로를 출력합니다.

---

### 📌 19~23행: 생성 메인 함수 및 클라이언트 초기화
```python
19: def generate():
20:     client = genai.Client(
21:         api_key=os.environ.get("GEMINI_API_KEY"),
22:     )
```
* **Line 19:** TTS 생성을 담당하는 메인 진입 함수 `generate()`를 정의합니다.
* **Line 20~22:** `genai.Client` 인스턴스를 생성합니다. `os.environ.get("GEMINI_API_KEY")`를 통해 시스템 환경변수에 등록된 구글 API 키를 안전하게 불러와 인증합니다.

---

### 📌 24~48행: 모델 지정 및 프롬프트 대본 구성 (`contents`)
```python
24:     model = "gemini-3.1-flash-tts-preview"
25:     contents = [
26:         types.Content(
27:             role="user",
28:             parts=[
29:                 types.Part.from_text(text="""Read the following transcript based on the audio profile.
...
41: ## Transcript:
42: [urgent] 테크 긴급 속보입니다! [excited] 구글이 차세대 플래그십 모델인 '제미나이 4.0 Pro'를 전격 공개했습니다. 
...
45: [confident] 고성능 멀티모달 추론 능력을 갖추고도..."""),
28:             ],
29:         ),
30:     ]
```
* **Line 24:** 음성 합성에 특화된 프리뷰 모델 `gemini-3.1-flash-tts-preview`를 지정합니다.
* **Line 25~28:** 사용자 역할(`user`)의 메시지를 `types.Content` 규격으로 포장합니다.
* **Line 29~45:** AI Studio의 음성 지시어(Prompt)입니다:
  * `# Audio Profile warm`: 따뜻하고 신뢰감 있는 목소리 톤을 지정합니다.
  * `## Scene`: 뉴스 스튜디오 배경 분위기를 제공합니다.
  * `## Sample Context`: 앵커가 긴급 속보를 전하는 긴박한 맥락을 전달합니다.
  * `## Transcript`: 실제 발화할 대본이며, 대괄호 태그(`[urgent]`, `[excited]`, `[astonished]`, `[confident]`, `[chuckles]`)를 통해 각 문장마다 세밀한 감정과 호흡을 부여합니다.

---

### 📌 49~61행: 음성 생성 설정 (`GenerateContentConfig`)
```python
49:     generate_content_config = types.GenerateContentConfig(
50:         temperature=1,
51:         response_modalities=[
52:             "audio",
53:         ],
54:         speech_config=types.SpeechConfig(
55:             voice_config=types.VoiceConfig(
56:                 prebuilt_voice_config=types.PrebuiltVoiceConfig(
57:                     voice_name="Kore"
58:                 )
59:             )
60:         ),
61:     )
```
* **Line 50 (`temperature=1`):** 음성의 억양과 감정 표현의 다양성 수준을 지정합니다.
* **Line 51~53 (`response_modalities=["audio"]`):** 텍스트 답변이 아닌 **순수 오디오 바이너리**를 응답으로 반환하도록 강제합니다.
* **Line 54~60 (`speech_config`):** 발화할 프리셋 음성 캐릭터를 지정합니다. 여기서는 부드럽고 명확한 여성/뉴스 톤의 `"Kore"` 음성을 사용합니다.

---

### 📌 63~80행: 스트리밍 오디오 조각(Chunk) 수집
```python
63:     audio_chunks = []
64:     mime_type = "audio/wav"
65: 
66:     for chunk in client.models.generate_content_stream(
67:         model=model,
68:         contents=contents,
69:         config=generate_content_config,
70:     ):
71:         if chunk.parts is None:
72:             continue
73:         for part in chunk.parts:
74:             if part.inline_data and part.inline_data.data:
75:                 audio_chunks.append(part.inline_data.data)
76:                 if part.inline_data.mime_type:
77:                     mime_type = part.inline_data.mime_type
78:             elif part.text:
79:                 print(part.text)
```
* **Line 63~64:** 스트리밍으로 전달되는 오디오 바이트 조각들을 임시 저장할 `audio_chunks` 리스트와 MIME 타입 기본값을 초기화합니다.
* **Line 66~70:** `client.models.generate_content_stream(...)`을 호출하여 오디오 조각을 실시간 스트리밍으로 받습니다.
* **Line 71~72:** 청크에 내용(`parts`)이 없는 빈 패킷이면 건너뜁니다.
* **Line 73~77:** 각 파트에 `inline_data`와 `data`(바이너리 PCM 바이트)가 포함되어 있다면, **파일로 즉시 쓰지 않고 리스트(`audio_chunks`)에 추가(`append`)**합니다. (수백 개의 쪼개진 파일 생성을 방지하는 핵심 로직)
* **Line 78~79:** 모델이 반환한 텍스트 로그가 있다면 콘솔에 출력합니다.

---

### 📌 81~89행: 단일 오디오 파일 병합 및 저장
```python
81:     # 스트리밍이 완료된 후 하나로 합쳐서 1개의 파일로 저장
82:     if audio_chunks:
83:         full_audio_data = b"".join(audio_chunks)
84:         file_name = "output"  # 원하는 파일명으로 변경 가능
85:         file_extension = mimetypes.guess_extension(mime_type)
86:         if file_extension is None:
87:             file_extension = ".wav"
88:             full_audio_data = convert_to_wav(full_audio_data, mime_type)
89:         save_binary_file(f"{file_name}{file_extension}", full_audio_data)
```
* **Line 82:** 수집된 오디오 바이트 조각이 존재하는지 확인합니다.
* **Line 83 (`b"".join(audio_chunks)`):** 수십 개로 쪼개져 수신된 원시 PCM 오디오 바이트들을 하나로 매끄럽게 이어 붙입니다.
* **Line 84~85:** 저장할 파일명(`"output"`)과 확장자를 MIME 타입으로부터 추론합니다.
* **Line 86~88:** 만약 표준 확장자가 없는 원시 PCM 스트림(`audio/L16`)인 경우, 기본 확장자를 `.wav`로 지정하고 `convert_to_wav()` 함수를 호출하여 규격에 맞는 **WAV 44바이트 헤더**를 앞단에 씌워줍니다.
* **Line 89:** 완성된 단일 무결성 오디오 데이터를 `output.wav` 파일로 저장합니다.

---

### 📌 91~130행: WAV 헤더 생성 및 결합 (`convert_to_wav`)
```python
91: def convert_to_wav(audio_data: bytes, mime_type: str) -> bytes:
...
101:     parameters = parse_audio_mime_type(mime_type)
102:     bits_per_sample = parameters["bits_per_sample"]
103:     sample_rate = parameters["rate"]
104:     num_channels = 1
105:     data_size = len(audio_data)
106:     bytes_per_sample = bits_per_sample // 8
107:     block_align = num_channels * bytes_per_sample
108:     byte_rate = sample_rate * block_align
109:     chunk_size = 36 + data_size
```
* **Line 101~103:** 오디오 MIME 정보로부터 샘플당 비트 수(예: 16-bit)와 샘플링 레이트(예: 24,000Hz)를 추출합니다.
* **Line 104~109:** 표준 PCM WAV 파일 규격에 필요한 메타데이터(채널 수 1개(모노), 데이터 크기, 바이트 레이트 등)를 연산합니다.

```python
114:     header = struct.pack(
115:         "<4sI4s4sIHHIIHH4sI",
116:         b"RIFF",          # ChunkID
117:         chunk_size,       # ChunkSize (total file size - 8 bytes)
118:         b"WAVE",          # Format
119:         b"fmt ",          # Subchunk1ID
120:         16,               # Subchunk1Size (16 for PCM)
121:         1,                # AudioFormat (1 for PCM)
122:         num_channels,     # NumChannels
123:         sample_rate,      # SampleRate
124:         byte_rate,        # ByteRate
125:         block_align,      # BlockAlign
126:         bits_per_sample,  # BitsPerSample
127:         b"data",          # Subchunk2ID
128:         data_size         # Subchunk2Size (size of audio data)
129:     )
130:     return header + audio_data
```
* **Line 114~129:** `struct.pack`의 리틀 엔디언(`"<"`) 포맷을 사용하여 44바이트의 표준 RIFF/WAV 헤더를 생성하고, 순수 오디오 데이터(`audio_data`)와 결합(`header + audio_data`)하여 어디서든 재생 가능한 완성형 WAV 바이너리를 반환합니다.

---

### 📌 131~163행: MIME 타입 파싱 (`parse_audio_mime_type`)
```python
131: def parse_audio_mime_type(mime_type: str) -> dict[str, int]:
...
139:     bits_per_sample = 16
140:     rate = 24000
141: 
142:     # Extract rate from parameters
143:     parts = mime_type.split(";")
144:     for param in parts:
...
```
* **Line 131:** 반환 타입을 `dict[str, int]`로 명시하여 파이썬 정적 타입 분석기(Pyrefly)와의 호환성을 보장합니다.
* **Line 139~140:** 정보가 없을 때 적용할 기본 오디오 스펙(16-bit, 24kHz)을 설정합니다.
* **Line 143~161:** `"audio/L16;rate=24000"`과 같은 문자열을 세미콜론(`;`) 단위로 쪼개어 비트수(16)와 재생 주파수(24000)를 안전하게 정수로 추출합니다.

---

### 📌 166~167행: 실행 진입점 (`__main__`)
```python
166: if __name__ == "__main__":
167:     generate()
```
* **Line 166~167:** 해당 파이썬 스크립트가 직접 실행(`python gemini-31-tts-example.py`)될 때 `generate()` 함수를 호출하여 음성 합성을 시작합니다.
