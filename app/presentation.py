"""Labels and display rules shared by the HTML pages (01b 4 display, 7.4 warnings)."""

# metric -> (label, decimals of a single value). Statistics get one more decimal.
METRIC_DISPLAY = {
    "tds_pct": ("TDS (%)", 2),
    "ey_pct": ("EY (%)", 1),
    "beverage_mass_g": ("飲料重量 (g)", 1),
    "brew_time_s": ("抽出時間 (秒)", 0),
    "overall_score": ("総合点 (1〜10)", 0),
    "acidity": ("酸味の強さ (0〜5)", 0),
    "sweetness": ("甘味の強さ (0〜5)", 0),
    "bitterness": ("苦味の強さ (0〜5)", 0),
    "body": ("ボディの強さ (0〜5)", 0),
    "aroma": ("香りの強さ (0〜5)", 0),
}

WARNING_MESSAGES = {
    "N_SMALL": "いずれかの条件で試行が5杯未満です。平均やSDは杯数が増えると大きく変わり得ます。",
    "ORDER_CONFOUNDED": "一方の条件をすべて淹れてから他方を淹れています。豆の経時変化や室温などと条件差を区別できません。",
    "MULTIPLE_VARIABLES_CHANGED": "計画の差分が2項目以上あります。差がどの変更によるものかは分けられません。",
    "NO_DIFFERENCE_IN_PLAN": "2条件の計画に差分がありません。",
    "NOT_BLINDED": "条件を知ったまま評価した杯があります。官能評価に期待の影響が入り得ます。",
    "DEVIATED_OR_EXCLUDED": "比較から外した試行が{count}件あります（除外、または計画から逸脱）。",
    "MEASUREMENT_REPEATS_MISSING": "同じ飲料を2回以上測った試行がなく、測定のばらつきを試行間のばらつきから分けられません。",
    "EY_METHOD_ASSUMPTION": "透過式以外の抽出方式です。飲料重量法のEYは、粉に残った液を数えないため過小評価になり得ます。",
}

STATUS_LABELS = {
    "DRAFT": "計画中（試行なし）",
    "RUNNING": "実施中",
    "PLANNED_REACHED": "予定反復数に到達",
}

STEP_TYPE_LABELS = {"pour": "注湯", "agitate": "攪拌", "other": "その他"}

AGITATION_METHOD_LABELS = {"stir": "かき混ぜる", "swirl": "回す", "other": "その他"}

EXTRACTION_STYLE_LABELS = {
    "percolation": "透過式",
    "immersion": "浸漬式",
    "hybrid": "ハイブリッド",
    "unknown": "不明",
}


def warning_message(code: str, count: int | None) -> str:
    return WARNING_MESSAGES.get(code, code).format(count=count)
