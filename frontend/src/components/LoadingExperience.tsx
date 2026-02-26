import { useState, useEffect, useRef, useCallback } from 'react';
import type { Location } from '../types';
import { HistoricalMapMini } from './loading/HistoricalMapMini';
import { DisasterQuiz } from './loading/DisasterQuiz';
import { YoukaiTrivia } from './loading/YoukaiTrivia';

interface LoadingExperienceProps {
  selectedLocation: Location;
  message?: string;
}

type TabId = 'map' | 'quiz' | 'trivia';

const TABS: { id: TabId; label: string; icon: string }[] = [
  { id: 'map', label: '古地図', icon: '🗺️' },
  { id: 'quiz', label: '防災クイズ', icon: '❓' },
  { id: 'trivia', label: '妖怪豆知識', icon: '👻' }
];

const SOUDAN_IMAGES = ['/images/soudan.png', '/images/soudan1.png'];

const AUTO_ROTATE_INTERVAL = 20_000;
const MANUAL_PAUSE_DURATION = 60_000;

function getElapsedMessage(seconds: number): string {
  if (seconds < 60) return '妖怪たちが土地を調べています...';
  if (seconds < 90) return 'もう少しお待ちください... 妖怪たちが慎重に調査しています';
  return '結果はもうすぐです!';
}

export function LoadingExperience({ selectedLocation }: LoadingExperienceProps) {
  const [activeTab, setActiveTab] = useState<TabId>('map');
  const [elapsedSeconds, setElapsedSeconds] = useState(0);
  const autoRotateTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const manualPauseTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const [autoRotateEnabled, setAutoRotateEnabled] = useState(true);
  const [soudanIndex, setSoudanIndex] = useState(0);

  // 経過時間カウンター
  useEffect(() => {
    const interval = setInterval(() => {
      setElapsedSeconds(prev => prev + 1);
    }, 1000);
    return () => clearInterval(interval);
  }, []);

  // タブ自動ローテーション
  const scheduleNextRotation = useCallback(() => {
    if (autoRotateTimerRef.current) clearTimeout(autoRotateTimerRef.current);
    autoRotateTimerRef.current = setTimeout(() => {
      setActiveTab(prev => {
        const currentIdx = TABS.findIndex(t => t.id === prev);
        return TABS[(currentIdx + 1) % TABS.length].id;
      });
      scheduleNextRotation();
    }, AUTO_ROTATE_INTERVAL);
  }, []);

  useEffect(() => {
    if (autoRotateEnabled) {
      scheduleNextRotation();
    }
    return () => {
      if (autoRotateTimerRef.current) clearTimeout(autoRotateTimerRef.current);
    };
  }, [autoRotateEnabled, scheduleNextRotation]);

  const handleTabClick = (tabId: TabId) => {
    setActiveTab(tabId);
    setAutoRotateEnabled(false);
    if (autoRotateTimerRef.current) clearTimeout(autoRotateTimerRef.current);
    if (manualPauseTimerRef.current) clearTimeout(manualPauseTimerRef.current);

    // 60秒後に自動ローテーション再開
    manualPauseTimerRef.current = setTimeout(() => {
      setAutoRotateEnabled(true);
    }, MANUAL_PAUSE_DURATION);
  };

  // soudan画像切り替え（10秒ごと）
  useEffect(() => {
    const interval = setInterval(() => {
      setSoudanIndex(prev => (prev + 1) % SOUDAN_IMAGES.length);
    }, 10000);
    return () => clearInterval(interval);
  }, []);

  // cleanup
  useEffect(() => {
    return () => {
      if (manualPauseTimerRef.current) clearTimeout(manualPauseTimerRef.current);
    };
  }, []);

  const formatTime = (seconds: number) => {
    const m = Math.floor(seconds / 60);
    const s = seconds % 60;
    return m > 0 ? `${m}:${s.toString().padStart(2, '0')}` : `${s}秒`;
  };

  return (
    <div className="loading-experience">
      {/* 妖怪会議イラスト */}
      <div className="loading-experience-hero">
        <img
          key={soudanIndex}
          src={SOUDAN_IMAGES[soudanIndex]}
          alt="妖怪たちが相談中"
          className="loading-experience-hero-img"
        />
      </div>

      {/* プログレスバー */}
      <div className="loading-experience-progress">
        <div className="loading-experience-progress-bar" />
      </div>

      {/* メッセージ + 経過時間 */}
      <div className="loading-experience-status">
        <p className="loading-experience-message">
          {getElapsedMessage(elapsedSeconds)}
        </p>
        <span className="loading-experience-timer">
          {formatTime(elapsedSeconds)}
        </span>
      </div>

      {/* タブ */}
      <div className="loading-experience-tabs">
        {TABS.map(tab => (
          <button
            key={tab.id}
            className={`loading-experience-tab ${activeTab === tab.id ? 'active' : ''}`}
            onClick={() => handleTabClick(tab.id)}
          >
            <span>{tab.icon}</span>
            <span>{tab.label}</span>
          </button>
        ))}
      </div>

      {/* タブコンテンツ */}
      <div className="loading-experience-content">
        {activeTab === 'map' && (
          <HistoricalMapMini selectedLocation={selectedLocation} />
        )}
        {activeTab === 'quiz' && (
          <DisasterQuiz />
        )}
        {activeTab === 'trivia' && (
          <YoukaiTrivia />
        )}
      </div>
    </div>
  );
}
