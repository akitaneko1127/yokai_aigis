import { useState, useEffect, useRef, useCallback } from 'react';
import { QUIZ_DATA } from '../../data/quizData';

export function DisasterQuiz() {
  const [questionIndex, setQuestionIndex] = useState(0);
  const [selectedChoice, setSelectedChoice] = useState<number | null>(null);
  const [score, setScore] = useState(0);
  const [answered, setAnswered] = useState(0);
  const [shuffledIndices, setShuffledIndices] = useState<number[]>([]);
  const autoAdvanceTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const autoAnswerTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // 初回シャッフル
  useEffect(() => {
    setShuffledIndices(shuffle(QUIZ_DATA.map((_, i) => i)));
  }, []);

  const currentQuiz = shuffledIndices.length > 0
    ? QUIZ_DATA[shuffledIndices[questionIndex % shuffledIndices.length]]
    : null;

  const clearTimers = useCallback(() => {
    if (autoAdvanceTimerRef.current) {
      clearTimeout(autoAdvanceTimerRef.current);
      autoAdvanceTimerRef.current = null;
    }
    if (autoAnswerTimerRef.current) {
      clearTimeout(autoAnswerTimerRef.current);
      autoAnswerTimerRef.current = null;
    }
  }, []);

  // 無操作12秒で自動回答表示
  useEffect(() => {
    if (selectedChoice !== null || !currentQuiz) return;

    autoAnswerTimerRef.current = setTimeout(() => {
      setSelectedChoice(currentQuiz.correctIndex);
      setAnswered(prev => prev + 1);

      // 5秒後に次の問題
      autoAdvanceTimerRef.current = setTimeout(() => {
        advanceQuestion();
      }, 5000);
    }, 12000);

    return clearTimers;
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [questionIndex, selectedChoice, shuffledIndices]);

  const handleChoice = (index: number) => {
    if (selectedChoice !== null) return;
    clearTimers();

    setSelectedChoice(index);
    setAnswered(prev => prev + 1);
    if (index === currentQuiz?.correctIndex) {
      setScore(prev => prev + 1);
    }

    // 5秒後に次の問題
    autoAdvanceTimerRef.current = setTimeout(() => {
      advanceQuestion();
    }, 5000);
  };

  const advanceQuestion = () => {
    clearTimers();
    const nextIndex = questionIndex + 1;
    if (nextIndex >= shuffledIndices.length) {
      // シャッフルして再開
      setShuffledIndices(shuffle(QUIZ_DATA.map((_, i) => i)));
      setQuestionIndex(0);
    } else {
      setQuestionIndex(nextIndex);
    }
    setSelectedChoice(null);
  };

  if (!currentQuiz) return null;

  const categoryLabel: Record<string, string> = {
    earthquake: '地震',
    flood: '水害',
    tsunami: '津波',
    fire: '火災',
    general: '一般'
  };

  return (
    <div className="disaster-quiz">
      {answered > 0 && (
        <div className="disaster-quiz-score">
          {score}/{answered} 正解!
        </div>
      )}

      <div className="disaster-quiz-category">
        {categoryLabel[currentQuiz.category] || currentQuiz.category}
      </div>

      <p className="disaster-quiz-question">{currentQuiz.question}</p>

      <div className="disaster-quiz-choices">
        {currentQuiz.choices.map((choice, i) => {
          let className = 'disaster-quiz-choice';
          if (selectedChoice !== null) {
            if (i === currentQuiz.correctIndex) className += ' correct';
            else if (i === selectedChoice) className += ' incorrect';
          }
          return (
            <button
              key={i}
              className={className}
              onClick={() => handleChoice(i)}
              disabled={selectedChoice !== null}
            >
              {choice}
            </button>
          );
        })}
      </div>

      {selectedChoice !== null && (
        <div className="disaster-quiz-explanation">
          <span className="disaster-quiz-result">
            {selectedChoice === currentQuiz.correctIndex ? '正解!' : '不正解...'}
          </span>
          <p>{currentQuiz.explanation}</p>
        </div>
      )}
    </div>
  );
}

function shuffle<T>(array: T[]): T[] {
  const arr = [...array];
  for (let i = arr.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    [arr[i], arr[j]] = [arr[j], arr[i]];
  }
  return arr;
}
