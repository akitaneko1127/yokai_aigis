const GSI_ATTRIBUTION = '<a href="https://maps.gsi.go.jp/development/ichiran.html">国土地理院</a>';
const KONJAKU_ATTRIBUTION = '<a href="https://ktgis.net/kjmapw/">今昔マップ on the web</a>';

export interface LayerOption {
  id: string;
  name: string;
  url: string;
  attribution: string;
  maxZoom: number;
  maxNativeZoom: number;
  coverage?: string;
  tms?: boolean;
}

export const LAYER_OPTIONS: LayerOption[] = [
  // 現代の地図
  {
    id: 'osm',
    name: '標準地図',
    url: 'https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',
    attribution: '&copy; OpenStreetMap',
    maxZoom: 20,
    maxNativeZoom: 19,
    coverage: '全国'
  },
  {
    id: 'gsi_std',
    name: '地理院地図',
    url: 'https://cyberjapandata.gsi.go.jp/xyz/std/{z}/{x}/{y}.png',
    attribution: GSI_ATTRIBUTION,
    maxZoom: 20,
    maxNativeZoom: 18,
    coverage: '全国'
  },
  {
    id: 'gsi_photo',
    name: '航空写真',
    url: 'https://cyberjapandata.gsi.go.jp/xyz/seamlessphoto/{z}/{x}/{y}.jpg',
    attribution: GSI_ATTRIBUTION,
    maxZoom: 20,
    maxNativeZoom: 18,
    coverage: '全国'
  },
  // 国土地理院の歴史的地図
  {
    id: 'gsi_ort_old',
    name: '1960年代航空写真',
    url: 'https://cyberjapandata.gsi.go.jp/xyz/ort_old10/{z}/{x}/{y}.png',
    attribution: GSI_ATTRIBUTION,
    maxZoom: 20,
    maxNativeZoom: 17,
    coverage: '全国'
  },
  {
    id: 'gsi_ort_usa',
    name: '1945-50年航空写真',
    url: 'https://cyberjapandata.gsi.go.jp/xyz/ort_USA10/{z}/{x}/{y}.png',
    attribution: GSI_ATTRIBUTION,
    maxZoom: 20,
    maxNativeZoom: 17,
    coverage: '全国'
  },
  {
    id: 'gsi_ort_riku',
    name: '1936-42年航空写真',
    url: 'https://cyberjapandata.gsi.go.jp/xyz/ort_riku10/{z}/{x}/{y}.png',
    attribution: GSI_ATTRIBUTION,
    maxZoom: 20,
    maxNativeZoom: 17,
    coverage: '東京・大阪'
  },
  {
    id: 'gsi_rapid',
    name: '迅速測図（明治）',
    url: 'https://cyberjapandata.gsi.go.jp/xyz/rapid/{z}/{x}/{y}.png',
    attribution: GSI_ATTRIBUTION,
    maxZoom: 20,
    maxNativeZoom: 18,
    coverage: '関東地方'
  },
  {
    id: 'gsi_swale',
    name: '明治期低湿地',
    url: 'https://cyberjapandata.gsi.go.jp/xyz/swale/{z}/{x}/{y}.png',
    attribution: GSI_ATTRIBUTION,
    maxZoom: 20,
    maxNativeZoom: 16,
    coverage: '一部地域'
  },
  {
    id: 'gsi_flood',
    name: '治水地形分類図',
    url: 'https://cyberjapandata.gsi.go.jp/xyz/lcmfc2/{z}/{x}/{y}.png',
    attribution: GSI_ATTRIBUTION,
    maxZoom: 20,
    maxNativeZoom: 16,
    coverage: '一部地域'
  },
  // 今昔マップ - 京阪神
  {
    id: 'konjaku_keihansin_meiji',
    name: '明治(1892-1910)京阪神',
    url: 'https://ktgis.net/kjmapw/kjtilemap/keihansin/00/{z}/{x}/{y}.png',
    attribution: KONJAKU_ATTRIBUTION,
    maxZoom: 20,
    maxNativeZoom: 16,
    coverage: '京阪神',
    tms: true
  },
  {
    id: 'konjaku_keihansin_taisho',
    name: '大正(1922-23)京阪神',
    url: 'https://ktgis.net/kjmapw/kjtilemap/keihansin/01/{z}/{x}/{y}.png',
    attribution: KONJAKU_ATTRIBUTION,
    maxZoom: 20,
    maxNativeZoom: 16,
    coverage: '京阪神',
    tms: true
  },
  // 今昔マップ - 中京圏
  {
    id: 'konjaku_chukyo_meiji',
    name: '明治(1888-98)中京',
    url: 'https://ktgis.net/kjmapw/kjtilemap/chukyo/00/{z}/{x}/{y}.png',
    attribution: KONJAKU_ATTRIBUTION,
    maxZoom: 20,
    maxNativeZoom: 16,
    coverage: '名古屋圏',
    tms: true
  },
  // 今昔マップ - 広島
  {
    id: 'konjaku_hiroshima_meiji',
    name: '明治(1894-99)広島',
    url: 'https://ktgis.net/kjmapw/kjtilemap/hiroshima/00/{z}/{x}/{y}.png',
    attribution: KONJAKU_ATTRIBUTION,
    maxZoom: 20,
    maxNativeZoom: 16,
    coverage: '広島',
    tms: true
  },
  // 今昔マップ - 札幌
  {
    id: 'konjaku_sapporo_taisho',
    name: '大正(1916)札幌',
    url: 'https://ktgis.net/kjmapw/kjtilemap/sapporo/00/{z}/{x}/{y}.png',
    attribution: KONJAKU_ATTRIBUTION,
    maxZoom: 20,
    maxNativeZoom: 16,
    coverage: '札幌',
    tms: true
  },
  // 今昔マップ - 福岡
  {
    id: 'konjaku_fukuoka_taisho',
    name: '大正(1922-26)福岡',
    url: 'https://ktgis.net/kjmapw/kjtilemap/fukuoka/00/{z}/{x}/{y}.png',
    attribution: KONJAKU_ATTRIBUTION,
    maxZoom: 20,
    maxNativeZoom: 16,
    coverage: '福岡',
    tms: true
  },
  // 今昔マップ - 仙台
  {
    id: 'konjaku_sendai_showa',
    name: '昭和初期(1928-33)仙台',
    url: 'https://ktgis.net/kjmapw/kjtilemap/sendai/00/{z}/{x}/{y}.png',
    attribution: KONJAKU_ATTRIBUTION,
    maxZoom: 20,
    maxNativeZoom: 16,
    coverage: '仙台',
    tms: true
  },
  // 今昔マップ - 首都圏
  {
    id: 'konjaku_tokyo_meiji',
    name: '明治(1896-1909)首都圏',
    url: 'https://ktgis.net/kjmapw/kjtilemap/tokyo50/00/{z}/{x}/{y}.png',
    attribution: KONJAKU_ATTRIBUTION,
    maxZoom: 20,
    maxNativeZoom: 15,
    coverage: '首都圏',
    tms: true
  }
];

