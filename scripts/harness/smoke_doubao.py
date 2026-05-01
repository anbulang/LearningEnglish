from __future__ import annotations

import json
import os
import base64
import struct
import zlib
from pathlib import Path

import httpx


PROJECT_ROOT = Path(__file__).resolve().parents[2]
ENV_FILE = PROJECT_ROOT / "infra" / ".env"


def main() -> int:
    env = _load_env_file(ENV_FILE)
    api_key = env.get("ARK_API_KEY", "")
    base_url = env.get("ARK_BASE_URL", "https://ark.cn-beijing.volces.com/api/v3").rstrip("/")
    vision_model = env.get("DOUBAO_VISION_MODEL_OR_ENDPOINT", "")
    text_model = env.get("DOUBAO_TEXT_MODEL_OR_ENDPOINT", "")
    if not api_key or not vision_model or not text_model:
        print("missing_config")
        print("required: ARK_API_KEY, DOUBAO_VISION_MODEL_OR_ENDPOINT, DOUBAO_TEXT_MODEL_OR_ENDPOINT")
        return 2

    client = httpx.Client(timeout=60, trust_env=False)
    try:
        text_content = _chat(
            client,
            api_key=api_key,
            base_url=base_url,
            model=text_model,
            messages=[
                {"role": "system", "content": "只输出 json。"},
                {"role": "user", "content": '请返回 {"ok": true, "provider": "doubao"}'},
            ],
        )
        print("text_ok")
        print(_short(text_content))

        vision_content = _chat(
            client,
            api_key=api_key,
            base_url=base_url,
            model=vision_model,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": '请判断图片是否可见，只输出 json：{"image_visible": true} 或 {"image_visible": false}',
                        },
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:image/png;base64,{_sample_png_base64()}"},
                        },
                    ],
                }
            ],
        )
        print("vision_ok")
        print(_short(vision_content))
    finally:
        client.close()
    return 0


def _chat(
    client: httpx.Client,
    *,
    api_key: str,
    base_url: str,
    model: str,
    messages: list[dict],
) -> str:
    response = client.post(
        f"{base_url}/chat/completions",
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        json={"model": model, "messages": messages, "temperature": 0.1, "response_format": {"type": "json_object"}},
    )
    try:
        response.raise_for_status()
    except httpx.HTTPStatusError as exc:
        print(f"request_failed status={response.status_code} model={model}")
        print(_short(response.text))
        raise exc
    payload = response.json()
    return payload["choices"][0]["message"]["content"]


def _load_env_file(path: Path) -> dict[str, str]:
    values = dict(os.environ)
    if not path.exists():
        return values
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def _short(value: str) -> str:
    compact = " ".join(value.split())
    return compact[:500]


def _sample_png_base64() -> str:
    width = 32
    height = 32
    raw_rows = []
    for y in range(height):
        row = bytearray([0])
        for x in range(width):
            row.extend((240, 132 if (x + y) % 2 == 0 else 210, 96))
        raw_rows.append(bytes(row))
    raw = b"".join(raw_rows)
    png = (
        b"\x89PNG\r\n\x1a\n"
        + _png_chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))
        + _png_chunk(b"IDAT", zlib.compress(raw))
        + _png_chunk(b"IEND", b"")
    )
    return base64.b64encode(png).decode("ascii")


def _png_chunk(chunk_type: bytes, data: bytes) -> bytes:
    return (
        struct.pack(">I", len(data))
        + chunk_type
        + data
        + struct.pack(">I", zlib.crc32(chunk_type + data) & 0xFFFFFFFF)
    )


if __name__ == "__main__":
    raise SystemExit(main())
