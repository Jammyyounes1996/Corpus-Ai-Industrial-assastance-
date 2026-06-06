import argparse
import asyncio
import base64
import json
import sys
import tempfile
from pathlib import Path

import httpx
from sqlalchemy import update

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.database.database import async_session_maker
from backend.database.models import OCRResult


def parse_sse_events(response: httpx.Response) -> list[dict]:
    events: list[dict] = []
    current_event = None
    current_data_lines: list[str] = []

    for line in response.iter_lines():
        if line is None:
            continue
        text = line.strip()
        if text == "":
            if current_event:
                data_text = "\n".join(current_data_lines) if current_data_lines else "{}"
                try:
                    payload = json.loads(data_text)
                except json.JSONDecodeError:
                    payload = {"raw": data_text}
                events.append({"event": current_event, "data": payload})
            current_event = None
            current_data_lines = []
            continue

        if text.startswith("event:"):
            current_event = text.split(":", 1)[1].strip()
        elif text.startswith("data:"):
            current_data_lines.append(text.split(":", 1)[1].strip())

    return events


def unwrap_payload(data: dict) -> dict:
    if isinstance(data, dict) and "data" in data and isinstance(data["data"], dict):
        return data["data"]
    return data if isinstance(data, dict) else {}


def stream_chat(base_url: str, chat_id: str, query: str, attached_files: list[str]) -> dict:
    url = f"{base_url}/api/chat/{chat_id}/stream"
    payload = {
        "query": query,
        "model_provider": "ollama",
        "model_name": "gemma4:latest",
        "attached_files": attached_files,
    }

    with httpx.stream("POST", url, json=payload, timeout=180.0) as resp:
        resp.raise_for_status()
        events = parse_sse_events(resp)

    answer_tokens: list[str] = []
    done_chat_id = ""
    sources_payload: dict = {}

    for event in events:
        if event["event"] == "token":
            token_data = unwrap_payload(event.get("data", {}))
            token = token_data.get("token") or token_data.get("content") or ""
            answer_tokens.append(token)
        elif event["event"] == "done":
            done_data = unwrap_payload(event.get("data", {}))
            done_chat_id = str(done_data.get("chat_id", ""))
        elif event["event"] == "sources":
            sources_payload = unwrap_payload(event.get("data", {}))
        elif event["event"] == "error":
            err = unwrap_payload(event.get("data", {})).get("error") or event.get("data")
            raise RuntimeError(f"Stream returned error event: {err}")

    return {
        "events": events,
        "answer": "".join(answer_tokens),
        "done_chat_id": done_chat_id,
        "sources": sources_payload.get("sources", []) if isinstance(sources_payload, dict) else [],
    }


def create_chat(base_url: str, title: str) -> str:
    resp = httpx.post(f"{base_url}/api/chats", json={"title": title}, timeout=30.0)
    resp.raise_for_status()
    return str(resp.json()["id"])


def generate_test_image(file_path: Path) -> None:
    tiny_png_b64 = (
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8Xw8AAoMBgQfM9m0AAAAASUVORK5CYII="
    )
    file_path.write_bytes(base64.b64decode(tiny_png_b64))


def upload_image(base_url: str, image_path: Path) -> dict:
    with image_path.open("rb") as image_file:
        files = {"file": (image_path.name, image_file, "image/png")}
        resp = httpx.post(f"{base_url}/api/ingest/image", files=files, timeout=120.0)
    resp.raise_for_status()
    return resp.json()


async def force_ocr_text(file_id: str, forced_text: str) -> None:
    async with async_session_maker() as session:
        await session.execute(
            update(OCRResult)
            .where(OCRResult.file_id == file_id)
            .values(extracted_text=forced_text)
        )
        await session.commit()


def run_t099(base_url: str) -> None:
    secret = "TURBOPUMP-9917"
    chat_id = create_chat(base_url, "T099 validation")

    first = stream_chat(
        base_url,
        chat_id,
        f"Remember this code exactly: {secret}. Reply with code only.",
        [],
    )
    done_chat_id = first["done_chat_id"] or chat_id

    second = stream_chat(
        base_url,
        done_chat_id,
        "What code did I ask you to remember? Reply with code only.",
        [],
    )

    if secret not in second["answer"]:
        raise AssertionError(
            "T099 failed: follow-up answer did not preserve prior context. "
            f"Expected code '{secret}' in answer: {second['answer']}"
        )

    print("T099 PASS: Multi-turn context preserved.")


def run_t100(base_url: str) -> None:
    ocr_text = "OCR-CHECK-31415"
    with tempfile.TemporaryDirectory() as tmp_dir:
        image_path = Path(tmp_dir) / "t100_ocr_check.png"
        generate_test_image(image_path)
        ingest = upload_image(base_url, image_path)

    file_id = str(ingest["file_id"])
    filename = str(ingest.get("filename", ""))
    asyncio.run(force_ocr_text(file_id, ocr_text))
    chat_id = create_chat(base_url, "T100 validation")

    result = stream_chat(
        base_url,
        chat_id,
        "Read the attached image and return the exact text in it.",
        [file_id],
    )

    answer = result["answer"]
    if ocr_text not in answer:
        raise AssertionError(
            "T100 failed: OCR text was not incorporated into answer. "
            f"Expected '{ocr_text}' in answer: {answer}"
        )

    sources = result["sources"]
    source_blob = json.dumps(sources).lower()
    if file_id.lower() not in source_blob and filename.lower() not in source_blob and "ocr" not in source_blob:
        raise AssertionError(
            "T100 failed: sources do not include evidence of attached image/OCR. "
            f"Sources: {sources}"
        )

    print("T100 PASS: Attached image OCR used in answer and sources.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate T099 and T100 automation.")
    parser.add_argument("--base-url", default="http://127.0.0.1:8011", help="Backend base URL")
    args = parser.parse_args()

    run_t099(args.base_url)
    run_t100(args.base_url)
    print("ALL PASS: T099 and T100 validations completed successfully.")


if __name__ == "__main__":
    main()
