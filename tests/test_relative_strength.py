from scanner.relative_strength import (
    rank_rs_scores,
    score_from_relative_performance,
    weighted_relative_performance,
)


def test_relative_strength_outperformance_scores_above_neutral(make_trending_history):
    stock = make_trending_history(start=20, end=140)
    benchmark = make_trending_history(start=100, end=125)

    raw = weighted_relative_performance(stock, benchmark)

    assert raw is not None
    assert raw > 0
    assert score_from_relative_performance(raw) > 50


def test_rs_rank_score_reflects_universe_percentile():
    ranked = rank_rs_scores({"A": 0.30, "B": 0.10, "C": -0.05})

    assert ranked["A"] > ranked["B"] > ranked["C"]
    assert ranked["A"] >= 90
