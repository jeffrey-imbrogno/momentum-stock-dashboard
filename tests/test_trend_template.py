from scanner.trend_template import evaluate_trend_template


def test_trend_template_passes_strong_uptrend(make_trending_history):
    result = evaluate_trend_template(make_trending_history())

    assert result.score == 8
    assert result.label == "8/8"
    assert result.critical_failure is False


def test_trend_template_detects_failure(make_downtrend_history):
    result = evaluate_trend_template(make_downtrend_history())

    assert result.score < 5
    assert result.critical_failure is True
