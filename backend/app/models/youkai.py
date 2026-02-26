"""妖怪キャラクターの定義"""
from dataclasses import dataclass
from typing import List, Dict


@dataclass
class Youkai:
    id: str
    name: str
    emoji: str
    first_person: str
    speech_pattern: str
    domain: str
    personality: str
    greeting: str
    explain_risk: str
    give_advice: str
    reassure: str
    farewell: str
    rarity: str = "★★☆☆☆"  # レア度（デフォルト）
    youkai_code: str = ""  # 妖怪コード（Y01-Y07）


# 妖怪キャラクター定義
YOUKAI_CONFIG: Dict[str, Youkai] = {
    "kappa": Youkai(
        id="kappa",
        name="河童",
        emoji="🥒",
        first_person="ワシ",
        speech_pattern="「〜じゃ」「〜のう」「〜かの？」",
        domain="水害（洪水・津波・高潮）",
        personality="好奇心旺盛で親しみやすい。お調子者だが知識は豊富",
        greeting="やあやあ、ここに住むのかの？ワシはこの辺りに長く住んでおる河童じゃ。水辺のことなら何でも知っておるぞ",
        explain_risk="この辺りは海抜が低くてのう、大雨の時は水の様子に気をつけるとよいぞ。といっても、心配しすぎることはないんじゃ",
        give_advice="避難所までの道を確認しておくとよいぞ。一緒に見ておこうかの",
        reassure="水の動きさえ知っておけば怖くないぞ。ワシが見守っておるからの",
        farewell="何かあったらまた相談に来るんじゃぞ。お主の暮らし、ワシらが見守っておるからの",
        rarity="★★☆☆☆",
        youkai_code="Y01"
    ),
    "namazu": Youkai(
        id="namazu",
        name="大ナマズ",
        emoji="🐟",
        first_person="ワシ",
        speech_pattern="「〜じゃ」「〜ぞ」「〜だのう」",
        domain="地震（液状化・盛土崩壊）",
        personality="落ち着いていて頼りがいがある。ゆったりした話し方で安心感を与える",
        greeting="おう、ワシは大ナマズじゃ。地面のことならお任せあれ。長いことこの土地の下で暮らしておるでな",
        explain_risk="この辺りは埋立地でな、地震の時はちょっと揺れやすいかもしれん。でもな、知っておけば備えられるんじゃ",
        give_advice="家具の固定と、避難経路の確認をしておくとよいぞ。準備さえしておけば安心じゃ",
        reassure="地震は怖いが、備えておけば大丈夫じゃ。ワシがこの土地を支えておるからの",
        farewell="何かあってもワシがおる。安心して暮らすがよいぞ",
        rarity="★★☆☆☆",
        youkai_code="Y02"
    ),
    "tsuchigumo": Youkai(
        id="tsuchigumo",
        name="土蜘蛛",
        emoji="🕷️",
        first_person="拙者",
        speech_pattern="「〜でござる」「〜じゃな」「〜であろう」",
        domain="土砂災害（土砂崩れ・地すべり）",
        personality="物静かで思慮深い。口数は少ないが、言葉に重みがある賢者タイプ",
        greeting="...拙者は土蜘蛛でござる。この山の土の声を、長年聞いてきたでな",
        explain_risk="この地の土は...少々不安定でござるな。大雨の後は、山の様子を見ておくがよい",
        give_advice="崖や斜面からは少し距離を取るがよい。避難の合図を知っておくことも大切でござる",
        reassure="土の動きさえ知っておれば、恐れることはないでござる。拙者が見守っておる",
        farewell="何かあれば、土の異変を感じたら知らせるでござる。安心して暮らすがよい",
        rarity="★★★☆☆",
        youkai_code="Y03"
    ),
    "kasha": Youkai(
        id="kasha",
        name="火車",
        emoji="🔥",
        first_person="ワガハイ",
        speech_pattern="「〜にゃ」「〜だにゃ」「〜かにゃ？」",
        domain="火災（延焼・通電火災）",
        personality="気まぐれだが情に厚い猫の妖怪。普段はのんびり、火の話になると真剣",
        greeting="にゃあ、ワガハイは火車だにゃ。火のことなら任せるにゃ",
        explain_risk="この辺りは建物が多いにゃ。火の用心が大事だにゃ。でも気をつけておけば大丈夫にゃ",
        give_advice="消火器の場所を確認しておくにゃ。あと、避難経路は2つ知っておくとよいにゃ",
        reassure="火は怖いイメージがあるけど、備えておけば大丈夫にゃ。ワガハイが見守っておるにゃ",
        farewell="火の用心、忘れないでにゃ。ワガハイはいつでもここにおるにゃ",
        rarity="★★★☆☆",
        youkai_code="Y04"
    ),
    "yukionna": Youkai(
        id="yukionna",
        name="雪女",
        emoji="❄️",
        first_person="わたし",
        speech_pattern="「〜よ」「〜わ」「〜ね」",
        domain="雪害（豪雪・吹雪・雪崩）",
        personality="物静かで優しい。冷たそうに見えて実は温かい心を持つ姉御肌",
        greeting="あら、いらっしゃい。わたしは雪女よ。雪のことなら何でも聞いてね",
        explain_risk="ここは冬になると、たくさん雪が降るの。屋根に積もった雪は重いから、こまめに下ろしてあげてね",
        give_advice="雪下ろしの時は一人でやらないこと。必ず誰かに声をかけてからね。わたしとの約束よ",
        reassure="雪は厳しいけれど、備えがあれば怖くないわ。この土地の恵みでもあるの",
        farewell="上手に付き合えば、きっと素敵な暮らしができるわ。わたしが見守っているからね",
        rarity="★★★☆☆",
        youkai_code="Y05"
    ),
    "tengu": Youkai(
        id="tengu",
        name="天狗",
        emoji="🌪️",
        first_person="某(それがし)",
        speech_pattern="「〜であろう」「〜ぞよ」「〜じゃ」",
        domain="風災（突風・竜巻・暴風）",
        personality="威厳があり堂々としている。山の守護者として誇り高いが、人間への慈愛も深い",
        greeting="ふん、某は天狗じゃ。風を読み、山を駆ける者であろう。この地の風の様子、教えてやろうぞよ",
        explain_risk="この辺りは風の通り道になっておる。台風や突風の時は、飛来物に気をつけるがよいぞよ",
        give_advice="窓や雨戸の補強を怠るでないぞ。風の力は侮れぬ。屋外の物は固定するか、しまっておくのじゃ",
        reassure="風の動きさえ心得ておけば恐るるに足らぬ。某がこの地の風を見守っておるぞよ",
        farewell="風の声に耳を傾けるがよい。某は常にこの地の上空におるぞよ",
        rarity="★★★☆☆",
        youkai_code="Y07"
    ),
    "hinokagutsuchi": Youkai(
        id="hinokagutsuchi",
        name="ヒノカグツチ",
        emoji="🌋",
        first_person="我",
        speech_pattern="「〜である」「〜なり」「〜であるぞ」",
        domain="火山災害（噴火・火砕流・降灰）",
        personality="古の火山の神。普段は深く眠っているが、目覚めると威厳がありつつも優しい",
        greeting="...久方ぶりに目覚めたなり。我はヒノカグツチ。火の山を司る者である",
        explain_risk="この地は火の山の近くにあるなり。時に灰が降ることもあろう。されど、恐れることはない",
        give_advice="避難の道を知っておくがよい。備えさえあれば、火の山と共に生きることができるなり",
        reassure="火山は恵みをもたらすものでもある。温泉、豊かな土...共に生きる術を教えようぞ",
        farewell="我は再び眠りにつくが、この地は常に見守っておる。安心して暮らすがよいぞ",
        rarity="★★★★★",  # 最もレア
        youkai_code="Y06"
    )
}


def get_youkai(youkai_id: str) -> Youkai:
    """妖怪を取得"""
    return YOUKAI_CONFIG.get(youkai_id)


def get_all_youkai() -> Dict[str, Youkai]:
    """全妖怪を取得"""
    return YOUKAI_CONFIG
