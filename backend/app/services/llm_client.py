"""LLM推論サーバークライアント"""
import json
import logging
import re
from typing import Any, Dict, List, Optional

import httpx

from ..config import settings

logger = logging.getLogger(__name__)


def sanitize_json_strings(text: str) -> str:
    """JSON文字列内のリテラル改行・制御文字をエスケープ"""
    result = []
    in_string = False
    escape_next = False
    for ch in text:
        if escape_next:
            escape_next = False
            result.append(ch)
            continue
        if ch == '\\' and in_string:
            escape_next = True
            result.append(ch)
            continue
        if ch == '"':
            in_string = not in_string
            result.append(ch)
            continue
        if in_string:
            if ch == '\n':
                result.append('\\n')
                continue
            if ch == '\r':
                continue
            if ch == '\t':
                result.append('\\t')
                continue
        result.append(ch)
    return ''.join(result)


def strip_markdown_fences(text: str) -> str:
    """マークダウンコードフェンス（```json ... ```）を除去"""
    stripped = re.sub(r"^```(?:json)?\s*\n?", "", text.strip())
    stripped = re.sub(r"\n?```\s*$", "", stripped)
    return stripped.strip()


def repair_truncated_json(text: str) -> str:
    """トランケーションされたJSONの閉じ括弧を補完（スタックベース）"""
    in_string = False
    escape_next = False
    stack = []  # 開き括弧の順序を記録

    for ch in text:
        if escape_next:
            escape_next = False
            continue
        if ch == '\\' and in_string:
            escape_next = True
            continue
        if ch == '"':
            in_string = not in_string
            continue
        if in_string:
            continue
        if ch == '{':
            stack.append('}')
        elif ch == '[':
            stack.append(']')
        elif ch in ('}', ']') and stack and stack[-1] == ch:
            stack.pop()

    # 開いている文字列を閉じる
    if in_string:
        text += '"'

    # 末尾のカンマを除去（不正なJSON防止）
    stripped = text.rstrip()
    if stripped.endswith(','):
        text = stripped[:-1]

    # 開き括弧を逆順で閉じる
    text += ''.join(reversed(stack))
    return text


def parse_llm_json(content: str) -> Optional[Dict[str, Any]]:
    """LLMレスポンスからJSONをパース（段階的修復付き）

    Returns:
        パース成功時はdict、失敗時はNone
    """
    if not content:
        return None

    cleaned = strip_markdown_fences(content)
    cleaned = sanitize_json_strings(cleaned)
    # 引用符なし・不完全なキーを修正（category: / category": → "category":）
    cleaned = re.sub(r'(?<=[\{\,\n])\s*"?(\w+)"?\s*:', r' "\1":', cleaned)
    last_error = None

    # Step 1: そのままパース
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError as e:
        last_error = e

    # Step 2: JSON部分を正規表現で抽出
    match = re.search(r'\{.*\}', cleaned, re.DOTALL)
    if match:
        try:
            return json.loads(match.group())
        except json.JSONDecodeError as e:
            last_error = e

    # Step 3: トランケーション修復
    repaired = repair_truncated_json(cleaned)
    try:
        return json.loads(repaired)
    except json.JSONDecodeError as e:
        last_error = e
        # Step 4: JSON部分抽出 + 修復
        match = re.search(r'\{.*', repaired, re.DOTALL)
        if match:
            try:
                return json.loads(repair_truncated_json(match.group()))
            except json.JSONDecodeError as e:
                last_error = e

    if last_error:
        # エラー位置の周辺を表示
        pos = last_error.pos or 0
        context = cleaned[max(0, pos - 50):pos + 50]
        logger.warning(
            f"JSONパースエラー: {last_error.msg} (位置:{pos})\n"
            f"  エラー周辺: ...{context}..."
        )

    return None


class LLMClient:
    """LLMクライアント"""

    def __init__(self):
        self._model_name: Optional[str] = None

    async def _get_model_name(self, client: httpx.AsyncClient) -> str:
        """推論サーバーからモデル名を自動検出"""
        if self._model_name:
            return self._model_name

        if settings.LLM_MODEL_NAME:
            self._model_name = settings.LLM_MODEL_NAME
            return self._model_name

        try:
            resp = await client.get(
                f"{settings.LLM_API_URL}/models",
                timeout=10.0,
            )
            resp.raise_for_status()
            data = resp.json()
            self._model_name = data["data"][0]["id"]
            logger.info(f"LLMモデル自動検出: {self._model_name}")
            return self._model_name
        except Exception as e:
            logger.error(f"モデル名取得失敗: {e}")
            raise

    async def chat_completion(
        self,
        messages: List[Dict[str, str]],
        max_tokens: int = 512,
        temperature: Optional[float] = None,
    ) -> Optional[str]:
        """チャット補完リクエストを送信

        Returns:
            レスポンス文字列。失敗時はNone。
        """
        if temperature is None:
            temperature = settings.LLM_TEMPERATURE

        try:
            async with httpx.AsyncClient() as client:
                model_name = await self._get_model_name(client)

                payload = {
                    "model": model_name,
                    "messages": messages,
                    "max_tokens": max_tokens,
                    "temperature": temperature,
                }

                resp = await client.post(
                    f"{settings.LLM_API_URL}/chat/completions",
                    json=payload,
                    timeout=settings.LLM_TIMEOUT,
                )
                resp.raise_for_status()
                data = resp.json()
                content = data["choices"][0]["message"]["content"]
                logger.debug(
                    f"LLM応答: tokens={data['usage']['completion_tokens']}, "
                    f"time={data['usage'].get('total_time', 'N/A')}"
                )
                return content

        except httpx.TimeoutException:
            logger.warning("LLMリクエストタイムアウト")
            return None
        except httpx.HTTPStatusError as e:
            logger.error(f"LLM APIエラー: {e.response.status_code}")
            return None
        except Exception as e:
            logger.error(f"LLM通信エラー: {e}")
            return None

    async def generate_json(
        self,
        messages: List[Dict[str, str]],
        max_tokens: int = 512,
        temperature: Optional[float] = None,
    ) -> Optional[Dict[str, Any]]:
        """JSON応答を生成しパースして返す

        Returns:
            パース成功時はdict、失敗時はNone
        """
        content = await self.chat_completion(
            messages=messages,
            max_tokens=max_tokens,
            temperature=temperature,
        )
        if content is None:
            return None

        parsed = parse_llm_json(content)
        if parsed is None:
            logger.warning(
                f"JSONパース失敗（{len(content)}文字）\n"
                f"  先頭: {content[:200]}\n"
                f"  末尾: {content[-200:]}"
            )
        return parsed

    async def health_check(self) -> bool:
        """LLM推論サーバーの接続確認"""
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(
                    f"{settings.LLM_API_URL}/models",
                    timeout=5.0,
                )
                return resp.status_code == 200
        except Exception:
            return False


# シングルトンインスタンス
llm_client = LLMClient()
