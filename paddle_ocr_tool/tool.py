"""
Tool template for calling Paddle OCR HTTP endpoint.

Supports:
- infer (single image)
- infer_batch (multiple images)

Input images can be local file paths or HTTP/HTTPS URLs.
"""

import argparse
import base64
import json
import mimetypes
import os
from typing import Any, Dict, List, Literal, Optional

import requests
from pydantic import BaseModel, Field


class UserParameters(BaseModel):
    """
    Args:
        endpoint_url (str): Paddle OCR endpoint URL.
        api_key (Optional[str]): API key/JWT token for Bearer auth.
        timeout_seconds (int): HTTP timeout in seconds.
    """

    endpoint_url: str = Field(
        description="Paddle OCR endpoint URL, e.g. https://.../paddle-ocr/v1/infer"
    )
    api_key: Optional[str] = Field(
        default=None,
        description="Bearer token value (without 'Bearer ' prefix)",
    )
    timeout_seconds: int = Field(default=60, description="HTTP timeout in seconds")


class ToolParameters(BaseModel):
    action: Literal["infer", "infer_batch"] = Field(
        description="Action to perform: infer (single image) or infer_batch (multiple images)"
    )

    image_source: Optional[str] = Field(
        default=None,
        description="Single image source for infer: local path or HTTP/HTTPS URL",
    )
    image_sources: Optional[List[str]] = Field(
        default=None,
        description="List of image sources for infer_batch",
    )

    output_mode: Literal["raw", "text", "lines"] = Field(
        default="text",
        description=(
            "Output format: raw (full response JSON), text (joined OCR text), "
            "lines (structured lines with confidence)"
        ),
    )


def _guess_mime(source: str) -> str:
    mime_type, _ = mimetypes.guess_type(source)
    return mime_type or "image/png"


def _load_image_bytes(image_source: str) -> bytes:
    if image_source.startswith(("http://", "https://")):
        response = requests.get(image_source, timeout=30)
        response.raise_for_status()
        return response.content

    with open(image_source, "rb") as f:
        return f.read()


def _to_data_url(image_source: str) -> str:
    image_bytes = _load_image_bytes(image_source)
    mime_type = _guess_mime(image_source)
    encoded = base64.b64encode(image_bytes).decode("utf-8")
    return f"data:{mime_type};base64,{encoded}"


def _build_headers(config: UserParameters) -> Dict[str, str]:
    headers: Dict[str, str] = {"Content-Type": "application/json", "accept": "application/json"}
    if config.api_key:
        headers["Authorization"] = f"Bearer {config.api_key}"
    return headers


def _extract_lines_from_paddle_response(result: Any) -> List[Dict[str, Any]]:
    lines: List[Dict[str, Any]] = []

    def add_line(text: Any, confidence: Any = None):
        text_str = str(text).strip() if text is not None else ""
        if not text_str:
            return
        line: Dict[str, Any] = {"text": text_str}
        if isinstance(confidence, (int, float)):
            line["confidence"] = float(confidence)
        lines.append(line)

    # Current endpoint shape:
    # {"data":[{"text_detections":[{"text_prediction":{"text":"...","confidence":0.99}, ...}]}]}
    if isinstance(result, dict) and isinstance(result.get("data"), list):
        for item in result["data"]:
            if not isinstance(item, dict):
                continue
            text_detections = item.get("text_detections")
            if not isinstance(text_detections, list):
                continue
            for detection in text_detections:
                if not isinstance(detection, dict):
                    continue
                prediction = detection.get("text_prediction", {})
                if isinstance(prediction, dict):
                    add_line(prediction.get("text"), prediction.get("confidence"))
        return lines

    # Fallback shapes.
    if isinstance(result, list):
        for item in result:
            if isinstance(item, dict) and "text" in item:
                add_line(item.get("text"), item.get("confidence"))
            elif isinstance(item, list) and len(item) >= 2:
                candidate = item[1]
                if isinstance(candidate, (list, tuple)) and len(candidate) >= 1:
                    confidence = candidate[1] if len(candidate) > 1 else None
                    add_line(candidate[0], confidence)
        return lines

    if isinstance(result, dict):
        if isinstance(result.get("output"), list):
            for item in result["output"]:
                if isinstance(item, dict) and "text" in item:
                    add_line(item.get("text"), item.get("confidence"))
        elif isinstance(result.get("text"), str):
            add_line(result.get("text"))
        elif isinstance(result.get("result"), str):
            add_line(result.get("result"))

    return lines


def _format_output(result: Any, output_mode: str) -> str:
    if output_mode == "raw":
        return json.dumps(result, indent=2, ensure_ascii=False)

    lines = _extract_lines_from_paddle_response(result)

    if output_mode == "lines":
        return json.dumps({"line_count": len(lines), "lines": lines}, indent=2, ensure_ascii=False)

    # output_mode == "text"
    text = "\n".join(line["text"] for line in lines)
    return text if text else ""


def _call_paddle(config: UserParameters, image_sources: List[str]) -> Any:
    payload = {
        "input": [
            {
                "type": "image_url",
                "url": _to_data_url(source),
            }
            for source in image_sources
        ]
    }
    headers = _build_headers(config)

    response = requests.post(
        config.endpoint_url,
        headers=headers,
        json=payload,
        timeout=config.timeout_seconds,
    )
    response.raise_for_status()
    return response.json()


def run_tool(config: UserParameters, args: ToolParameters) -> str:
    try:
        if args.action == "infer":
            if not args.image_source:
                return "Error: 'image_source' is required for action='infer'."
            if not args.image_source.startswith(("http://", "https://")) and not os.path.exists(args.image_source):
                return f"Error: image file not found: {args.image_source}"

            result = _call_paddle(config, [args.image_source])
            return _format_output(result, args.output_mode)

        if args.action == "infer_batch":
            if not args.image_sources:
                return "Error: 'image_sources' is required for action='infer_batch'."

            for source in args.image_sources:
                if not source.startswith(("http://", "https://")) and not os.path.exists(source):
                    return f"Error: image file not found: {source}"

            result = _call_paddle(config, args.image_sources)
            return _format_output(result, args.output_mode)

        return f"Error: Unsupported action '{args.action}'."

    except requests.exceptions.RequestException as e:
        return f"Paddle OCR request failed: {str(e)}"
    except Exception as e:
        return f"Tool execution failed: {str(e)}"


OUTPUT_KEY = "tool_output"


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--user-params", required=True, help="JSON string for tool configuration")
    parser.add_argument("--tool-params", required=True, help="JSON string for tool arguments")
    cli_args = parser.parse_args()

    user_params_dict = json.loads(cli_args.user_params)
    tool_params_dict = json.loads(cli_args.tool_params)

    config = UserParameters(**user_params_dict)
    params = ToolParameters(**tool_params_dict)

    output = run_tool(config, params)
    print(OUTPUT_KEY, output)

