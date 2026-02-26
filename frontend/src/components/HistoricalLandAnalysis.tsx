import { useState } from 'react';
import type { HistoricalLandAnalysis as HistoricalLandAnalysisType, HistoricalFinding } from '../types';

interface HistoricalLandAnalysisProps {
  analysis: HistoricalLandAnalysisType;
  onRecommendedMapSelect?: (layerId: string) => void;
}

const categoryIcons: Record<string, string> = {
  terrain: '🏔️',
  water: '💧',
  development: '🏗️',
  disaster: '⚠️'
};

const categoryLabels: Record<string, string> = {
  terrain: '地形',
  water: '水辺の歴史',
  development: '開発履歴',
  disaster: '災害リスク'
};

function FindingCard({ finding }: { finding: HistoricalFinding }) {
  const [expanded, setExpanded] = useState(false);

  return (
    <div
      className="historical-finding-card"
      onClick={() => setExpanded(!expanded)}
    >
      <div className="finding-header">
        <span className="finding-icon">{categoryIcons[finding.category] || '📋'}</span>
        <div className="finding-title-area">
          <span className="finding-category">{categoryLabels[finding.category] || finding.category}</span>
          <h4 className="finding-title">{finding.title}</h4>
        </div>
        <span className="finding-expand-icon">{expanded ? '▲' : '▼'}</span>
      </div>

      {expanded && (
        <div className="finding-details">
          <p className="finding-description">{finding.description}</p>
          <div className="finding-implication">
            <strong>リスクへの影響:</strong>
            <p>{finding.risk_implication}</p>
          </div>
          <div className="finding-meta">
            <span className="finding-source">出典: {finding.source}</span>
            <span className="finding-confidence">
              信頼度: {Math.round(finding.confidence * 100)}%
            </span>
          </div>
        </div>
      )}
    </div>
  );
}

export function HistoricalLandAnalysis({ analysis, onRecommendedMapSelect }: HistoricalLandAnalysisProps) {
  if (!analysis.has_historical_data) {
    return null;
  }

  return (
    <div className="historical-land-analysis">
      <h3 className="historical-title">
        <span className="historical-icon">📜</span>
        土地の歴史分析
      </h3>

      {analysis.terrain_type && (
        <div className="terrain-badge">
          <span className="terrain-label">地形分類:</span>
          <span className="terrain-type">{analysis.terrain_type}</span>
          {analysis.era_analysis && (
            <span className="era-badge">{analysis.era_analysis}</span>
          )}
        </div>
      )}

      <div className="historical-summary">
        {analysis.summary.split('\n').map((line, idx) => (
          <p key={idx}>{line}</p>
        ))}
      </div>

      {analysis.findings.length > 0 && (
        <div className="historical-findings">
          <h4 className="findings-header">詳細な分析結果</h4>
          {analysis.findings.map((finding, idx) => (
            <FindingCard key={idx} finding={finding} />
          ))}
        </div>
      )}

      {analysis.recommended_map_layer && onRecommendedMapSelect && (
        <button
          className="recommended-map-btn"
          onClick={() => onRecommendedMapSelect(analysis.recommended_map_layer!)}
        >
          <span>🗺️</span>
          <span>この地形の歴史を地図で確認</span>
        </button>
      )}
    </div>
  );
}
