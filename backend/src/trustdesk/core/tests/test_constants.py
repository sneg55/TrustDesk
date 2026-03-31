from trustdesk.core.constants import (
    ALIGNMENT_GRADES,
    ERROR_IDS,
    REGIMES,
    SUPPORTED_PAIRS,
    TIERS,
    VERDICTS,
)


def test_supported_pairs() -> None:
    assert SUPPORTED_PAIRS == ("BTC/USD", "ETH/USD", "SOL/USD")


def test_regimes() -> None:
    assert set(REGIMES) == {"TRENDING_UP", "TRENDING_DOWN", "RANGING", "VOLATILE"}


def test_tiers() -> None:
    assert set(TIERS) == {"UNPROVEN", "ESTABLISHED", "TRUSTED"}


def test_verdicts() -> None:
    expected = {"APPROVED", "APPROVED_WITH_MODIFICATION", "APPROVED_HARD_ONLY", "REJECTED"}
    assert set(VERDICTS) == expected


def test_error_ids_are_unique() -> None:
    values = list(ERROR_IDS.values())
    assert len(values) == len(set(values))


def test_alignment_grades() -> None:
    assert set(ALIGNMENT_GRADES) == {"STRONG", "MODERATE", "WEAK", "NO_SIGNAL"}
