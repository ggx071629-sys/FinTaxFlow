from typing import Literal
from pydantic import BaseModel, ConfigDict, Field

class CompanyInput(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)
    company_id: str

class BatchInput(CompanyInput):
    import_id: str
    confirmed: Literal[True]

class RetryInput(CompanyInput):
    failed_only: Literal[True]

class ReconciliationInput(CompanyInput):
    bank_import_id: str
    ledger_import_id: str
    period: str

class DeclarationInput(CompanyInput):
    filing_id: str
    period: str
    tax_type: Literal['VAT']
    confirmed: Literal[True]

class RecoveryInput(CompanyInput):
    confirmed: Literal[True]

class PortalInput(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)
    declaration_id: str
    sales_amount: str = Field(pattern=r'^\d{1,10}(\.\d{1,2})?$')
    tax_amount: str = Field(pattern=r'^\d{1,10}(\.\d{1,2})?$')
