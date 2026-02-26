// 妖怪ID/名前/絵文字 → イラスト画像パスのマッピング
// 画像が未作成の妖怪はundefinedを返し、呼び出し側でemoji表示にフォールバック

export type YoukaiExpression = 'default' | 'futuu' | 'egao' | 'sinpai';

interface YoukaiImageSet {
  default: string;
  futuu: string;
  egao: string;
  sinpai: string;
}

const YOUKAI_IMAGE_MAP: Record<string, string> = {
  kappa: '/images/youkai/kappa.png',
  namazu: '/images/youkai/namazu.png',
  kasha: '/images/youkai/kasya.png',
  tsuchigumo: '/images/youkai/tutigumo.png',
  tengu: '/images/youkai/tengu.png',
  yukionna: '/images/youkai/yukionna.png',
  hinokagutsuchi: '/images/youkai/hinokagututi.png',
};

// 表情付き画像セット
const YOUKAI_EXPRESSION_MAP: Record<string, YoukaiImageSet> = {
  kappa: {
    default: '/images/youkai/kappa.png',
    futuu: '/images/youkai/kappa_futuu.png',
    egao: '/images/youkai/kappa_egao.png',
    sinpai: '/images/youkai/kappa_sinpai.png',
  },
  namazu: {
    default: '/images/youkai/namazu.png',
    futuu: '/images/youkai/namazu_futuu.png',
    egao: '/images/youkai/namazu_egao.png',
    sinpai: '/images/youkai/namazu_sinpai.png',
  },
  kasha: {
    default: '/images/youkai/kasya.png',
    futuu: '/images/youkai/kasya_futuu.png',
    egao: '/images/youkai/kasya_egao.png',
    sinpai: '/images/youkai/kasya_sinpai.png',
  },
  tsuchigumo: {
    default: '/images/youkai/tutigumo.png',
    futuu: '/images/youkai/tutigumo_futuu.png',
    egao: '/images/youkai/tutigumo_egao.png',
    sinpai: '/images/youkai/tutigumo_sinpai.png',
  },
  tengu: {
    default: '/images/youkai/tengu.png',
    futuu: '/images/youkai/tengu_futuu.png',
    egao: '/images/youkai/tengu_egao.png',
    sinpai: '/images/youkai/tengu_sinpai.png',
  },
  yukionna: {
    default: '/images/youkai/yukionna.png',
    futuu: '/images/youkai/yukionna_futuu.png',
    egao: '/images/youkai/yukionna_egao.png',
    sinpai: '/images/youkai/yukionna_sinpai.png',
  },
  hinokagutsuchi: {
    default: '/images/youkai/hinokagututi.png',
    futuu: '/images/youkai/hinokagututi_futuu.png',
    egao: '/images/youkai/hinokagututi_egao.png',
    sinpai: '/images/youkai/hinokagututi_sinpai.png',
  },
};

// emotion → 表情マッピング
const EMOTION_EXPRESSION_MAP: Record<string, YoukaiExpression> = {
  friendly: 'egao',
  warm: 'egao',
  reassuring: 'egao',
  relieved: 'egao',
  calm: 'futuu',
  teaching: 'futuu',
  thinking: 'futuu',
  curious: 'futuu',
  serious: 'sinpai',
  suggesting: 'sinpai',
  warning: 'sinpai',
};

const YOUKAI_NAME_MAP: Record<string, string> = {
  '河童': 'kappa',
  '大ナマズ': 'namazu',
  '土蜘蛛': 'tsuchigumo',
  '天狗': 'tengu',
  '火車': 'kasha',
  '雪女': 'yukionna',
  'ヒノカグツチ': 'hinokagutsuchi',
};

const YOUKAI_EMOJI_MAP: Record<string, string> = {
  '🥒': 'kappa',
  '🐟': 'namazu',
  '🕷️': 'tsuchigumo',
  '🌪️': 'tengu',
  '🔥': 'kasha',
  '❄️': 'yukionna',
  '🌋': 'hinokagutsuchi',
};

/** youkai_id から画像パスを取得 */
export function getYoukaiImageById(id: string): string | undefined {
  return YOUKAI_IMAGE_MAP[id];
}

/** speaker_name から画像パスを取得 */
export function getYoukaiImageByName(name: string): string | undefined {
  const id = YOUKAI_NAME_MAP[name];
  return id ? YOUKAI_IMAGE_MAP[id] : undefined;
}

/** emoji から画像パスを取得 */
export function getYoukaiImageByEmoji(emoji: string): string | undefined {
  const id = YOUKAI_EMOJI_MAP[emoji];
  return id ? YOUKAI_IMAGE_MAP[id] : undefined;
}

/** speaker_name + emotion から表情付き画像パスを取得 */
export function getYoukaiExpressionImage(name: string, emotion: string): string | undefined {
  const id = YOUKAI_NAME_MAP[name];
  if (!id) return undefined;
  const expressionSet = YOUKAI_EXPRESSION_MAP[id];
  if (!expressionSet) return undefined;
  const expression = EMOTION_EXPRESSION_MAP[emotion] || 'futuu';
  return expressionSet[expression];
}

/** speaker_name からデフォルト表情（futuu）の画像パスを取得 */
export function getYoukaiDefaultExpression(name: string): string | undefined {
  const id = YOUKAI_NAME_MAP[name];
  if (!id) return undefined;
  const expressionSet = YOUKAI_EXPRESSION_MAP[id];
  return expressionSet?.futuu;
}

/** speaker_name からIDを取得 */
export function getYoukaiIdByName(name: string): string | undefined {
  return YOUKAI_NAME_MAP[name];
}
