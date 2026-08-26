"""Unit tests for the centralized financial-access policy boundary.

The policy (docs/architecture/financial_access_policy.md) restricts ALL
financial data to L0 CEO and L1 Director. These tests pin the truth
table of ``has_financial_access`` and the wiring between the shared
constant and the API dependency layer.
"""

import pytest

from app.api import deps
from app.models import OrgLevel, User
from app.utils.shared import FINANCIAL_LEVEL, LEVEL_RANK, has_financial_access


def _user_at(code: str | None) -> User:
    user = User(name="Persona")
    if code is not None:
        user.org_level = OrgLevel(code=code, name=f"Level {code}")
    return user


class TestFinancialAccessTruthTable:
    @pytest.mark.parametrize("code", ["L0", "L1"])
    def test_ceo_and_director_allowed(self, code):
        assert has_financial_access(_user_at(code)) is True

    @pytest.mark.parametrize("code", ["L2", "L3", "L4", "L5", "L6"])
    def test_all_other_levels_denied(self, code):
        assert has_financial_access(_user_at(code)) is False

    def test_user_without_level_denied(self):
        assert has_financial_access(_user_at(None)) is False

    def test_unknown_level_code_denied(self):
        assert has_financial_access(_user_at("LX")) is False


class TestPolicyWiring:
    def test_shared_constant_is_director_floor(self):
        assert FINANCIAL_LEVEL == "L1"

    def test_dependency_layer_uses_the_same_constant(self):
        assert deps.FinancialLevel == FINANCIAL_LEVEL

    def test_revenue_guard_is_an_alias_of_financial_policy(self):
        # Both factories must resolve to require_min_level(FINANCIAL_LEVEL).
        def required_rank(factory):
            checker = factory()
            (rank,) = {c.cell_contents for c in checker.__closure__}
            return rank

        assert (
            required_rank(deps.require_revenue_access)
            == required_rank(deps.require_financial_access)
            == LEVEL_RANK[FINANCIAL_LEVEL]
        )

    def test_financial_boundary_matches_executive_band(self):
        from app.utils.shared import ExecutiveLevels

        assert set(ExecutiveLevels) == {"L0", FINANCIAL_LEVEL}
