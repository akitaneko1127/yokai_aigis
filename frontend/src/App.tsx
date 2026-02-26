import { useState, useCallback, useEffect } from 'react';
import {
  MapCompare,
  YoukaiConversation,
  RiskScoreCard,
  ActionList,
  LoadingExperience,
  HiddenRiskDisplay,
  YoukaiAppearance,
  HistoricalLandAnalysis,
  NearbyInfo
} from './components';
import { getYoukaiImageById } from './data/youkaiImages';
import { api } from './services/api';
import type { Location, HazardResponse } from './types';
import './App.css';

const YOUKAI_INTRO_LIST = [
  { id: 'kappa', name: '河童', domain: '水害' },
  { id: 'namazu', name: '大ナマズ', domain: '地震' },
  { id: 'tsuchigumo', name: '土蜘蛛', domain: '土砂災害' },
  { id: 'tengu', name: '天狗', domain: '風災' },
  { id: 'kasha', name: '火車', domain: '火災' },
  { id: 'yukionna', name: '雪女', domain: '雪害' },
  { id: 'hinokagutsuchi', name: 'ヒノカグツチ', domain: '火山' },
] as const;

// 初期位置（東京駅付近）
const DEFAULT_CENTER: Location = {
  lat: 35.6812,
  lng: 139.7671
};

