"""Financial calculations for lease-break buyout options."""

from __future__ import annotations

from pydantic import BaseModel


class BuyoutCalculation(BaseModel):
    buyout_multiple: float
    monthly_rent: float
    last_months_rent_held: float
    current_month_rent: float
    move_out_date: str

    buyout_amount_gross: float
    last_month_credit: float
    cash_due_at_signing: float
    total_cash_collected: float

    security_deposit_held: float


class LeaseBreakCalculator:
    @staticmethod
    def calculate_buyout_option(
        monthly_rent: float,
        last_months_rent_held: float,
        security_deposit: float,
        buyout_multiple: float,
        move_out_date: str,
    ) -> BuyoutCalculation:
        """Buyout amounts with the last month's rent credited against the buyout.

        Example: rent $1,450, last-month held $1,450, 3x buyout →
          gross $4,350, credit -$1,450, cash due $2,900,
          total collected = current month $1,450 + $2,900 = $4,350.
        """
        buyout_gross = round(monthly_rent * buyout_multiple, 2)
        current_month_rent = monthly_rent
        # Credit cannot exceed the gross buyout.
        last_month_credit = round(min(last_months_rent_held, buyout_gross), 2)
        cash_due_at_signing = round(buyout_gross - last_month_credit, 2)
        total_collected = round(current_month_rent + cash_due_at_signing, 2)

        return BuyoutCalculation(
            buyout_multiple=buyout_multiple,
            monthly_rent=monthly_rent,
            last_months_rent_held=last_months_rent_held,
            current_month_rent=current_month_rent,
            move_out_date=move_out_date,
            buyout_amount_gross=buyout_gross,
            last_month_credit=last_month_credit,
            cash_due_at_signing=cash_due_at_signing,
            total_cash_collected=total_collected,
            security_deposit_held=security_deposit,
        )

    @staticmethod
    def generate_option_title(option_number: int, option_type: str, tenant_names: list[str]) -> str:
        if option_type == "buyout":
            if len(tenant_names) > 1:
                return f"Option {option_number}: Joint Buyout (All Tenants)"
            name = tenant_names[0] if tenant_names else "Tenant"
            return f"Option {option_number}: {name} Buyout"
        if option_type == "stay_on_hook":
            return f"Option {option_number}: No Buyout (Remain Liable)"
        if option_type == "mutual_termination":
            return f"Option {option_number}: Mutual Termination"
        return f"Option {option_number}"
