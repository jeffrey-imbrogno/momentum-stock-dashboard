from scanner.vcp import analyze_vcp, detect_contractions


def test_vcp_contraction_sequence_scores(make_vcp_history):
    history = make_vcp_history()

    contractions = detect_contractions(history, lookback=90)
    result = analyze_vcp(history)

    assert len(contractions) == 3
    assert contractions[0] > contractions[1] > contractions[2]
    assert result.contraction_count == 3
    assert result.score >= 45
