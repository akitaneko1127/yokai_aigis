import { useEffect, useRef, useState } from 'react';
import L from 'leaflet';
import type { Location } from '../../types';
import { HISTORICAL_LAYERS_OLDEST_FIRST, LAYER_OPTIONS } from '../../data/layerOptions';
import type { LayerOption } from '../../data/layerOptions';

interface HistoricalMapMiniProps {
  selectedLocation: Location;
}

export function HistoricalMapMini({ selectedLocation }: HistoricalMapMiniProps) {
  const mapRef = useRef<HTMLDivElement>(null);
  const mapInstanceRef = useRef<L.Map | null>(null);
  const tileLayerRef = useRef<L.TileLayer | null>(null);
  const historicalLayerRef = useRef<LayerOption | null>(null);
  const [currentLayer, setCurrentLayer] = useState<LayerOption | null>(null);
  const [showModern, setShowModern] = useState(false);
  const [searching, setSearching] = useState(true);

  useEffect(() => {
    if (!mapRef.current) return;
    // Strict Mode対策: 前回のmapが残っていたら破棄
    if (mapInstanceRef.current) {
      mapInstanceRef.current.remove();
      mapInstanceRef.current = null;
    }

    const map = L.map(mapRef.current, {
      zoomControl: false,
      attributionControl: true,
      dragging: false,
      scrollWheelZoom: false,
      doubleClickZoom: false,
      touchZoom: false,
      boxZoom: false,
      keyboard: false,
      maxZoom: 17
    }).setView([selectedLocation.lat, selectedLocation.lng], 14);

    L.marker([selectedLocation.lat, selectedLocation.lng], {
      icon: L.divIcon({
        className: 'custom-marker',
        html: '<div class="marker-pin">📍</div>',
        iconSize: [30, 30],
        iconAnchor: [15, 30]
      })
    }).addTo(map);

    mapInstanceRef.current = map;

    // mapインスタンスの有効性チェック（クロージャ内のmapが現在のインスタンスか）
    const isMapAlive = () => mapInstanceRef.current === map;

    // 古い順にタイルを試す
    const tryNextLayer = (index: number) => {
      if (!isMapAlive()) return;

      if (index >= HISTORICAL_LAYERS_OLDEST_FIRST.length) {
        const fallback = LAYER_OPTIONS.find(l => l.id === 'gsi_ort_old')!;
        applyLayer(fallback);
        setSearching(false);
        return;
      }

      const layer = HISTORICAL_LAYERS_OLDEST_FIRST[index];
      const tileLayer = L.tileLayer(layer.url, {
        attribution: layer.attribution,
        maxZoom: layer.maxZoom,
        maxNativeZoom: layer.maxNativeZoom,
        tms: layer.tms || false
      });

      let loadCount = 0;
      let errorCount = 0;
      let resolved = false;

      const resolve = (success: boolean) => {
        if (resolved || !isMapAlive()) return;
        resolved = true;
        tileLayer.off('tileload');
        tileLayer.off('tileerror');

        if (success) {
          historicalLayerRef.current = layer;
          setCurrentLayer(layer);
          tileLayerRef.current = tileLayer;
          setSearching(false);
        } else {
          try { map.removeLayer(tileLayer); } catch { /* already removed */ }
          tryNextLayer(index + 1);
        }
      };

      tileLayer.on('tileload', () => {
        loadCount++;
        if (loadCount >= 2) resolve(true);
      });

      tileLayer.on('tileerror', () => {
        errorCount++;
        if (errorCount >= 3) resolve(false);
      });

      if (!isMapAlive()) return;
      tileLayer.addTo(map);

      setTimeout(() => {
        if (!resolved) resolve(errorCount > loadCount);
      }, 3000);
    };

    const applyLayer = (layer: LayerOption) => {
      if (!isMapAlive()) return;
      if (tileLayerRef.current) {
        try { map.removeLayer(tileLayerRef.current); } catch { /* already removed */ }
      }
      const tileLayer = L.tileLayer(layer.url, {
        attribution: layer.attribution,
        maxZoom: layer.maxZoom,
        maxNativeZoom: layer.maxNativeZoom,
        tms: layer.tms || false
      });
      tileLayer.addTo(map);
      tileLayerRef.current = tileLayer;
      setCurrentLayer(layer);
    };

    tryNextLayer(0);

    return () => {
      map.remove();
      mapInstanceRef.current = null;
    };
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const toggleModern = () => {
    const map = mapInstanceRef.current;
    if (!map) return;

    const applyToggleLayer = (layer: LayerOption) => {
      if (tileLayerRef.current) {
        try { map.removeLayer(tileLayerRef.current); } catch { /* ok */ }
      }
      const tileLayer = L.tileLayer(layer.url, {
        attribution: layer.attribution,
        maxZoom: layer.maxZoom,
        maxNativeZoom: layer.maxNativeZoom,
        tms: layer.tms || false
      });
      tileLayer.addTo(map);
      tileLayerRef.current = tileLayer;
      setCurrentLayer(layer);
    };

    if (showModern) {
      if (historicalLayerRef.current) applyToggleLayer(historicalLayerRef.current);
    } else {
      const modern = LAYER_OPTIONS.find(l => l.id === 'gsi_photo')!;
      applyToggleLayer(modern);
    }
    setShowModern(!showModern);
  };

  return (
    <div className="historical-map-mini">
      <div className="historical-map-mini-container" ref={mapRef} />
      {searching ? (
        <p className="historical-map-mini-status">古地図を探しています...</p>
      ) : (
        <div className="historical-map-mini-info">
          <span className="historical-map-mini-label">
            {showModern ? '現代の航空写真' : historicalLayerRef.current?.name || currentLayer?.name || ''}
          </span>
          <button
            className="historical-map-mini-toggle"
            onClick={toggleModern}
          >
            {showModern ? '古地図に戻す' : '現代と比較'}
          </button>
        </div>
      )}
    </div>
  );
}
