import uuid
from datetime import date
from typing import Optional

from sqlmodel import Field

from app.models.base import TimestampMixin
from app.models.enums import ExpenseCategory, PaymentStatus, PaymentType


class Payment(TimestampMixin, table=True):
    __tablename__ = "payment"

    lease_id: uuid.UUID = Field(foreign_key="lease.id", index=True)

    payment_type: str = Field(default=PaymentType.rent.value, max_length=30)
    status: str = Field(default=PaymentStatus.pending.value, max_length=20, index=True)

    amount: float = Field(description="Amount due/expected in USD")
    amount_paid: float = Field(default=0.0)

    due_date: Optional[date] = Field(default=None, index=True)
    paid_date: Optional[date] = Field(default=None)

    method: Optional[str] = Field(default=None, max_length=50)
    reference: Optional[str] = Field(default=None, max_length=100)
    notes: Optional[str] = Field(default=None)


class Expense(TimestampMixin, table=True):
    __tablename__ = "expense"

    property_id: uuid.UUID = Field(foreign_key="property.id", index=True)
    unit_id: Optional[uuid.UUID] = Field(default=None, foreign_key="unit.id", index=True)

    category: str = Field(default=ExpenseCategory.maintenance.value, max_length=30)
    amount: float = Field()
    incurred_date: date = Field(index=True)

    vendor: Optional[str] = Field(default=None, max_length=200)
    description: Optional[str] = Field(default=None)
    receipt_url: Optional[str] = Field(default=None, max_length=500)
