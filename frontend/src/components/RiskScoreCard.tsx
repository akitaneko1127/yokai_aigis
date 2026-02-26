import { useState } from 'react';
import type { RiskScore } from '../types';
import { getYoukaiImageById } from '../data/youkaiImages';

interface RiskScoreCardProps {
  risks: RiskScore[];
}

const levelColors: Record<string, string> = {
  '安心': '#4caf50',
  '注意': '#ff9800',
  '警戒': '#f44336',
  '要対策': '#9c27b0'
};

const levelBgColors: Record<string, string> = {
  '安心': '#e8f5e9',
  '注意': '#fff3e0',
  '警戒': '#ffebee',
  '要対策': '#f3e5f5'
};

// 詳細情報を日本語に変換
// 戻り値: { reasons: 理由の配列, hasMeaningfulData: 実データがあるか }
function formatDetails(details: Record<string, unknown>, score: number): { reasons: string[], hasMeaningfulData: boolean } {
  const reasons: string[] = [];
  let hasMeaningfulData = false;

  // 洪水
  if (details.flood) {
    const flood = details.flood as Record<string, unknown>;
    if (flood.depth) {
      reasons.push(`洪水浸水想定: ${flood.depth}`);
      hasMeaningfulData = true;
    }
    if (flood.river_name) {
      reasons.push(`対象河川: ${flood.river_name}`);
    }
  }

  // 津波
  if (details.tsunami) {
    const tsunami = details.tsunami as Record<string, unknown>;
    if (tsunami.depth) {
      reasons.push(`津波浸水想定: ${tsunami.depth}`);
      hasMeaningfulData = true;
    }
  }

  // 高潮
  if (details.storm_surge) {
    const storm = details.storm_surge as Record<string, unknown>;
    if (storm.depth) {
      reasons.push(`高潮浸水想定: ${storm.depth}`);
      hasMeaningfulData = true;
    }
  }

  // 内水氾濫
  if (details.inland_flood) {
    const inland = details.inland_flood as Record<string, unknown>;
    if (inland.depth) {
      reasons.push(`内水氾濫想定: ${inland.depth}`);
      hasMeaningfulData = true;
    }
    if (inland.note) {
      reasons.push(`${inland.note}`);
    }
  }

  // 土砂災害
  if (details.zone_type) {
    reasons.push(`${details.zone_type}`);
    hasMeaningfulData = true;
  }
  if (details.landslide_type) {
    const typeMap: Record<string, string> = {
      '1': '急傾斜地の崩壊',
      '2': '土石流',
      '3': '地滑り'
    };
    const typeName = typeMap[String(details.landslide_type)] || String(details.landslide_type);
    reasons.push(`災害種別: ${typeName}`);
  }

  // 液状化
  if (details.liquefaction) {
    const liq = details.liquefaction as Record<string, unknown>;
    if (liq.risk_level) {
      reasons.push(`液状化: ${liq.risk_level}`);
      hasMeaningfulData = true;
    }
  }

  // 地形
  if (details.terrain) {
    const terrain = details.terrain as Record<string, unknown>;
    if (terrain.type) {
      reasons.push(`地形分類: ${terrain.type}`);
      hasMeaningfulData = true;
    }
    if (terrain.ground_condition) {
      reasons.push(`地盤状態: ${terrain.ground_condition}`);
    }
    if (terrain.former_land_use) {
      reasons.push(`過去の土地: ${terrain.former_land_use}`);
    }
    if (terrain.former_water) {
      reasons.push(`${terrain.former_water}`);
    }
    if (terrain.fire_risk_factor) {
      reasons.push(`火災リスク要因: ${terrain.fire_risk_factor}`);
    }
  }

  // 風災（高潮からの暴風推定）
  if (details.storm_surge_wind) {
    const wind = details.storm_surge_wind as Record<string, unknown>;
    if (wind.note) {
      reasons.push(`${wind.note}`);
      hasMeaningfulData = true;
    }
  }

  // 火災時の液状化リスク
  if (details.liquefaction_fire_risk) {
    const liqFire = details.liquefaction_fire_risk as Record<string, unknown>;
    if (liqFire.note) {
      reasons.push(`${liqFire.note}`);
      hasMeaningfulData = true;
    }
  }

  // 評価根拠
  if (details.evaluation_basis) {
    reasons.push(`評価方法: ${details.evaluation_basis}`);
  }

  // 一般的なノート（スコアが0より大きい場合は常に表示）
  if (details.note && score > 0) {
    reasons.push(String(details.note));
  }

  return { reasons, hasMeaningfulData };
}

export function RiskScoreCard({ risks }: RiskScoreCardProps) {
  const [expandedId, setExpandedId] = useState<string | null>(null);

  if (!risks || risks.length === 0) {
    return null;
  }

  // 高リスク順にソート
  const sortedRisks = [...risks].sort((a, b) => b.score - a.score);

  const toggleExpand = (id: string) => {
    setExpandedId(expandedId === id ? null : id);
  };

  return (
    <div className="risk-score-card">
      <h3 style={{ marginBottom: '16px', color: '#333' }}>
        📊 リスク評価
      </h3>
      <div className="risks">
        {sortedRisks.map((risk) => {
          const isExpanded = expandedId === risk.youkai_id;
          const { reasons } = formatDetails(risk.details, risk.score);
          // スコアが0より大きく、理由がある場合は詳細表示可能
          const hasReasons = reasons.length > 0 && risk.score > 0;

          return (
            <div
              key={risk.youkai_id}
              className={`risk-item ${isExpanded ? 'expanded' : ''}`}
              style={{
                backgroundColor: levelBgColors[risk.level] || '#f5f5f5',
                border: `2px solid ${levelColors[risk.level] || '#999'}`,
                cursor: hasReasons ? 'pointer' : 'default',
              }}
              onClick={() => hasReasons && toggleExpand(risk.youkai_id)}
            >
              <div className="risk-item-content">
                {/* 基本情報 */}
                <div className="risk-item-summary">
                  <div className="risk-emoji">
                    {getYoukaiImageById(risk.youkai_id) ? (
                      <img
                        src={getYoukaiImageById(risk.youkai_id)}
                        alt={risk.youkai_name}
                        className="risk-youkai-img"
                      />
                    ) : (
                      <span className="risk-emoji-text">{risk.youkai_emoji}</span>
                    )}
                  </div>
                  <div className="risk-name">
                    {risk.youkai_name}
                  </div>
                  <div
                    className="risk-level"
                    style={{ color: levelColors[risk.level] }}
                  >
                    {risk.level}
                  </div>
                  <div className="risk-score">
                    スコア: {risk.score}
                  </div>
                </div>

                {/* 展開時の詳細 */}
                {isExpanded && hasReasons && (
                  <div
                    className="risk-item-details"
                    style={{ borderLeftColor: levelColors[risk.level] }}
                  >
                    <div className="risk-item-details-title">
                      評価の理由:
                    </div>
                    <ul className="risk-item-details-list">
                      {reasons.map((reason, idx) => (
                        <li key={idx}>{reason}</li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>

              {/* 展開ヒント */}
              {hasReasons && (
                <div className="risk-item-hint">
                  {isExpanded ? 'タップで閉じる ▲' : 'タップで詳細表示 ▼'}
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
