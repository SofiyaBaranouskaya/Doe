from decimal import Decimal
from typing import Literal, Dict, Any

def calculate_compound_interest(
    initial: Decimal,
    monthly_contribution: Decimal,
    annual_rate: Decimal,  # 0.07 = 7%
    years: int,
    cadence: Literal["monthly", "annually"] = "monthly",
) -> dict:

    if not (0 <= years <= 50):
        raise ValueError("Years must be between 0 and 50")

    compounds_per_year = 12 if cadence == "monthly" else 1

    r = annual_rate / compounds_per_year
    n = years * compounds_per_year

    # Вклад за один период
    pmt = (
        monthly_contribution
        if cadence == "monthly"
        else monthly_contribution * 12
    )

    # -----------------------------
    # Final calculation
    # -----------------------------

    if r == 0:
        future_value = initial + pmt * n
    else:
        future_value = (
            initial * (1 + r) ** n
            + pmt * (((1 + r) ** n - 1) / r)
        )

    total_contributed = initial + pmt * n
    interest_earned = future_value - total_contributed

    # -----------------------------
    # Data for chart
    # -----------------------------

    years_data = []
    contributions_over_time = []
    interest_over_time = []
    balance_over_time = []

    for y in range(years + 1):

        periods = y * compounds_per_year

        if r == 0:
            bal = initial + pmt * periods
        else:
            bal = (
                initial * (1 + r) ** periods
                + pmt * (((1 + r) ** periods - 1) / r)
            )

        contributions = initial + pmt * periods
        interest = bal - contributions

        # Arrays specifically for Chart.js
        years_data.append(y)
        contributions_over_time.append(
            float(round(contributions, 2))
        )
        interest_over_time.append(
            float(round(interest, 2))
        )

        # Keep your existing detailed data too
        balance_over_time.append({
            "year": y,
            "balance": float(round(bal, 2)),
            "contributions": float(round(contributions, 2)),
            "interest": float(round(interest, 2)),
        })

    # -----------------------------
    # Return
    # -----------------------------

    return {
        "future_value": float(round(future_value, 2)),
        "total_contributed": float(round(total_contributed, 2)),
        "interest_earned": float(round(interest_earned, 2)),

        # Data for Chart.js
        "years": years_data,
        "contributions_over_time": contributions_over_time,
        "interest_over_time": interest_over_time,

        # Detailed data, if needed later
        "balance_over_time": balance_over_time,

        "inputs": {
            "initial": float(initial),
            "monthly_contribution": float(monthly_contribution),
            "annual_rate": float(annual_rate * 100),
            "years": years,
            "cadence": cadence,
            "compounds_per_year": compounds_per_year,
        },
    }

from decimal import Decimal
from typing import Any, Dict, Literal

# Новое: фиксированный график размывания (можно изменить под свои предположения)
DILUTION_SCHEDULE = [
    {"round": "Seed", "dilution": Decimal("0.20")},
    {"round": "Series A", "dilution": Decimal("0.15")},
    {"round": "Series B", "dilution": Decimal("0.10")},
]

