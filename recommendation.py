from models import BrewLogRead, EvaluationRead, RecommendationRead


def _fallback_recommendation(brew_log: BrewLogRead) -> RecommendationRead:
    return RecommendationRead(
        target_log_id=brew_log.id,
        recommendation_mode="experiment",
        action_type="keep_same",
        direction="none",
        amount=0,
        unit="none",
        message="次回も同じ条件で抽出する",
        reason=(
            "現在値が境界または設定単位が不明確なため、"
            "同条件で再確認する"
        ),
    )


def _apply_feasibility_guard(
    brew_log: BrewLogRead,
    recommendation: RecommendationRead,
) -> RecommendationRead:
    if recommendation.action_type == "adjust_water_temp":
        if (
            recommendation.direction == "increase"
            and brew_log.water_temp_c + recommendation.amount > 100
        ):
            return _fallback_recommendation(brew_log)
        if (
            recommendation.direction == "decrease"
            and brew_log.water_temp_c - recommendation.amount <= 0
        ):
            return _fallback_recommendation(brew_log)

    if recommendation.action_type == "adjust_agitation":
        if (
            recommendation.direction == "decrease"
            and brew_log.agitation_level - recommendation.amount < 0
        ):
            return _fallback_recommendation(brew_log)
        if (
            recommendation.direction == "increase"
            and brew_log.agitation_level + recommendation.amount > 3
        ):
            return _fallback_recommendation(brew_log)

    if recommendation.action_type == "adjust_grind":
        if (
            brew_log.grind_setting_value is None
            or brew_log.grind_setting_unit_snapshot == "other"
        ):
            return _fallback_recommendation(brew_log)

    return recommendation


def build_recommendation(
    brew_log: BrewLogRead,
    evaluation: EvaluationRead
) -> RecommendationRead:

    if evaluation.confidence == 1:
        return RecommendationRead(
            target_log_id=brew_log.id,
            recommendation_mode="experiment",
            action_type="keep_same",
            direction="none",
            amount=0,
            unit="none",
            message="次回も同じ条件で抽出する",
            reason=(
                "評価の自信度が低いため、条件を変更せず"
                "もう一度評価して傾向を確認する"
            ),
        )

    has_defect = (
        evaluation.taste_defect != "none"
        or evaluation.aroma_defect
        or evaluation.aftertaste_defect
        or evaluation.texture_defect
    )

    if (
        evaluation.confidence == 3
        and evaluation.overall_score is not None
        and evaluation.overall_score <= 3
        and has_defect
    ):
        recommendation_mode = "strong"
    else:
        recommendation_mode = "normal"

    if evaluation.taste_defect == "thin":
        candidate = RecommendationRead(
            target_log_id=brew_log.id,
            recommendation_mode=recommendation_mode,
            action_type="adjust_grind",
            direction="finer",
            amount=1,
            unit=brew_log.grind_setting_unit_snapshot,
            message="次回は挽き目を1段階細かくする",
            reason=(
                "薄さが出ているため、挽き目を少し細かくして"
                "抽出を進める方向で試す"
            ),
        )
        return _apply_feasibility_guard(brew_log, candidate)

    if evaluation.taste_defect == "sour":
        candidate = RecommendationRead(
            target_log_id=brew_log.id,
            recommendation_mode=recommendation_mode,
            action_type="adjust_water_temp",
            direction="increase",
            amount=2,
            unit="celsius",
            message="次回は湯温を2℃上げる",
            reason=(
                "酸っぱさが出ているため、湯温を少し上げて"
                "抽出を進める方向で試す"
            ),
        )
        return _apply_feasibility_guard(brew_log, candidate)

    if evaluation.taste_defect == "bitter":
        candidate = RecommendationRead(
            target_log_id=brew_log.id,
            recommendation_mode=recommendation_mode,
            action_type="adjust_water_temp",
            direction="decrease",
            amount=2,
            unit="celsius",
            message="次回は湯温を2℃下げる",
            reason=(
                "苦味が出ているため、湯温を少し下げて"
                "抽出を弱める方向で試す"
            ),
        )
        return _apply_feasibility_guard(brew_log, candidate)

    if evaluation.taste_defect == "not_sweet":
        candidate = RecommendationRead(
            target_log_id=brew_log.id,
            recommendation_mode=recommendation_mode,
            action_type="adjust_grind",
            direction="finer",
            amount=1,
            unit=brew_log.grind_setting_unit_snapshot,
            message="次回は挽き目を1段階細かくする",
            reason=(
                "甘さが十分に感じられないため、挽き目を少し細かくして"
                "抽出を進める方向で試す"
            ),
        )
        return _apply_feasibility_guard(brew_log, candidate)

    if evaluation.aroma_defect:
        candidate = RecommendationRead(
            target_log_id=brew_log.id,
            recommendation_mode=recommendation_mode,
            action_type="adjust_water_temp",
            direction="increase",
            amount=2,
            unit="celsius",
            message="次回は湯温を2℃上げる",
            reason=(
                "香りに欠点があるため、湯温を少し上げて"
                "香りの出方が変化するか試す"
            ),
        )
        return _apply_feasibility_guard(brew_log, candidate)

    if evaluation.aftertaste_defect:
        candidate = RecommendationRead(
            target_log_id=brew_log.id,
            recommendation_mode=recommendation_mode,
            action_type="adjust_grind",
            direction="coarser",
            amount=1,
            unit=brew_log.grind_setting_unit_snapshot,
            message="次回は挽き目を1段階粗くする",
            reason=(
                "後味に欠点があるため、挽き目を少し粗くして"
                "抽出を弱める方向で試す"
            ),
        )
        return _apply_feasibility_guard(brew_log, candidate)

    if evaluation.texture_defect:
        candidate = RecommendationRead(
            target_log_id=brew_log.id,
            recommendation_mode=recommendation_mode,
            action_type="adjust_agitation",
            direction="decrease",
            amount=1,
            unit="level",
            message="次回は攪拌レベルを1下げる",
            reason=(
                "質感に欠点があるため、攪拌を少し弱めて"
                "抽出状態が変化するか試す"
            ),
        )
        return _apply_feasibility_guard(brew_log, candidate)

    if (
        evaluation.overall_score is not None
        and evaluation.overall_score >= 8
    ):
        return RecommendationRead(
            target_log_id=brew_log.id,
            recommendation_mode="normal",
            action_type="keep_same",
            direction="none",
            amount=0,
            unit="none",
            message="次回も同じ条件で抽出する",
            reason=(
                "評価が高く明確な欠点がないため、"
                "同じ条件で再現できるか確認する"
            ),
        )

    return RecommendationRead(
        target_log_id=brew_log.id,
        recommendation_mode="experiment",
        action_type="keep_same",
        direction="none",
        amount=0,
        unit="none",
        message="次回も同じ条件で抽出し、評価をもう一度確認する",
        reason=(
            "総合点は高くないが明確な欠点カテゴリが選択されていないため、"
            "変更する操作を特定できない"
        ),
    )
