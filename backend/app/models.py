
from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, Text, ForeignKey, Enum
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime
import enum

Base = declarative_base()

class FilingStatus(enum.Enum):
    SINGLE = "single"
    MARRIED_FILING_JOINTLY = "married_filing_jointly"
    MARRIED_FILING_SEPARATELY = "married_filing_separately"
    HEAD_OF_HOUSEHOLD = "head_of_household"
    QUALIFYING_WIDOW = "qualifying_widow"

class BusinessType(enum.Enum):
    SOLE_PROPRIETORSHIP = "sole_proprietorship"
    PARTNERSHIP = "partnership"
    S_CORP = "s_corp"
    C_CORP = "c_corp"
    LLC = "llc"

class IncomeType(enum.Enum):
    W2_WAGES = "w2_wages"
    SELF_EMPLOYMENT = "self_employment"
    INTEREST = "interest"
    DIVIDENDS = "dividends"
    CAPITAL_GAINS = "capital_gains"
    RENTAL = "rental"
    BUSINESS = "business"
    RETIREMENT = "retirement"
    UNEMPLOYMENT = "unemployment"
    SOCIAL_SECURITY = "social_security"

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    first_name = Column(String)
    last_name = Column(String)
    ssn = Column(String)  # Encrypted in production
    date_of_birth = Column(DateTime)
    phone = Column(String)
    address = Column(Text)
    city = Column(String)
    state = Column(String)
    zip_code = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    tax_returns = relationship("TaxReturn", back_populates="user")
    businesses = relationship("Business", back_populates="owner")
    dependents = relationship("Dependent", back_populates="user")

class Dependent(Base):
    __tablename__ = "dependents"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    first_name = Column(String)
    last_name = Column(String)
    ssn = Column(String)
    date_of_birth = Column(DateTime)
    relationship = Column(String)
    months_lived_with_taxpayer = Column(Integer)
    is_student = Column(Boolean, default=False)
    is_disabled = Column(Boolean, default=False)

    user = relationship("User", back_populates="dependents")

class Business(Base):
    __tablename__ = "businesses"

    id = Column(Integer, primary_key=True, index=True)
    owner_id = Column(Integer, ForeignKey("users.id"))
    business_name = Column(String)
    ein = Column(String)
    business_type = Column(Enum(BusinessType))
    industry_code = Column(String)
    business_address = Column(Text)
    start_date = Column(DateTime)

    owner = relationship("User", back_populates="businesses")
    income_records = relationship("BusinessIncome", back_populates="business")
    expense_records = relationship("BusinessExpense", back_populates="business")

class TaxReturn(Base):
    __tablename__ = "tax_returns"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    tax_year = Column(Integer)
    filing_status = Column(Enum(FilingStatus))
    is_joint_return = Column(Boolean, default=False)
    spouse_ssn = Column(String, nullable=True)
    spouse_first_name = Column(String, nullable=True)
    spouse_last_name = Column(String, nullable=True)

    # Tax calculations
    total_income = Column(Float, default=0.0)
    adjusted_gross_income = Column(Float, default=0.0)
    taxable_income = Column(Float, default=0.0)
    federal_tax_owed = Column(Float, default=0.0)
    state_tax_owed = Column(Float, default=0.0)
    total_tax_owed = Column(Float, default=0.0)
    total_payments = Column(Float, default=0.0)
    refund_amount = Column(Float, default=0.0)
    amount_owed = Column(Float, default=0.0)

    # Status tracking
    is_filed = Column(Boolean, default=False)
    is_accepted = Column(Boolean, default=False)
    filed_date = Column(DateTime, nullable=True)
    accepted_date = Column(DateTime, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="tax_returns")
    income_records = relationship("IncomeRecord", back_populates="tax_return")
    deduction_records = relationship("DeductionRecord", back_populates="tax_return")
    credit_records = relationship("CreditRecord", back_populates="tax_return")
    payment_records = relationship("PaymentRecord", back_populates="tax_return")

class IncomeRecord(Base):
    __tablename__ = "income_records"

    id = Column(Integer, primary_key=True, index=True)
    tax_return_id = Column(Integer, ForeignKey("tax_returns.id"))
    income_type = Column(Enum(IncomeType))
    amount = Column(Float)
    payer_name = Column(String, nullable=True)
    payer_ein = Column(String, nullable=True)
    federal_withholding = Column(Float, default=0.0)
    state_withholding = Column(Float, default=0.0)

    # W2 specific fields
    wages_tips = Column(Float, nullable=True)
    social_security_wages = Column(Float, nullable=True)
    medicare_wages = Column(Float, nullable=True)

    # 1099 specific fields
    nonemployee_compensation = Column(Float, nullable=True)

    tax_return = relationship("TaxReturn", back_populates="income_records")

class DeductionRecord(Base):
    __tablename__ = "deduction_records"

    id = Column(Integer, primary_key=True, index=True)
    tax_return_id = Column(Integer, ForeignKey("tax_returns.id"))
    deduction_type = Column(String)
    amount = Column(Float)
    description = Column(Text, nullable=True)

    tax_return = relationship("TaxReturn", back_populates="deduction_records")

class CreditRecord(Base):
    __tablename__ = "credit_records"

    id = Column(Integer, primary_key=True, index=True)
    tax_return_id = Column(Integer, ForeignKey("tax_returns.id"))
    credit_type = Column(String)
    amount = Column(Float)
    qualifying_children = Column(Integer, default=0)

    tax_return = relationship("TaxReturn", back_populates="credit_records")

class BusinessIncome(Base):
    __tablename__ = "business_income"

    id = Column(Integer, primary_key=True, index=True)
    business_id = Column(Integer, ForeignKey("businesses.id"))
    income_type = Column(String)
    amount = Column(Float)
    date_received = Column(DateTime)
    description = Column(Text)

    business = relationship("Business", back_populates="income_records")

class BusinessExpense(Base):
    __tablename__ = "business_expenses"

    id = Column(Integer, primary_key=True, index=True)
    business_id = Column(Integer, ForeignKey("businesses.id"))
    expense_type = Column(String)
    amount = Column(Float)
    date_incurred = Column(DateTime)
    description = Column(Text)
    receipt_url = Column(String, nullable=True)

    business = relationship("Business", back_populates="expense_records")

class PaymentRecord(Base):
    __tablename__ = "payment_records"

    id = Column(Integer, primary_key=True, index=True)
    tax_return_id = Column(Integer, ForeignKey("tax_returns.id"))
    payment_type = Column(String)  # bank_transfer, credit_card, check
    amount = Column(Float)
    payment_date = Column(DateTime)
    transaction_id = Column(String)
    status = Column(String)  # pending, completed, failed

    tax_return = relationship("TaxReturn", back_populates="payment_records")

class StateRequirement(Base):
    __tablename__ = "state_requirements"

    id = Column(Integer, primary_key=True, index=True)
    state_code = Column(String, unique=True)
    state_name = Column(String)
    has_state_income_tax = Column(Boolean, default=True)
    standard_deduction_single = Column(Float)
    standard_deduction_married = Column(Float)
    tax_brackets = Column(Text)  # JSON string
    filing_deadline = Column(String)
    extension_deadline = Column(String)
    e_file_available = Column(Boolean, default=True)

class TaxForm(Base):
    __tablename__ = "tax_forms"

    id = Column(Integer, primary_key=True, index=True)
    form_name = Column(String)
    form_title = Column(String)
    tax_year = Column(Integer)
    form_fields = Column(Text)  # JSON string of form fields
    instructions = Column(Text)
    is_federal = Column(Boolean, default=True)
    state_code = Column(String, nullable=True)
