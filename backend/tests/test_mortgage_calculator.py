"""
tests/test_mortgage_calculator.py — Unit tests for the mortgage calculator tool.
"""
import pytest
from app.tools.mortgage_calculator import calculate_mortgage


def test_standard_mortgage():
    result = calculate_mortgage.invoke({
        "loan_amount": 200_000,
        "annual_interest_rate": 3.5,
        "loan_term_years": 20,
    })
    assert "monthly_payment_eur" in result
    assert result["monthly_payment_eur"] > 0
    assert result["loan_principal_eur"] == 200_000.0
    assert result["loan_term_years"] == 20


def test_mortgage_with_down_payment():
    result = calculate_mortgage.invoke({
        "loan_amount": 300_000,
        "annual_interest_rate": 4.0,
        "loan_term_years": 25,
        "down_payment": 60_000,
    })
    assert result["loan_principal_eur"] == 240_000.0
    assert result["down_payment_eur"] == 60_000.0
    assert result["monthly_payment_eur"] > 0


def test_total_payment_greater_than_principal():
    result = calculate_mortgage.invoke({
        "loan_amount": 150_000,
        "annual_interest_rate": 5.0,
        "loan_term_years": 30,
    })
    assert result["total_payment_eur"] > result["loan_principal_eur"]
    assert result["total_interest_eur"] > 0


def test_amortisation_snapshots_present():
    result = calculate_mortgage.invoke({
        "loan_amount": 200_000,
        "annual_interest_rate": 3.5,
        "loan_term_years": 20,
    })
    snapshots = result["amortisation_snapshots"]
    # 20 years → snapshots at year 5, 10, 15, 20
    assert len(snapshots) == 4
    assert snapshots[0]["year"] == 5
    assert snapshots[-1]["year"] == 20


def test_balance_decreases_over_time():
    result = calculate_mortgage.invoke({
        "loan_amount": 200_000,
        "annual_interest_rate": 3.5,
        "loan_term_years": 20,
    })
    balances = [s["remaining_balance_eur"] for s in result["amortisation_snapshots"]]
    assert balances == sorted(balances, reverse=True)  # strictly decreasing


def test_down_payment_exceeds_loan_returns_error():
    result = calculate_mortgage.invoke({
        "loan_amount": 100_000,
        "annual_interest_rate": 3.5,
        "loan_term_years": 20,
        "down_payment": 150_000,
    })
    assert "error" in result


def test_zero_interest_rate_returns_error():
    result = calculate_mortgage.invoke({
        "loan_amount": 200_000,
        "annual_interest_rate": 0,
        "loan_term_years": 20,
    })
    assert "error" in result


def test_monthly_payment_math():
    """Cross-check: manual annuity formula for a known case."""
    result = calculate_mortgage.invoke({
        "loan_amount": 100_000,
        "annual_interest_rate": 6.0,
        "loan_term_years": 10,
    })
    # Known result: ~1,110.21 €/month
    assert abs(result["monthly_payment_eur"] - 1110.21) < 1.0