function App() {
  const [selectedLocation, setSelectedLocation] = useState<Location | null>(null);
  const [hazardData, setHazardData] = useState<HazardResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [showAppearance, setShowAppearance] = useState(false);
  const [pendingHazardData, setPendingHazardData] = useState<HazardResponse | null>(null);
  const [selectionModeEnabled, setSelectionModeEnabled] = useState(false);
  const [autoOpenConversation, setAutoOpenConversation] = useState(false);

  const handleLocationSelect = useCallback(async (location: Location) => {
    setSelectedLocation(location);
    setSelectionModeEnabled(false); // 選択後はモード解除
    setLoading(true);
    setError(null);
    setHazardData(null);
    setShowAppearance(false);
    setAutoOpenConversation(false);

    try {
      const result = await api.analyzeLocation(location);
      // 妖怪登場アニメーションを表示
      setPendingHazardData(result);
      setShowAppearance(true);
    } catch (err) {
      console.error('分析エラー:', err);
      setError('ハザード情報の取得に失敗しました。再度お試しください。');
    } finally {
      setLoading(false);
    }
  }, []);

  const handleEnableSelectionMode = useCallback(() => {
    setSelectionModeEnabled(true);
  }, []);

  const handleAppearanceComplete = useCallback(() => {
    setShowAppearance(false);
    setHazardData(pendingHazardData);
    setPendingHazardData(null);
  }, [pendingHazardData]);

  // 結果表示後に妖怪劇場を自動オープン
  useEffect(() => {
    if (hazardData && !loading) {
      const timer = setTimeout(() => {
        setAutoOpenConversation(true);
      }, 400);
      return () => clearTimeout(timer);
    }
  }, [hazardData, loading]);

  const handleSearchAnother = useCallback(() => {
    setSelectedLocation(null);
    setHazardData(null);
    setError(null);
    // ページトップにスクロール
    window.scrollTo({ top: 0, behavior: 'smooth' });
  }, []);

  const handleClearSelection = useCallback(() => {
    setSelectedLocation(null);
    setHazardData(null);
    setError(null);
  }, []);

  return (
    <div className="app">
      <header className="header">
        <h1>
          <span className="header-emoji">🗾</span>
          妖怪ハザードマップ
        </h1>
        <p className="subtitle">
          土地の災害リスクを、妖怪たちが優しく教えてくれます
        </p>
      </header>

      <main className="main">
        <section className="map-section">
          <div
            className={`click-mode-indicator ${selectedLocation ? 'active' : ''} ${selectionModeEnabled ? 'selection-mode' : ''} ${!selectedLocation && !selectionModeEnabled ? 'clickable' : ''}`}
            onClick={!selectedLocation && !selectionModeEnabled ? handleEnableSelectionMode : undefined}
          >
            {selectedLocation ? (
              <>
                <span>✓</span>
                <span>選択中: 緯度 {selectedLocation.lat.toFixed(4)}, 経度 {selectedLocation.lng.toFixed(4)}</span>
              </>
            ) : selectionModeEnabled ? (
              <>
                <span className="click-icon pulse">👆</span>
                <span>地図上の調べたい場所をタップしてください</span>
              </>
            ) : (
              <>
                <span className="click-icon">👆</span>
                <span>ここをタップして場所選択モードへ</span>
              </>
            )}
          </div>

          <div className="map-container-wrapper">
            <MapCompare
              center={DEFAULT_CENTER}
              onLocationSelect={handleLocationSelect}
              onClearSelection={handleClearSelection}
              selectedLocation={selectedLocation}
              selectionModeEnabled={selectionModeEnabled}
            />

          </div>
        </section>

        {/* ローディングポップアップ（フルスクリーンモーダル） */}
        {loading && selectedLocation && (
          <div className="loading-modal-overlay">
            <div className="loading-modal">
              <LoadingExperience selectedLocation={selectedLocation} />
            </div>
          </div>
        )}

        {showAppearance && pendingHazardData && (
          <YoukaiAppearance
            risks={pendingHazardData.risk_scores}
            onComplete={handleAppearanceComplete}
          />
        )}

        {error && (
          <section className="error-section">
            <div className="error-message">
              ⚠️ {error}
            </div>
          </section>
        )}

        {hazardData && !loading && (
          <>
            <section className="result-section">
              <RiskScoreCard risks={hazardData.risk_scores} />
            </section>

            {hazardData.historical_analysis?.has_historical_data && (
              <section className="historical-section">
                <HistoricalLandAnalysis
                  analysis={hazardData.historical_analysis}
                />
              </section>
            )}

            <section className="conversation-section">
              <YoukaiConversation
                messages={hazardData.youkai_response.conversation}
                autoOpen={autoOpenConversation}
              />
            </section>

            {hazardData.youkai_response.ai_analysis?.hidden_risks?.length > 0 && (
              <section className="hidden-risk-section">
                <HiddenRiskDisplay
                  hiddenRisks={hazardData.youkai_response.ai_analysis.hidden_risks}
                />
              </section>
            )}

            {((hazardData.nearby_shelters?.length ?? 0) > 0 || (hazardData.nearby_monuments?.length ?? 0) > 0) && (
              <section className="nearby-info-section">
                <NearbyInfo
                  shelters={hazardData.nearby_shelters}
                  monuments={hazardData.nearby_monuments}
                />
              </section>
            )}

            <section className="action-section">
              <ActionList
                actions={hazardData.youkai_response.summary.actions}
                reassurance={hazardData.youkai_response.summary.reassurance}
              />
            </section>

            <section className="search-another-section">
              <button
                className="search-another-btn"
                onClick={handleSearchAnother}
              >
                <span>🔍</span>
                <span>違う場所を調べる</span>
              </button>
            </section>
          </>
        )}

        {!selectedLocation && !loading && (
          <section className="intro-section">
            <div className="intro-content">
              <div className="youkai-intro">
                {YOUKAI_INTRO_LIST.map((y) => (
                  <img
                    key={y.id}
                    src={getYoukaiImageById(y.id)}
                    alt={y.name}
                    className="youkai-intro-img"
                  />
                ))}
              </div>
              <h3>妖怪たちが見守っています</h3>
              <p>
                地図をクリックすると、その土地の災害リスクを<br />
                妖怪たちが優しく教えてくれます。
              </p>
              <div className="youkai-list">
                {YOUKAI_INTRO_LIST.map((y) => (
                  <div key={y.id} className="youkai-item">
                    <img
                      src={getYoukaiImageById(y.id)}
                      alt={y.name}
                      className="youkai-item-img"
                    />
                    <span>{y.name} - {y.domain}</span>
                  </div>
                ))}
              </div>
            </div>
          </section>
        )}
      </main>

      <footer className="footer">
        <p>
          データ出典: 国土交通省 不動産情報ライブラリ | 非商用プロジェクト
        </p>
      </footer>
    </div>
  );
}

export default App;
