import { useState, useEffect, useRef, useCallback } from 'react';
import { YOUKAI_TRIVIA_DATA } from '../../data/youkaiTriviaData';

export function YoukaiTrivia() {
  const [currentIndex, setCurrentIndex] = useState(0);
  const [fade, setFade] = useState(true);
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const touchStartX = useRef(0);
  const touchEndX = useRef(0);

  const goTo = useCallback((index: number) => {
    setFade(false);
    setTimeout(() => {
      setCurrentIndex(index);
      setFade(true);
    }, 200);
  }, []);

  const advanceToNext = useCallback(() => {
    goTo((currentIndex + 1) % YOUKAI_TRIVIA_DATA.length);
  }, [currentIndex, goTo]);

  const goToPrev = useCallback(() => {
    goTo((currentIndex - 1 + YOUKAI_TRIVIA_DATA.length) % YOUKAI_TRIVIA_DATA.length);
  }, [currentIndex, goTo]);

  // 自動ローテーション（操作後にリセット）
  const resetTimer = useCallback(() => {
    if (timerRef.current) clearInterval(timerRef.current);
    timerRef.current = setInterval(() => {
      setFade(false);
      setTimeout(() => {
        setCurrentIndex(prev => (prev + 1) % YOUKAI_TRIVIA_DATA.length);
        setFade(true);
      }, 200);
    }, 8000);
  }, []);

  useEffect(() => {
    resetTimer();
    return () => {
      if (timerRef.current) clearInterval(timerRef.current);
    };
  }, [resetTimer]);

  // スワイプ操作
  const handleTouchStart = useCallback((e: React.TouchEvent) => {
    touchStartX.current = e.touches[0].clientX;
  }, []);

  const handleTouchEnd = useCallback((e: React.TouchEvent) => {
    touchEndX.current = e.changedTouches[0].clientX;
    const diff = touchStartX.current - touchEndX.current;
    const threshold = 50;
    if (Math.abs(diff) > threshold) {
      if (diff > 0) {
        advanceToNext();
      } else {
        goToPrev();
      }
      resetTimer();
    }
  }, [advanceToNext, goToPrev, resetTimer]);

  // ドットタップ
  const handleDotClick = useCallback((index: number) => {
    if (index !== currentIndex) {
      goTo(index);
      resetTimer();
    }
  }, [currentIndex, goTo, resetTimer]);

  // 左右ボタン
  const handlePrev = useCallback(() => {
    goToPrev();
    resetTimer();
  }, [goToPrev, resetTimer]);

  const handleNext = useCallback(() => {
    advanceToNext();
    resetTimer();
  }, [advanceToNext, resetTimer]);

  const youkai = YOUKAI_TRIVIA_DATA[currentIndex];

  return (
    <div
      className="youkai-trivia"
      onTouchStart={handleTouchStart}
      onTouchEnd={handleTouchEnd}
    >
      <div className="youkai-trivia-nav">
        <button
          className="youkai-trivia-nav-btn"
          onClick={handlePrev}
          aria-label="前の妖怪"
        >
          ‹
        </button>

        <div className={`youkai-trivia-card ${fade ? 'visible' : ''}`}>
          <div className="youkai-trivia-header">
            {youkai.image ? (
              <img
                src={youkai.image}
                alt={youkai.name}
                className="youkai-trivia-image"
              />
            ) : (
              <span className="youkai-trivia-emoji">{youkai.emoji}</span>
            )}
            <div>
              <h4 className="youkai-trivia-name">{youkai.name}</h4>
              <span className="youkai-trivia-domain">{youkai.domain}</span>
            </div>
          </div>

          <ul className="youkai-trivia-list">
            {youkai.trivia.map((t, i) => (
              <li key={i}>{t}</li>
            ))}
          </ul>

          <div className="youkai-trivia-funfact">
            <strong>知ってた?</strong>
            <p>{youkai.funFact}</p>
          </div>
        </div>

        <button
          className="youkai-trivia-nav-btn"
          onClick={handleNext}
          aria-label="次の妖怪"
        >
          ›
        </button>
      </div>

      <div className="youkai-trivia-dots">
        {YOUKAI_TRIVIA_DATA.map((d, i) => (
          <button
            key={i}
            className={`youkai-trivia-dot ${i === currentIndex ? 'active' : ''}`}
            onClick={() => handleDotClick(i)}
            aria-label={d.name}
          >
            {d.image ? (
              <img src={d.image} alt={d.name} className="youkai-trivia-dot-img" />
            ) : (
              <span className="youkai-trivia-dot-emoji">{d.emoji}</span>
            )}
          </button>
        ))}
      </div>
    </div>
  );
}