// 古い順にソートした歴史地図レイヤー（ローディング画面の古地図表示用）
export const HISTORICAL_LAYERS_OLDEST_FIRST: LayerOption[] = [
  LAYER_OPTIONS.find(l => l.id === 'konjaku_chukyo_meiji')!,     // 1888-98 名古屋圏
  LAYER_OPTIONS.find(l => l.id === 'konjaku_keihansin_meiji')!,   // 1892-1910 京阪神
  LAYER_OPTIONS.find(l => l.id === 'konjaku_hiroshima_meiji')!,   // 1894-99 広島
  LAYER_OPTIONS.find(l => l.id === 'konjaku_tokyo_meiji')!,       // 1896-1909 首都圏
  LAYER_OPTIONS.find(l => l.id === 'gsi_rapid')!,                 // 明治 関東
  LAYER_OPTIONS.find(l => l.id === 'gsi_swale')!,                 // 明治 一部地域
  LAYER_OPTIONS.find(l => l.id === 'konjaku_sapporo_taisho')!,    // 大正 1916 札幌
  LAYER_OPTIONS.find(l => l.id === 'konjaku_keihansin_taisho')!,  // 大正 1922-23 京阪神
  LAYER_OPTIONS.find(l => l.id === 'konjaku_fukuoka_taisho')!,    // 大正 1922-26 福岡
  LAYER_OPTIONS.find(l => l.id === 'konjaku_sendai_showa')!,      // 昭和初期 1928-33 仙台
  LAYER_OPTIONS.find(l => l.id === 'gsi_ort_riku')!,              // 1936-42 東京・大阪
  LAYER_OPTIONS.find(l => l.id === 'gsi_ort_usa')!,               // 1945-50 全国
  LAYER_OPTIONS.find(l => l.id === 'gsi_ort_old')!,               // 1960s 全国（究極フォールバック）
];
