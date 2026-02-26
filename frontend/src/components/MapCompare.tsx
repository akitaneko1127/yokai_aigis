import { useEffect, useRef, useState, useCallback } from 'react';
import L from 'leaflet';
import type { Location } from '../types';
import { LAYER_OPTIONS } from '../data/layerOptions';
import type { LayerOption } from '../data/layerOptions';

interface MapCompareProps {
  center: Location;
  onLocationSelect: (location: Location) => void;
  onClearSelection: () => void;
  selectedLocation: Location | null;
  selectionModeEnabled: boolean;
}

export function MapCompare({ center, onLocationSelect, onClearSelection, selectedLocation, selectionModeEnabled }: MapCompareProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const leftMapRef = useRef<HTMLDivElement>(null);
  const rightMapRef = useRef<HTMLDivElement>(null);
  const leftMapInstanceRef = useRef<L.Map | null>(null);
  const rightMapInstanceRef = useRef<L.Map | null>(null);
  const leftLayerRef = useRef<L.TileLayer | null>(null);
  const rightLayerRef = useRef<L.TileLayer | null>(null);
  const leftMarkerRef = useRef<L.Marker | null>(null);
  const rightMarkerRef = useRef<L.Marker | null>(null);
  const isSyncingRef = useRef(false);
  const selectionModeRef = useRef(selectionModeEnabled);

  // selectionModeEnabled の変更を ref に反映
  useEffect(() => {
    selectionModeRef.current = selectionModeEnabled;
  }, [selectionModeEnabled]);

  const [sliderPosition, setSliderPosition] = useState(50);
  const [isDragging, setIsDragging] = useState(false);
  const [leftLayerId, setLeftLayerId] = useState('gsi_photo');
  const [rightLayerId, setRightLayerId] = useState('gsi_ort_old');
  const [compareMode, setCompareMode] = useState(false);
  const [tileError, setTileError] = useState<string | null>(null);

  // マーカーアイコン
  const createMarkerIcon = () => L.divIcon({
    className: 'custom-marker',
    html: '<div class="marker-pin">📍</div>',
    iconSize: [30, 30],
    iconAnchor: [15, 30]
  });

  // レイヤー作成
  const createLayer = useCallback((option: LayerOption) => {
    return L.tileLayer(option.url, {
      attribution: option.attribution,
      maxZoom: option.maxZoom,
      maxNativeZoom: option.maxNativeZoom,
      tms: option.tms || false
    });
  }, []);

  // マップ同期
  const syncMaps = useCallback((source: L.Map, target: L.Map) => {
    if (isSyncingRef.current) return;
    isSyncingRef.current = true;
    target.setView(source.getCenter(), source.getZoom(), { animate: false });
    setTimeout(() => { isSyncingRef.current = false; }, 50);
  }, []);

  // マップ初期化
  useEffect(() => {
    if (!leftMapRef.current || !rightMapRef.current) return;
    if (leftMapInstanceRef.current || rightMapInstanceRef.current) return;

    // 左マップ作成（maxZoomを高く設定して、タイルがなくても拡大表示）
    const leftMap = L.map(leftMapRef.current, {
      zoomControl: true,
      attributionControl: true,
      maxZoom: 20
    }).setView([center.lat, center.lng], 14);

    // 右マップ作成（ズームコントロールなし、同じmaxZoom）
    const rightMap = L.map(rightMapRef.current, {
      zoomControl: false,
      attributionControl: false,
      maxZoom: 20
    }).setView([center.lat, center.lng], 14);

    // 初期レイヤー設定
    const leftOption = LAYER_OPTIONS.find(l => l.id === 'gsi_photo') || LAYER_OPTIONS[0];
    const leftLayer = createLayer(leftOption);
    leftLayer.addTo(leftMap);
    leftLayerRef.current = leftLayer;

    const rightOption = LAYER_OPTIONS.find(l => l.id === 'gsi_ort_old') || LAYER_OPTIONS[3];
    const rightLayer = createLayer(rightOption);
    rightLayer.addTo(rightMap);
    rightLayerRef.current = rightLayer;

    // マップ同期イベント
    leftMap.on('move', () => syncMaps(leftMap, rightMap));
    leftMap.on('zoom', () => syncMaps(leftMap, rightMap));
    rightMap.on('move', () => syncMaps(rightMap, leftMap));
    rightMap.on('zoom', () => syncMaps(rightMap, leftMap));

    // クリックイベント（左マップのみ、選択モード時のみ）
    leftMap.on('click', (e: L.LeafletMouseEvent) => {
      if (selectionModeRef.current) {
        onLocationSelect({ lat: e.latlng.lat, lng: e.latlng.lng });
      }
    });

    leftMapInstanceRef.current = leftMap;
    rightMapInstanceRef.current = rightMap;

    return () => {
      leftMap.remove();
      rightMap.remove();
      leftMapInstanceRef.current = null;
      rightMapInstanceRef.current = null;
    };
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // 左レイヤー変更
  const handleLeftLayerChange = useCallback((e: React.ChangeEvent<HTMLSelectElement>) => {
    const newLayerId = e.target.value;
    setLeftLayerId(newLayerId);

    const map = leftMapInstanceRef.current;
    if (!map) return;

    const option = LAYER_OPTIONS.find(l => l.id === newLayerId);
    if (!option) return;

    if (leftLayerRef.current) {
      map.removeLayer(leftLayerRef.current);
    }

    const newLayer = createLayer(option);
    newLayer.addTo(map);
    leftLayerRef.current = newLayer;
  }, [createLayer]);

  // 右レイヤー変更
  const handleRightLayerChange = useCallback((e: React.ChangeEvent<HTMLSelectElement>) => {
    const newLayerId = e.target.value;
    setRightLayerId(newLayerId);

    const map = rightMapInstanceRef.current;
    if (!map) return;

    const option = LAYER_OPTIONS.find(l => l.id === newLayerId);
    if (!option) return;

    if (rightLayerRef.current) {
      map.removeLayer(rightLayerRef.current);
    }

    const newLayer = createLayer(option);
    newLayer.addTo(map);
    rightLayerRef.current = newLayer;

    // タイルエラーハンドリング
    let hasError = false;
    newLayer.on('tileerror', () => {
      if (!hasError && option.coverage !== '全国') {
        setTileError(`「${option.name}」はこの地域では利用できない可能性があります`);
        hasError = true;
      }
    });
    setTileError(null);
  }, [createLayer]);

  // 選択位置にマーカーを表示
  useEffect(() => {
    const leftMap = leftMapInstanceRef.current;
    const rightMap = rightMapInstanceRef.current;
    if (!leftMap || !rightMap) return;

    // 既存マーカー削除
    if (leftMarkerRef.current) {
      leftMarkerRef.current.remove();
      leftMarkerRef.current = null;
    }
    if (rightMarkerRef.current) {
      rightMarkerRef.current.remove();
      rightMarkerRef.current = null;
    }

    if (selectedLocation) {
      const icon = createMarkerIcon();
      leftMarkerRef.current = L.marker(
        [selectedLocation.lat, selectedLocation.lng],
        { icon, zIndexOffset: 1000 }
      ).addTo(leftMap);

      rightMarkerRef.current = L.marker(
        [selectedLocation.lat, selectedLocation.lng],
        { icon, zIndexOffset: 1000 }
      ).addTo(rightMap);

      leftMap.setView([selectedLocation.lat, selectedLocation.lng], leftMap.getZoom());
    }
  }, [selectedLocation]);

  // 比較モード切り替え
  useEffect(() => {
    if (rightMapRef.current) {
      rightMapRef.current.style.display = compareMode ? 'block' : 'none';
    }
    // display:none→blockの後にLeafletのサイズ再計算が必要
    if (compareMode && rightMapInstanceRef.current) {
      setTimeout(() => {
        rightMapInstanceRef.current?.invalidateSize();
      }, 100);
    }
  }, [compareMode]);

  // 選択解除ハンドラ
  const handleClearSelection = useCallback(() => {
    if (leftMarkerRef.current) {
      leftMarkerRef.current.remove();
      leftMarkerRef.current = null;
    }
    if (rightMarkerRef.current) {
      rightMarkerRef.current.remove();
      rightMarkerRef.current = null;
    }
    onClearSelection();
  }, [onClearSelection]);

  // ドラッグハンドラー
  const handleDragStart = (e: React.MouseEvent | React.TouchEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(true);
  };

  const handleDragEnd = () => {
    setIsDragging(false);
  };

  const handleDragMove = useCallback((e: React.MouseEvent | React.TouchEvent) => {
    if (!isDragging || !containerRef.current) return;

    const rect = containerRef.current.getBoundingClientRect();
    const clientX = 'touches' in e ? e.touches[0].clientX : e.clientX;
    const x = clientX - rect.left;
    const percentage = Math.min(Math.max((x / rect.width) * 100, 5), 95);
    setSliderPosition(percentage);
  }, [isDragging]);

  return (
    <div className="map-compare-wrapper">
      {/* レイヤー選択UI */}
      <div className="map-compare-controls">
        <label className="compare-toggle">
          <input
            type="checkbox"
            checked={compareMode}
            onChange={(e) => setCompareMode(e.target.checked)}
          />
          <span>比較モード</span>
        </label>

        {selectedLocation && (
          <button
            className="clear-selection-btn"
            onClick={handleClearSelection}
            title="選択を解除"
          >
            ✕ 選択解除
          </button>
        )}

        {compareMode && (
          <div className="layer-selectors">
            <div className="layer-select">
              <span className="layer-label">左側:</span>
              <select
                value={leftLayerId}
                onChange={handleLeftLayerChange}
              >
                {LAYER_OPTIONS.map(opt => (
                  <option key={opt.id} value={opt.id}>
                    {opt.name}{opt.coverage !== '全国' ? ` (${opt.coverage})` : ''}
                  </option>
                ))}
              </select>
            </div>
            <div className="layer-select">
              <span className="layer-label">右側:</span>
              <select
                value={rightLayerId}
                onChange={handleRightLayerChange}
              >
                {LAYER_OPTIONS.map(opt => (
                  <option key={opt.id} value={opt.id}>
                    {opt.name}{opt.coverage !== '全国' ? ` (${opt.coverage})` : ''}
                  </option>
                ))}
              </select>
            </div>
          </div>
        )}
      </div>

      {/* タイルエラー警告 */}
      {tileError && (
        <div className="tile-error-alert">
          {tileError}
        </div>
      )}

      {/* 地図コンテナ */}
      <div
        ref={containerRef}
        className="map-compare-container"
        onMouseMove={handleDragMove}
        onMouseUp={handleDragEnd}
        onMouseLeave={handleDragEnd}
        onTouchMove={handleDragMove}
        onTouchEnd={handleDragEnd}
      >
        {/* 左マップ（ベース、フル表示） */}
        <div
          ref={leftMapRef}
          className="map-layer map-left"
        />

        {/* 右マップ（上に重ねてclipで切り取り） */}
        <div
          ref={rightMapRef}
          className="map-layer map-right"
          style={{
            clipPath: compareMode ? `inset(0 0 0 ${sliderPosition}%)` : 'none',
            display: compareMode ? 'block' : 'none'
          }}
        />

        {/* スライダー */}
        {compareMode && (
          <div
            className="compare-slider"
            style={{ left: `${sliderPosition}%` }}
            onMouseDown={handleDragStart}
            onTouchStart={handleDragStart}
          >
            <div className="slider-handle">
              <div className="slider-arrows">
                <span>◀</span>
                <span>▶</span>
              </div>
            </div>
            <div className="slider-line" />
          </div>
        )}

        {/* レイヤーラベル */}
        {compareMode && (
          <>
            <div className="layer-indicator left">
              {LAYER_OPTIONS.find(l => l.id === leftLayerId)?.name}
            </div>
            <div className="layer-indicator right">
              {LAYER_OPTIONS.find(l => l.id === rightLayerId)?.name}
            </div>
          </>
        )}
      </div>

      <p className="map-hint">
        {compareMode
          ? 'スライダーをドラッグして左右の地図を比較'
          : '地図をタップして場所を選択'}
      </p>
    </div>
  );
}
