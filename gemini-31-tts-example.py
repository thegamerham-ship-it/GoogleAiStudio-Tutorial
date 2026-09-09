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


