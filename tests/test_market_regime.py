from scanner.market_regime import analyze_market_regime


def test_market_regime_scores_green_for_broad_uptrend(make_trending_history):
    spy = make_trending_history()
    qqq = make_trending_history(start=30, end=150)
    regime = analyze_market_regime(spy, qqq, {"AAA": spy, "BBB": qqq})

    assert regime.score >= 80
    assert regime.classification == "GREEN"
    assert regime.exposure == "AGGRESSIVE"
