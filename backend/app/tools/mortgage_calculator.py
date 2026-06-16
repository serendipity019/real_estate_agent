"""
tools/mortgage_calculator.py — Python mortgage calculation tool.

Exposed as a LangChain @tool so the LangGraph agent can call it
via function calling whenever the user asks about loan payments.
"""
from langchain_core.tools import tool


@tool
def calculate_mortgage(
    loan_amount: float,
    annual_interest_rate: float,
    loan_term_years: int,
    down_payment: float = 0.0,
) -> dict:
    """
    Calculate mortgage / home-loan monthly payments and full amortisation summary.

    Use this tool whenever the user asks about:
    - Monthly mortgage or loan payments
    - How much a property loan will cost in total
    - Affordability of a property at a given price
    - The effect of different interest rates or loan durations

    Args:
        loan_amount: Total property price OR loan principal in euros (€).
        annual_interest_rate: Annual interest rate as a percentage (e.g. 3.5 for 3.5%).
        loan_term_years: Loan duration in years (e.g. 20 or 30).
        down_payment: Down-payment amount in euros. Defaults to 0.

    Returns:
        A dict with monthly_payment, total_payment, total_interest, and a
        short amortisation breakdown by 5-year intervals.
    """
    principal = loan_amount - down_payment
    if principal <= 0:
        return {"error": "Down payment exceeds or equals the loan amount."}
    if annual_interest_rate <= 0:
        return {"error": "Interest rate must be greater than 0."}
    if loan_term_years <= 0:
        return {"error": "Loan term must be at least 1 year."}

    monthly_rate = (annual_interest_rate / 100) / 12
    n_payments = loan_term_years * 12

    # Standard annuity formula
    monthly_payment = principal * (monthly_rate * (1 + monthly_rate) ** n_payments) / (
        (1 + monthly_rate) ** n_payments - 1
    )

    total_payment = monthly_payment * n_payments
    total_interest = total_payment - principal

    # Amortisation snapshot — balance remaining at every 5-year mark
    balance = principal
    snapshots = []
    for month in range(1, n_payments + 1):
        interest_portion = balance * monthly_rate
        principal_portion = monthly_payment - interest_portion
        balance -= principal_portion

        if month % 60 == 0:  # every 5 years
            year = month // 12
            snapshots.append(
                {
                    "year": year,
                    "remaining_balance_eur": round(max(balance, 0), 2),
                    "paid_so_far_eur": round(monthly_payment * month, 2),
                }
            )

    return {
        "loan_principal_eur": round(principal, 2),
        "down_payment_eur": round(down_payment, 2),
        "annual_interest_rate_pct": annual_interest_rate,
        "loan_term_years": loan_term_years,
        "monthly_payment_eur": round(monthly_payment, 2),
        "total_payment_eur": round(total_payment, 2),
        "total_interest_eur": round(total_interest, 2),
        "interest_to_principal_ratio": round(total_interest / principal, 4),
        "amortisation_snapshots": snapshots,
    }
