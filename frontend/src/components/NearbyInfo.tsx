import type { NearbyShelter, NearbyMonument } from '../types';

interface NearbyInfoProps {
  shelters?: NearbyShelter[];
  monuments?: NearbyMonument[];
}

export function NearbyInfo({ shelters, monuments }: NearbyInfoProps) {
  const hasShelters = shelters && shelters.length > 0;
  const hasMonuments = monuments && monuments.length > 0;

  if (!hasShelters && !hasMonuments) return null;

  return (
    <div className="nearby-info">
      {/* 避難所セクション */}
      {hasShelters && (
        <div className="nearby-info-section">
          <h3 className="nearby-info-title">
            <span className="nearby-info-icon">🏫</span>
            近くの指定緊急避難場所
          </h3>
          <div className="nearby-info-list">
            {shelters.map((s, i) => (
              <div key={i} className="nearby-info-card shelter-card">
                <div className="nearby-info-card-header">
                  <span className="nearby-info-card-name">{s.name}</span>
                  <span className="nearby-info-card-distance">
                    約{s.distance_km}km
                  </span>
                </div>
                {s.address && (
                  <div className="nearby-info-card-address">{s.address}</div>
                )}
                {s.disaster_types.length > 0 && (
                  <div className="nearby-info-card-tags">
                    {s.disaster_types.map((dt, j) => (
                      <span key={j} className="nearby-info-tag shelter-tag">{dt}</span>
                    ))}
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* 伝承碑セクション */}
      {hasMonuments && (
        <div className="nearby-info-section">
          <h3 className="nearby-info-title">
            <span className="nearby-info-icon">🪨</span>
            近くの自然災害伝承碑
          </h3>
          <div className="monument-trivia">
            <ul>
              <li>全国に約2,000基以上が確認されている、過去の災害を記録した石碑です。</li>
              <li>2019年から国土地理院の地形図に地図記号として掲載されるようになりました。</li>
            </ul>
          </div>
          <div className="nearby-info-list">
            {monuments.map((m, i) => (
              <div key={i} className="nearby-info-card monument-card">
                <div className="nearby-info-card-header">
                  <span className="nearby-info-card-name">「{m.name}」</span>
                  <span className="nearby-info-card-distance">
                    約{m.distance_km}km
                  </span>
                </div>
                <div className="nearby-info-card-meta">
                  <span className="nearby-info-tag monument-tag">{m.disaster_type}</span>
                  {m.disaster_name && (
                    <span className="nearby-info-card-disaster">{m.disaster_name}</span>
                  )}
                </div>
                {m.description && (
                  <div className="nearby-info-card-description">
                    {m.description}
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
