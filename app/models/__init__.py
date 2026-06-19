"""SQLModel table models.

Importing this package registers every table on ``SQLModel.metadata`` so that
``create_all`` and Alembic autogenerate can see them.
"""

from app.models.email_approval import EmailApproval
from app.models.finance import Expense, Payment
from app.models.hoa import HOA, HOADocument
from app.models.jurisdiction import Jurisdiction
from app.models.lease import Lease, LeaseTenant
from app.models.lease_document import LeaseDocument
from app.models.lease_break import (
    LeaseBreakDocument,
    LeaseBreakOption,
    LeaseBreakRequest,
)
from app.models.organization import ManagementCompany, Owner
from app.models.property import Property, PropertyPhoto
from app.models.template import LeaseTemplate
from app.models.tenant import Tenant

__all__ = [
    "Jurisdiction",
    "Owner",
    "ManagementCompany",
    "Property",
    "PropertyPhoto",
    "Tenant",
    "Lease",
    "LeaseTenant",
    "LeaseDocument",
    "Payment",
    "Expense",
    "LeaseTemplate",
    "LeaseBreakRequest",
    "LeaseBreakOption",
    "LeaseBreakDocument",
    "EmailApproval",
    "HOA",
    "HOADocument",
]
