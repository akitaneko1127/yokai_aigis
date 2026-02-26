"""VOICEVOX TTSクライアント"""
import hashlib
import logging
import re
from collections import OrderedDict
from typing import Optional

import httpx

from ..config import settings

logger = logging.getLogger(__name__)

# 妖怪ID → VOICEVOX speaker_id マッピング
YOUKAI_SPEAKER_MAP: dict[str, int] = {
    "kappa": 42,           # ちび式じい ノーマル
    "namazu": 13,          # 青山龍星 ノーマル
    "tsuchigumo": 52,      # 雀松朱司 ノーマル
    "tengu": 53,           # 麒ヶ島宗麟 ノーマル
    "kasha": 1,            # ずんだもん あまあま
    "yukionna": 2,         # 四国めたん ノーマル
    "hinokagutsuchi": 11,  # 玄野武宏 ノーマル
}

DEFAULT_SPEAKER_ID = 2  # フォールバック: 四国めたん ノーマル


class TTSClient:
    """VOICEVOX TTSクライアント（LRUキャッシュ付き）"""

    def __init__(self):
        self._cache: OrderedDict[str, bytes] = OrderedDict()

    @staticmethod
    def get_speaker_id(youkai_id: str) -> int:
        """妖怪IDからVOICEVOX speaker_idを取得"""
        return YOUKAI_SPEAKER_MAP.get(youkai_id, DEFAULT_SPEAKER_ID)

    @staticmethod
    def _cache_key(text: str, speaker_id: int) -> str:
        """キャッシュキーを生成（text+speaker_idのハッシュ）"""
        raw = f"{speaker_id}:{text}"
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    @staticmethod
    def _strip_parenthesized(text: str) -> str:
        """カッコ内のテキストを除去（読み上げ不要な注釈・ト書きなど）"""
        # 全角（）と半角() の両方に対応
        text = re.sub(r'（[^）]*）', '', text)
        text = re.sub(r'\([^)]*\)', '', text)
        # 連続する空白を1つに
        return re.sub(r' {2,}', ' ', text).strip()

    async def synthesize(self, text: str, speaker_id: int) -> Optional[bytes]:
        """テキストからWAV音声を合成（2段階API: audio_query → synthesis）

        Returns:
            WAVバイナリ。失敗時はNone。
        """
        # カッコ内を除去して読み上げ用テキストを作成
        speech_text = self._strip_parenthesized(text)
        if not speech_text.strip():
            return None

        # キャッシュ確認
        key = self._cache_key(text, speaker_id)
        if key in self._cache:
            self._cache.move_to_end(key)
            logger.debug("TTSキャッシュヒット: speaker=%d, len=%d", speaker_id, len(text))
            return self._cache[key]

        try:
            async with httpx.AsyncClient() as client:
                # Step 1: audio_query（音声合成用クエリの作成）
                query_resp = await client.post(
                    f"{settings.TTS_API_URL}/audio_query",
                    params={"text": speech_text, "speaker": speaker_id},
                    timeout=settings.TTS_TIMEOUT,
                )
                query_resp.raise_for_status()
                audio_query = query_resp.json()

                # Step 2: synthesis（音声合成の実行）
                synth_resp = await client.post(
                    f"{settings.TTS_API_URL}/synthesis",
                    params={"speaker": speaker_id},
                    json=audio_query,
                    timeout=settings.TTS_TIMEOUT,
                )
                synth_resp.raise_for_status()
                wav_data = synth_resp.content

            # キャッシュに保存（LRU: 最大サイズを超えたら古いものから削除）
            self._cache[key] = wav_data
            if len(self._cache) > settings.TTS_CACHE_MAX_SIZE:
                self._cache.popitem(last=False)

            logger.info(
                "TTS合成成功: speaker=%d, text_len=%d, wav_size=%d",
                speaker_id, len(text), len(wav_data),
            )
            return wav_data

        except httpx.TimeoutException:
            logger.warning("TTSリクエストタイムアウト: speaker=%d", speaker_id)
            return None
        except httpx.HTTPStatusError as e:
            logger.error("TTS APIエラー: %d %s", e.response.status_code, e.response.text[:200])
            return None
        except Exception as e:
            logger.error("TTS通信エラー: %s", e)
            return None

    async def health_check(self) -> bool:
        """VOICEVOXエンジンの接続確認"""
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(
                    f"{settings.TTS_API_URL}/speakers",
                    timeout=5.0,
                )
                return resp.status_code == 200
        except Exception:
            return False


# シングルトンインスタンス
tts_client = TTSClient()
