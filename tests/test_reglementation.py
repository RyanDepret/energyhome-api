from datetime import date, datetime

import pytest

from app.core.reglementation import COEFFICIENTS_ELECTRICITE, coefficient_electricite, coefficient_en_vigueur


@pytest.mark.parametrize(
    "jour, attendu",
    [
        (date(2021, 7, 1), 2.3),
        (date(2025, 12, 31), 2.3),
        (date(2026, 1, 1), 1.9),
        (date(2026, 12, 31), 1.9),
        (date(2027, 1, 1), 1.7),
        (date(2035, 6, 1), 1.7),
    ],
)
def test_chaque_bascule(jour, attendu):
    assert coefficient_electricite(jour) == attendu


def test_accepte_un_datetime():
    assert coefficient_electricite(datetime(2026, 1, 1, 0, 0)) == 1.9


def test_refuse_avant_2021_07_01():
    with pytest.raises(ValueError):
        coefficient_electricite(date(2021, 6, 30))


def test_table_triee_et_sourcee():
    dates = [ligne.date_effet for ligne in COEFFICIENTS_ELECTRICITE]
    assert dates == sorted(dates)
    assert all(ligne.source for ligne in COEFFICIENTS_ELECTRICITE)
    assert "JORFTEXT000054747079" in coefficient_en_vigueur(date(2027, 1, 1)).source
