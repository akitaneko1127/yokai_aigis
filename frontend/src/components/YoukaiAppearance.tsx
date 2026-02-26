import { useEffect, useState } from 'react';
import type { RiskScore } from '../types';
import { getYoukaiImageById } from '../data/youkaiImages';

interface YoukaiAppearanceProps {
  risks: RiskScore[];
  onComplete: () => void;
}

export function YoukaiAppearance({ risks, onComplete }: YoukaiAppearanceProps) {
  const [visibleIndex, setVisibleIndex] = useState(-1);
  const [isComplete, setIsComplete] = useState(false);

  // リスクが高い順にソート
  const sortedRisks = [...risks].sort((a, b) => b.score - a.score);
  // 上位3体の妖怪を表示
  const topRisks = sortedRisks.slice(0, 3);

  useEffect(() => {
    // 順番に妖怪を表示
    const timers: ReturnType<typeof setTimeout>[] = [];

    topRisks.forEach((_, index) => {
      const timer = setTimeout(() => {
        setVisibleIndex(index);
      }, index * 400);
      timers.push(timer);
    });

    // アニメーション完了
    const completeTimer = setTimeout(() => {
      setIsComplete(true);
      setTimeout(onComplete, 500);
    }, topRisks.length * 400 + 800);
    timers.push(completeTimer);

    return () => {
      timers.forEach(t => clearTimeout(t));
    };
  }, [topRisks.length, onComplete]);

  return (
    <div className={`youkai-appearance ${isComplete ? 'fade-out' : ''}`}>
      <div className="appearance-content">
        <div className="appearance-title">
          この土地の守護妖怪たち
        </div>
        <div className="appearance-youkai-row">
          {topRisks.map((risk, index) => (
            <div
              key={risk.youkai_id}
              className={`appearance-youkai ${index <= visibleIndex ? 'visible' : ''}`}
              style={{ animationDelay: `${index * 0.1}s` }}
            >
              {getYoukaiImageById(risk.youkai_id) ? (
                <img
                  src={getYoukaiImageById(risk.youkai_id)}
                  alt={risk.youkai_name}
                  className="appearance-youkai-img"
                />
              ) : (
                <span className="appearance-emoji">{risk.youkai_emoji}</span>
              )}
              <span className="appearance-name">{risk.youkai_name}</span>
            </div>
          ))}
        </div>
        <div className={`appearance-message ${visibleIndex >= topRisks.length - 1 ? 'visible' : ''}`}>
          「この土地のことを教えてあげるよ」
        </div>
      </div>
    </div>
  );
}
