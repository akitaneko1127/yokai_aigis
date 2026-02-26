import type { Action } from '../types';

interface ActionListProps {
  actions: Action[];
  reassurance: string;
}

// カテゴリ別のアイコン
const categoryIcons: Record<string, string> = {
  '避難所': '🏃',
  '準備品': '🎒',
  '情報': '📱',
  '家具': '🪑',
  '確認': '👀',
  '判断': '🤔',
  '習慣': '📅',
  '安全': '⚠️',
  '点検': '🔧',
  '基本': '✅'
};

export function ActionList({ actions, reassurance }: ActionListProps) {
  if (!actions || actions.length === 0) {
    return null;
  }

  return (
    <div className="action-list">
      <h3 style={{ marginBottom: '16px', color: '#333' }}>
        ✅ おすすめの備え
      </h3>
      <ul style={{
        listStyle: 'none',
        padding: 0,
        margin: 0
      }}>
        {actions.map((action, index) => (
          <li
            key={index}
            style={{
              padding: '12px 16px',
              backgroundColor: '#f8f9fa',
              borderRadius: '8px',
              marginBottom: '8px',
              display: 'flex',
              alignItems: 'center',
              gap: '12px'
            }}
          >
            <span style={{ fontSize: '1.2em' }}>
              {categoryIcons[action.category] || '✓'}
            </span>
            <div style={{ flex: 1 }}>
              <span style={{
                display: 'inline-block',
                padding: '2px 8px',
                backgroundColor: '#e3f2fd',
                borderRadius: '4px',
                fontSize: '0.75em',
                color: '#1976d2',
                marginRight: '8px'
              }}>
                {action.category}
              </span>
              <span>{action.content}</span>
            </div>
          </li>
        ))}
      </ul>
      {reassurance && (
        <div style={{
          marginTop: '16px',
          padding: '16px',
          backgroundColor: '#e8f5e9',
          borderRadius: '8px',
          textAlign: 'center',
          color: '#2e7d32',
          fontWeight: '500'
        }}>
          {reassurance}
        </div>
      )}
    </div>
  );
}