def calculate_angel_investment(
    investment: Decimal,
    val_cap: Decimal,
    interest_rate: Decimal,
    years_to_conversion: Decimal,
    pre_money: Decimal,
    round_size: Decimal,
    security_type: Literal["safe", "note", "priced_round"],
    average_time_horizon: Decimal,
    modest_exit_value: Decimal,  # <-- НОВЫЙ ПАРАМЕТР
) -> Dict[str, Any]:

    if investment < 0:
        raise ValueError("Investment cannot be negative.")

    if modest_exit_value <= 0:
        raise ValueError("Modest Exit Value must be greater than zero.")

    if average_time_horizon <= 0 or average_time_horizon > 20:
        raise ValueError("Time horizon must be between 1 and 20 years.")

    # Сценарии согласно слайду 6
    scenarios_data = [
        {"name": "Total loss",   "prob": Decimal("0.55"), "multiple": Decimal("0"),    "rounds": 0},
        {"name": "Soft Landing", "prob": Decimal("0.17"), "multiple": Decimal("0.3"),  "rounds": 2},
        {"name": "Modest Exit",  "prob": Decimal("0.20"), "multiple": Decimal("1"),    "rounds": 3},
        {"name": "Good Outcome", "prob": Decimal("0.06"), "multiple": Decimal("3"),    "rounds": 4},
        {"name": "Home Run",     "prob": Decimal("0.02"), "multiple": Decimal("12.5"), "rounds": 5},
    ]

    # ── OWNERSHIP AT CLOSE ─────────────────────────────────────
    if security_type == "safe":
        if val_cap <= 0:
            raise ValueError("Val Cap must be greater than zero.")
        ownership_at_close = investment / val_cap

    elif security_type == "note":
        if val_cap <= 0:
            raise ValueError("Val Cap must be greater than zero.")
        effective_investment = (
            investment
            * ((Decimal("1") + interest_rate) ** years_to_conversion)
        )
        ownership_at_close = effective_investment / val_cap

    elif security_type == "priced_round":
        if pre_money <= 0 or round_size <= 0:
            raise ValueError("Pre-money valuation and Round Size are required.")
        ownership_at_close = investment / (pre_money + round_size)

    else:
        raise ValueError("Invalid security type.")

    # ── ПРОХОД ПО СЦЕНАРИЯМ ────────────────────────────────────
    results = []
    total_expected_payout = Decimal("0")

    for scenario in scenarios_data:
        multiple = scenario["multiple"]
        probability = scenario["prob"]
        rounds = scenario["rounds"]

        # Ретеншн (остаточная доля) после `rounds` раундов размытия по 20%
        retention = (Decimal("1") - Decimal("0.20")) ** rounds

        # Доля на выходе для этого сценария
        ownership_at_exit_scenario = ownership_at_close * retention

        # Выходная стоимость = Modest Exit Value * множитель
        exit_valuation = modest_exit_value * multiple

        # Выплата инвестору
        payout = ownership_at_exit_scenario * exit_valuation

        # MOIC
        if investment > 0:
            moic = payout / investment
        else:
            moic = Decimal("0")

        # IRR
        if moic > 0:
            irr = moic ** (Decimal("1") / average_time_horizon) - Decimal("1")
        else:
            irr = Decimal("-1")

        results.append({
            "scenario": scenario["name"],
            "probability": float(probability * Decimal("100")),
            "multiple": float(multiple),
            "exit_valuation": float(round(exit_valuation, 2)),
            "ownership_at_exit": float(round(ownership_at_exit_scenario * Decimal("100"), 3)),
            "payout": float(round(payout, 2)),
            "moic": float(round(moic, 2)),
            "irr": float(round(irr * Decimal("100"), 2)),
        })

        total_expected_payout += payout * probability

    # ── ИТОГОВЫЕ ЗНАЧЕНИЯ ─────────────────────────────────────
    if investment > 0:
        avg_moic = total_expected_payout / investment
    else:
        avg_moic = Decimal("0")

    if avg_moic > 0:
        avg_irr = avg_moic ** (Decimal("1") / average_time_horizon) - Decimal("1")
    else:
        avg_irr = Decimal("-1")

    # Доля на выходе именно для сценария "Modest Exit" (3 раунда)
    retention_modest = (Decimal("1") - Decimal("0.20")) ** 3
    ownership_at_exit_modest = ownership_at_close * retention_modest

    return {
        "scenarios": results,
        "summary": {
            "avg_moic": float(round(avg_moic, 2)),
            "avg_irr": float(round(avg_irr * Decimal("100"), 2)),
            "total_expected_payout": float(round(total_expected_payout, 2)),
            "ownership_at_close": float(round(ownership_at_close * Decimal("100"), 3)),
            "ownership_at_exit_modest": float(round(ownership_at_exit_modest * Decimal("100"), 3)),
            "time_horizon": float(average_time_horizon),
        }
    }