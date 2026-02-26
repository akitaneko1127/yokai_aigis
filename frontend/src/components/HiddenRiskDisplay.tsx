import type { HiddenRisk } from '../types';

interface HiddenRiskDisplayProps {
  hiddenRisks: HiddenRisk[];
}

// 深刻度別の色設定
const severityColors: Record<string, { bg: string; border: string; text: string }> = {
  low: { bg: '#e8f5e9', border: '#4caf50', text: '#2e7d32' },
  medium: { bg: '#fff3e0', border: '#ff9800', text: '#e65100' },
  high: { bg: '#ffebee', border: '#f44336', text: '#c62828' },
  critical: { bg: '#fce4ec', border: '#e91e63', text: '#ad1457' }
};

// リスクタイプ別のアイコン
const typeIcons: Record<string, string> = {
  '時系列リスク': '⏰',
  '経路リスク': '🛤️',
  '季節リスク': '🌸',
  '時間帯リスク': '🌙',
  '複合地域リスク': '🗺️',
  'インフラリスク': '🔌',
  '地形リスク': '⛰️'
};

export function HiddenRiskDisplay({ hiddenRisks }: HiddenRiskDisplayProps) {
  if (!hiddenRisks || hiddenRisks.length === 0) {
    return null;
  }

  return (
    <div className="hidden-risk-display">
      <h3 style={{
        marginBottom: '16px',
        color: '#333',
        display: 'flex',
        alignItems: 'center',
        gap: '8px'
      }}>
        <span>💡</span>
        <span>AIが発見した隠れリスク</span>
      </h3>
      <p style={{
        fontSize: '0.875em',
        color: '#666',
        marginBottom: '16px'
      }}>
        複数のリスクが組み合わさることで生じる可能性のある危険です。
      </p>
      <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
        {hiddenRisks.map((risk) => {
          const colors = severityColors[risk.severity] || severityColors.medium;
          return (
            <div
              key={risk.id}
              style={{
                backgroundColor: colors.bg,
                border: `2px solid ${colors.border}`,
                borderRadius: '12px',
                padding: '16px',
                boxShadow: '0 2px 4px rgba(0,0,0,0.1)'
              }}
            >
              <div style={{
                display: 'flex',
                alignItems: 'flex-start',
                gap: '12px',
                marginBottom: '12px'
              }}>
                <span style={{ fontSize: '1.5em' }}>
                  {typeIcons[risk.type] || '⚠️'}
                </span>
                <div style={{ flex: 1 }}>
                  <div style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: '8px',
                    marginBottom: '4px'
                  }}>
                    <span style={{
                      display: 'inline-block',
                      padding: '2px 8px',
                      backgroundColor: colors.border,
                      color: 'white',
                      borderRadius: '4px',
                      fontSize: '0.75em',
                      fontWeight: 'bold'
                    }}>
                      {risk.type}
                    </span>
                    <span style={{
                      fontSize: '0.75em',
                      color: '#666'
                    }}>
                      確信度: {Math.round(risk.confidence * 100)}%
                    </span>
                  </div>
                  <h4 style={{
                    margin: '0 0 8px 0',
                    color: colors.text,
                    fontSize: '1em'
                  }}>
                    {risk.title}
                  </h4>
                </div>
              </div>
              <p style={{
                margin: 0,
                fontSize: '0.9em',
                color: '#333',
                lineHeight: 1.6
              }}>
                {risk.description}
              </p>
              {risk.reasoning && (
                <div style={{
                  marginTop: '12px',
                  padding: '8px 12px',
                  backgroundColor: 'rgba(255,255,255,0.5)',
                  borderRadius: '6px',
                  fontSize: '0.8em',
                  color: '#666'
                }}>
                  <strong>分析根拠:</strong> {risk.reasoning}
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
