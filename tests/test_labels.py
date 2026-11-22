"""Dashboard labels must follow the numbers, not praise them unconditionally."""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app import labels
from app.duckdb_engine import calculate_deterministic_bankability


def test_dscr_below_covenant_is_not_shown_as_passing():
    text, color = labels.dscr_label(1.07)
    assert "Below" in text and color != labels.GOOD
    assert labels.dscr_label(1.45)[1] == labels.GOOD
    assert labels.dscr_label(0.9)[1] == labels.BAD


def test_leverage_quick_ratio_and_margin_labels():
    assert labels.leverage_label(4.94)[1] == labels.BAD
    assert labels.leverage_label(2.0)[1] == labels.GOOD
    assert labels.quick_ratio_label(0.29)[0] == "Thin cash cushion"
    assert labels.margin_label(11.2)[0] == "Moderate margin"


def test_decline_is_never_badged_as_approved():
    text, badge, note = labels.outcome_label("DECLINE")
    assert "approv" not in text.lower() or "below" in text.lower()
    assert badge == "badge-danger"
    assert labels.outcome_label("APPROVE")[1] == "badge-success"


def test_rate_is_shown_as_percentage():
    assert labels.format_rate(0.0525) == "5.25%"
    assert labels.format_rate(5.15) == "5.15%"


def test_engine_drivers_match_the_numbers():
    res = calculate_deterministic_bankability("ecotex", 750_000)
    text = " ".join(res["drivers"])
    lev = res["net_debt_ebitda"]
    if lev > 2.5:
        assert "sopra la soglia" in text
    else:
        assert "entro la soglia" in text
    assert "+-" not in text
