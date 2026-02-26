import { useState, useEffect, useCallback, useMemo, useRef } from 'react';
import type { YoukaiMessage } from '../types';
import { getYoukaiExpressionImage, getYoukaiDefaultExpression, getYoukaiImageByName } from '../data/youkaiImages';
import { api } from '../services/api';

interface YoukaiConversationProps {
  messages: YoukaiMessage[];
  autoOpen?: boolean;
}

const DEFAULT_CHAR_MS = 30;       // TTS無効時のデフォルト速度
const AUDIO_FETCH_TIMEOUT = 8000; // 音声取得の最大待ち時間

export function YoukaiConversation({ messages, autoOpen = false }: YoukaiConversationProps) {
  const [currentIndex, setCurrentIndex] = useState(0);
  const [isOpen, setIsOpen] = useState(false);
  const [displayedText, setDisplayedText] = useState('');
  const [isTyping, setIsTyping] = useState(false);
  const [hasAutoOpened, setHasAutoOpened] = useState(false);
  const [waitingAudio, setWaitingAudio] = useState(false);

  // TTS状態
  const [ttsEnabled, setTtsEnabled] = useState(true);
  const [isAudioPlaying, setIsAudioPlaying] = useState(false);
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const audioUrlsRef = useRef<Map<number, string>>(new Map());
  const fetchingRef = useRef<Set<number>>(new Set());
  // 音声のdurationキャッシュ (index → seconds)
  const audioDurationsRef = useRef<Map<number, number>>(new Map());

  // autoOpen: 結果表示時に自動で劇場を開く
  useEffect(() => {
    if (autoOpen && !hasAutoOpened && messages.length > 0) {
      setCurrentIndex(0);
      setIsOpen(true);
      setHasAutoOpened(true);
    }
  }, [autoOpen, hasAutoOpened, messages.length]);

  // 会話に登場するユニークなキャラクター一覧（登場順）
  const characters = useMemo(() => {
    const seen = new Set<string>();
    const list: { name: string; emoji: string }[] = [];
    for (const msg of messages) {
      if (!seen.has(msg.speaker_name)) {
        seen.add(msg.speaker_name);
        list.push({ name: msg.speaker_name, emoji: msg.speaker_emoji });
      }
    }
    return list;
  }, [messages]);

  const currentMsg = messages[currentIndex];

  // 音声URLフェッチ（Promise返却、durationも取得してキャッシュ）
  const fetchAudio = useCallback((index: number): Promise<string | null> => {
    // 既にキャッシュ済み
    if (audioUrlsRef.current.has(index)) {
      return Promise.resolve(audioUrlsRef.current.get(index)!);
    }
    if (index < 0 || index >= messages.length) return Promise.resolve(null);

    // 既にフェッチ中なら完了を待つ
    if (fetchingRef.current.has(index)) {
      return new Promise((resolve) => {
        const check = setInterval(() => {
          if (!fetchingRef.current.has(index)) {
            clearInterval(check);
            resolve(audioUrlsRef.current.get(index) ?? null);
          }
        }, 50);
        // タイムアウト
        setTimeout(() => { clearInterval(check); resolve(null); }, AUDIO_FETCH_TIMEOUT);
      });
    }

    const msg = messages[index];
    fetchingRef.current.add(index);

    return api.synthesizeSpeech(msg.text, msg.speaker)
      .then(url => {
        audioUrlsRef.current.set(index, url);
        // durationを取得
        return new Promise<string>((resolve) => {
          const audio = new Audio(url);
          audio.addEventListener('loadedmetadata', () => {
            if (audio.duration && isFinite(audio.duration)) {
              audioDurationsRef.current.set(index, audio.duration);
            }
            resolve(url);
          });
          audio.addEventListener('error', () => resolve(url));
          // loadedmetadataが発火しない場合のフォールバック
          setTimeout(() => resolve(url), 2000);
        });
      })
      .catch(() => null)
      .finally(() => { fetchingRef.current.delete(index); });
  }, [messages]);

  // 先読み（次のメッセージをバックグラウンドでフェッチ）
  const prefetchNext = useCallback((index: number) => {
    const next = index + 1;
    if (next < messages.length && !audioUrlsRef.current.has(next) && !fetchingRef.current.has(next)) {
      fetchAudio(next);
    }
  }, [messages.length, fetchAudio]);

  // 音声再生（Promiseで完了を通知）
  const playAudio = useCallback((index: number): Promise<void> => {
    const url = audioUrlsRef.current.get(index);
    if (!url) return Promise.resolve();

    // 既存の再生を停止
    if (audioRef.current) {
      audioRef.current.pause();
      audioRef.current.currentTime = 0;
    }

    return new Promise((resolve) => {
      const audio = new Audio(url);
      audioRef.current = audio;
      setIsAudioPlaying(true);

      const done = () => {
        setIsAudioPlaying(false);
        resolve();
      };
      audio.onended = done;
      audio.onerror = done;
      audio.play().catch(done);
    });
  }, []);

  // 音声停止
  const stopAudio = useCallback(() => {
    if (audioRef.current) {
      audioRef.current.pause();
      audioRef.current.currentTime = 0;
      setIsAudioPlaying(false);
    }
  }, []);

  // メインの演出ループ: 音声待ち → 音声+テキスト同時開始
  useEffect(() => {
    if (!isOpen || !currentMsg) return;

    let cancelled = false;
    let typingInterval: ReturnType<typeof setInterval> | null = null;

    const run = async () => {
      const text = currentMsg.text;
      setDisplayedText('');
      setIsTyping(false);

      if (ttsEnabled) {
        // 音声フェッチを待つ
        setWaitingAudio(true);
        const url = await fetchAudio(currentIndex);
        if (cancelled) return;
        setWaitingAudio(false);

        // 次のメッセージを先読み
        prefetchNext(currentIndex);

        if (url) {
          // duration から1文字あたりの表示速度を計算
          const duration = audioDurationsRef.current.get(currentIndex);
          const charMs = duration
            ? Math.max(10, Math.min(80, (duration * 1000) / text.length))
            : DEFAULT_CHAR_MS;

          // 音声再生開始 + テキスト送り同時開始
          setIsTyping(true);
          let i = 0;

          // 音声再生（非同期、待たない）
          playAudio(currentIndex);

          typingInterval = setInterval(() => {
            if (cancelled) { clearInterval(typingInterval!); return; }
            i++;
            setDisplayedText(text.slice(0, i));
            if (i >= text.length) {
              clearInterval(typingInterval!);
              typingInterval = null;
              setIsTyping(false);
            }
          }, charMs);

          return;
        }
      }

      // TTS無効 or 音声取得失敗: デフォルト速度でテキスト送り
      prefetchNext(currentIndex);
      setIsTyping(true);
      let i = 0;
      typingInterval = setInterval(() => {
        if (cancelled) { clearInterval(typingInterval!); return; }
        i++;
        setDisplayedText(text.slice(0, i));
        if (i >= text.length) {
          clearInterval(typingInterval!);
          typingInterval = null;
          setIsTyping(false);
        }
      }, DEFAULT_CHAR_MS);
    };

    run();

    return () => {
      cancelled = true;
      if (typingInterval) clearInterval(typingInterval);
    };
  }, [currentIndex, isOpen, currentMsg, ttsEnabled, fetchAudio, prefetchNext, playAudio]);

  const handleAdvance = useCallback(() => {
    if (waitingAudio) {
      // 音声待ち中はスキップ不可（まだテキストも始まっていない）
      return;
    }
    if (isTyping) {
      // タイピング中ならスキップして全文表示（音声はそのまま続行）
      setDisplayedText(currentMsg.text);
      setIsTyping(false);
      return;
    }
    // 次へ進む時は再生中の音声を停止
    stopAudio();
    if (currentIndex < messages.length - 1) {
      setCurrentIndex(prev => prev + 1);
    } else {
      setIsOpen(false);
      setCurrentIndex(0);
    }
  }, [waitingAudio, isTyping, currentIndex, messages.length, currentMsg, stopAudio]);

  const handleOpen = () => {
    setCurrentIndex(0);
    setIsOpen(true);
  };

  const handleClose = useCallback(() => {
    stopAudio();
    setIsOpen(false);
  }, [stopAudio]);

  // アンマウント時にobjectURL解放 + 音声停止
  useEffect(() => {
    return () => {
      if (audioRef.current) {
        audioRef.current.pause();
      }
      for (const url of audioUrlsRef.current.values()) {
        URL.revokeObjectURL(url);
      }
      audioUrlsRef.current.clear();
    };
  }, []);

  // messages変更時にキャッシュをリセット
  useEffect(() => {
    for (const url of audioUrlsRef.current.values()) {
      URL.revokeObjectURL(url);
    }
    audioUrlsRef.current.clear();
    audioDurationsRef.current.clear();
    fetchingRef.current.clear();
  }, [messages]);

  if (!messages || messages.length === 0) return null;

  // 話者の位置（左 or 右）: キャラクター一覧のインデックスが偶数→左、奇数→右
  const speakerSide = characters.findIndex(c => c.name === currentMsg?.speaker_name) % 2 === 0 ? 'left' : 'right';

  return (
    <>
      {/* 開くボタン（結果画面に表示） */}
      <div className="youkai-conversation">
        <button className="youkai-theater-open-btn" onClick={handleOpen}>
          <div className="youkai-theater-open-chars">
            {characters.slice(0, 4).map((c, i) => {
              const img = getYoukaiImageByName(c.name);
              return img ? (
                <img key={i} src={img} alt={c.name} className="youkai-theater-open-char-img" />
              ) : (
                <span key={i} className="youkai-theater-open-char-emoji">{c.emoji}</span>
              );
            })}
          </div>
          <span className="youkai-theater-open-text">妖怪たちからのメッセージを見る</span>
          <span className="youkai-theater-open-arrow">▶</span>
        </button>
      </div>

      {/* ゆっくり劇場風ポップアップ */}
      {isOpen && currentMsg && (
        <div className="youkai-theater-overlay" onClick={handleAdvance}>
          <div className="youkai-theater" onClick={e => e.stopPropagation()}>
            {/* 閉じるボタン */}
            <button className="youkai-theater-close" onClick={handleClose}>✕</button>

            {/* ステージ（キャラクター表示エリア） */}
            <div className="youkai-theater-stage">
              {/* 左側キャラクター群 */}
              <div className="youkai-theater-side left">
                {characters.filter((_, i) => i % 2 === 0).map((c) => {
                  const isSpeaking = c.name === currentMsg.speaker_name;
                  const img = isSpeaking
                    ? getYoukaiExpressionImage(c.name, currentMsg.emotion)
                    : (getYoukaiDefaultExpression(c.name) || getYoukaiImageByName(c.name));
                  return (
                    <div
                      key={c.name}
                      className={`youkai-theater-character ${isSpeaking ? 'speaking' : 'silent'}`}
                    >
                      {img ? (
                        <img src={img} alt={c.name} className="youkai-theater-char-img" />
                      ) : (
                        <span className="youkai-theater-char-emoji">{c.emoji}</span>
                      )}
                      <span className="youkai-theater-char-name">{c.name}</span>
                    </div>
                  );
                })}
              </div>

              {/* 右側キャラクター群 */}
              <div className="youkai-theater-side right">
                {characters.filter((_, i) => i % 2 === 1).map((c) => {
                  const isSpeaking = c.name === currentMsg.speaker_name;
                  const img = isSpeaking
                    ? getYoukaiExpressionImage(c.name, currentMsg.emotion)
                    : (getYoukaiDefaultExpression(c.name) || getYoukaiImageByName(c.name));
                  return (
                    <div
                      key={c.name}
                      className={`youkai-theater-character ${isSpeaking ? 'speaking' : 'silent'}`}
                    >
                      {img ? (
                        <img src={img} alt={c.name} className="youkai-theater-char-img" />
                      ) : (
                        <span className="youkai-theater-char-emoji">{c.emoji}</span>
                      )}
                      <span className="youkai-theater-char-name">{c.name}</span>
                    </div>
                  );
                })}
              </div>
            </div>

            {/* テキストボックス */}
            <div className={`youkai-theater-textbox ${speakerSide} ${currentMsg.tag ? `tag-${currentMsg.tag}` : ''}`} onClick={handleAdvance}>
              <div className="youkai-theater-speaker">
                <span className="youkai-theater-speaker-name">{currentMsg.speaker_name}</span>
                {currentMsg.tag === 'shelter' && (
                  <span className="youkai-theater-tag tag-shelter">🏠 避難場所</span>
                )}
                {currentMsg.tag === 'monument' && (
                  <span className="youkai-theater-tag tag-monument">🪨 伝承碑</span>
                )}
              </div>
              <div className="youkai-theater-text">
                {waitingAudio ? (
                  <span className="youkai-theater-loading">音声を準備中...</span>
                ) : (
                  <>
                    {displayedText}
                    {isTyping && <span className="youkai-theater-cursor">|</span>}
                  </>
                )}
              </div>
              <div className="youkai-theater-footer">
                <span className="youkai-theater-counter">
                  {currentIndex + 1} / {messages.length}
                </span>
                <div className="youkai-theater-controls">
                  <button
                    className={`youkai-theater-replay-btn ${isAudioPlaying ? 'playing' : ''}`}
                    onClick={(e) => {
                      e.stopPropagation();
                      playAudio(currentIndex);
                    }}
                    title="音声を再生"
                  >
                    🔊
                  </button>
                  <button
                    className={`youkai-theater-tts-toggle ${ttsEnabled ? '' : 'muted'}`}
                    onClick={(e) => {
                      e.stopPropagation();
                      if (ttsEnabled) stopAudio();
                      setTtsEnabled(prev => !prev);
                    }}
                    title={ttsEnabled ? '音声をオフ' : '音声をオン'}
                  >
                    {ttsEnabled ? '🔈' : '🔇'}
                  </button>
                </div>
                {!isTyping && !waitingAudio && (
                  <span className="youkai-theater-next">
                    {currentIndex < messages.length - 1 ? 'タップで次へ ▶' : 'タップで閉じる ✕'}
                  </span>
                )}
              </div>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
