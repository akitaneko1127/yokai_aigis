export interface QuizQuestion {
  question: string;
  choices: string[];
  correctIndex: number;
  explanation: string;
  category: 'earthquake' | 'flood' | 'tsunami' | 'fire' | 'general';
}

export const QUIZ_DATA: QuizQuestion[] = [
  {
    question: '地震が発生したとき、まず最初にすべきことは?',
    choices: [
      '机の下に隠れて頭を守る',
      'すぐに外に飛び出す',
      'エレベーターで避難する',
      'ガスの元栓を閉める'
    ],
    correctIndex: 0,
    explanation: 'まず自分の身を守ることが最優先です。丈夫な机の下に入り、揺れが収まるのを待ちましょう。',
    category: 'earthquake'
  },
  {
    question: '災害用伝言ダイヤルの番号は?',
    choices: [
      '110',
      '171',
      '119',
      '177'
    ],
    correctIndex: 1,
    explanation: '「171（いない）」で覚えましょう。災害時に安否確認のメッセージを録音・再生できます。',
    category: 'general'
  },
  {
    question: '洪水のとき、避難で最も危険な行動は?',
    choices: [
      '高台に移動する',
      '上の階に避難する',
      '車で冠水した道路を走る',
      '近くの避難所に徒歩で向かう'
    ],
    correctIndex: 2,
    explanation: 'わずか30cmの水深でもエンジンが止まり、50cmで車が流されます。冠水した道路は絶対に車で通らないでください。',
    category: 'flood'
  },
  {
    question: '津波警報が出たとき、正しい避難行動は?',
    choices: [
      '海の様子を見に行く',
      'できるだけ高い場所に素早く逃げる',
      '防潮堤の内側にいれば安全',
      '津波が見えてから逃げても間に合う'
    ],
    correctIndex: 1,
    explanation: '津波は見えてからでは逃げ切れません。警報が出たら直ちに高台や頑丈なビルの上層階に避難してください。',
    category: 'tsunami'
  },
  {
    question: '非常持ち出し袋に最低限必要ないものは?',
    choices: [
      '飲料水',
      '携帯ラジオ',
      'ノートパソコン',
      '懐中電灯'
    ],
    correctIndex: 2,
    explanation: '飲料水、ラジオ、懐中電灯は必須です。重くかさばるノートパソコンより、モバイルバッテリーの方が実用的です。',
    category: 'general'
  },
  {
    question: '火災で煙が充満しているとき、どう避難する?',
    choices: [
      '立ったまま素早く走る',
      '姿勢を低くして壁伝いに進む',
      'エレベーターを使う',
      '窓を開けて換気する'
    ],
    correctIndex: 1,
    explanation: '煙は上に溜まるため、姿勢を低くすることで新鮮な空気を確保できます。濡れたタオルで口を覆うとさらに効果的です。',
    category: 'fire'
  },
  {
    question: '地震の震度とマグニチュードの違いは?',
    choices: [
      '同じ意味の別の表現',
      '震度は揺れの強さ、マグニチュードは地震のエネルギー',
      'マグニチュードは揺れの強さ、震度はエネルギー',
      '震度は海外で使い、マグニチュードは日本で使う'
    ],
    correctIndex: 1,
    explanation: '震度は観測地点での揺れの強さ、マグニチュードは地震そのもののエネルギーの大きさを表します。',
    category: 'earthquake'
  },
  {
    question: '大雨のとき「警戒レベル4」が発令されたら?',
    choices: [
      '今後の情報に注意する',
      '高齢者は避難を開始する',
      '全員が危険な場所から避難する',
      '命の危険、直ちに安全確保'
    ],
    correctIndex: 2,
    explanation: 'レベル4「避難指示」は対象地域の全員が危険な場所から避難するタイミングです。レベル5では既に災害が発生している可能性があります。',
    category: 'flood'
  }
];
