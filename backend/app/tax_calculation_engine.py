
from typing import Dict, List, Optional, Tuple
from decimal import Decimal, ROUND_HALF_UP
import json
from datetime import datetime
from app.models import FilingStatus, IncomeType

class TaxCalculationEngine:
    """
    Comprehensive tax calculation engine supporting federal and state taxes,
    various income types, deductions, and credits.
    """

    def __init__(self, tax_year: int = 2023):
        self.tax_year = tax_year
        self.federal_brackets = self._get_federal_tax_brackets()
        self.standard_deductions = self._get_standard_deductions()
        self.tax_credits = self._get_tax_credits()
        self.state_tax_rates = self._get_state_tax_rates()

    def _get_federal_tax_brackets(self) -> Dict:
        """Federal tax brackets for 2023"""
        return {
            FilingStatus.SINGLE: [
                (11000, 0.10),
                (44725, 0.12),
                (95375, 0.22),
                (182050, 0.24),
                (231250, 0.32),
                (578125, 0.35),
                (float('inf'), 0.37)
            ],
            FilingStatus.MARRIED_FILING_JOINTLY: [
                (22000, 0.10),
                (89450, 0.12),
                (190750, 0.22),
                (364200, 0.24),
                (462500, 0.32),
                (693750, 0.35),
                (float('inf'), 0.37)
            ],
            FilingStatus.MARRIED_FILING_SEPARATELY: [
                (11000, 0.10),
                (44725, 0.12),
                (95375, 0.22),
                (182050, 0.24),
                (231250, 0.32),
                (346875, 0.35),
                (float('inf'), 0.37)
            ],
            FilingStatus.HEAD_OF_HOUSEHOLD: [
                (15700, 0.10),
                (59850, 0.12),
                (95350, 0.22),
                (182050, 0.24),
                (231250, 0.32),
                (578100, 0.35),
                (float('inf'), 0.37)
            ]
        }

    def _get_standard_deductions(self) -> Dict:
        """Standard deduction amounts for 2023"""
        return {
            FilingStatus.SINGLE: 13850,
            FilingStatus.MARRIED_FILING_JOINTLY: 27700,
            FilingStatus.MARRIED_FILING_SEPARATELY: 13850,
            FilingStatus.HEAD_OF_HOUSEHOLD: 20800,
            FilingStatus.QUALIFYING_WIDOW: 27700
        }

    def _get_tax_credits(self) -> Dict:
        """Tax credit information"""
        return {
            'child_tax_credit': {
                'max_amount': 2000,
                'refundable_portion': 1600,
                'phase_out_start': {
                    FilingStatus.SINGLE: 200000,
                    FilingStatus.MARRIED_FILING_JOINTLY: 400000,
                    FilingStatus.MARRIED_FILING_SEPARATELY: 200000,
                    FilingStatus.HEAD_OF_HOUSEHOLD: 200000
                }
            },
            'earned_income_credit': {
                'max_amounts': {
                    0: 600,  # No children
                    1: 3995,  # 1 child
                    2: 6604,  # 2 children
                    3: 7430   # 3+ children
                }
            },
            'american_opportunity_credit': {
                'max_amount': 2500,
                'refundable_portion': 1000
            },
            'child_and_dependent_care_credit': {
                'max_amount': 1050,
                'max_expenses': 3000
            }
        }

    def _get_state_tax_rates(self) -> Dict:
        """State tax rates and information"""
        return {
            'CA': {'rate': 0.13, 'standard_deduction': 5202},
            'NY': {'rate': 0.109, 'standard_deduction': 8000},
            'TX': {'rate': 0.0, 'standard_deduction': 0},  # No state income tax
            'FL': {'rate': 0.0, 'standard_deduction': 0},  # No state income tax
            'WA': {'rate': 0.0, 'standard_deduction': 0},  # No state income tax
            'OR': {'rate': 0.099, 'standard_deduction': 2350},
            'IL': {'rate': 0.0495, 'standard_deduction': 2425},
            'PA': {'rate': 0.0307, 'standard_deduction': 0},
            'OH': {'rate': 0.0399, 'standard_deduction': 0},
            'GA': {'rate': 0.0575, 'standard_deduction': 4600}
        }

    def calculate_federal_tax(self, taxable_income: float, filing_status: FilingStatus) -> Dict:
        """Calculate federal income tax"""
        brackets = self.federal_brackets.get(filing_status, self.federal_brackets[FilingStatus.SINGLE])

        tax_owed = 0.0
        previous_bracket = 0.0

        for bracket_limit, rate in brackets:
            if taxable_income <= previous_bracket:
                break

            taxable_in_bracket = min(taxable_income, bracket_limit) - previous_bracket
            tax_owed += taxable_in_bracket * rate
            previous_bracket = bracket_limit

            if taxable_income <= bracket_limit:
                break

        return {
            'tax_owed': round(tax_owed, 2),
            'effective_rate': round((tax_owed / taxable_income * 100) if taxable_income > 0 else 0, 2),
            'marginal_rate': rate * 100
        }

    def calculate_state_tax(self, taxable_income: float, state: str, filing_status: FilingStatus) -> Dict:
        """Calculate state income tax"""
        if state not in self.state_tax_rates:
            return {'tax_owed': 0.0, 'rate': 0.0, 'deduction': 0.0}

        state_info = self.state_tax_rates[state]
        state_deduction = state_info['standard_deduction']
        state_taxable_income = max(0, taxable_income - state_deduction)
        state_tax = state_taxable_income * state_info['rate']

        return {
            'tax_owed': round(state_tax, 2),
            'rate': state_info['rate'] * 100,
            'deduction': state_deduction,
            'taxable_income': state_taxable_income
        }

    def calculate_self_employment_tax(self, self_employment_income: float) -> Dict:
        """Calculate self-employment tax (Social Security and Medicare)"""
        if self_employment_income <= 0:
            return {'total_tax': 0.0, 'social_security': 0.0, 'medicare': 0.0}

        # 92.35% of self-employment income is subject to SE tax
        se_income = self_employment_income * 0.9235

        # Social Security tax (12.4% up to wage base)
        ss_wage_base = 160200  # 2023 limit
        ss_taxable = min(se_income, ss_wage_base)
        ss_tax = ss_taxable * 0.124

        # Medicare tax (2.9% on all income)
        medicare_tax = se_income * 0.029

        # Additional Medicare tax (0.9% on income over threshold)
        medicare_threshold = 200000
        additional_medicare = max(0, se_income - medicare_threshold) * 0.009

        total_tax = ss_tax + medicare_tax + additional_medicare

        return {
            'total_tax': round(total_tax, 2),
            'social_security': round(ss_tax, 2),
            'medicare': round(medicare_tax + additional_medicare, 2),
            'deductible_portion': round(total_tax * 0.5, 2)  # Half is deductible
        }

    def calculate_child_tax_credit(self, num_children: int, agi: float, filing_status: FilingStatus) -> Dict:
        """Calculate Child Tax Credit"""
        if num_children == 0:
            return {'credit': 0.0, 'refundable': 0.0}

        credit_info = self.tax_credits['child_tax_credit']
        max_credit = credit_info['max_amount'] * num_children
        phase_out_start = credit_info['phase_out_start'][filing_status]

        # Phase out calculation
        if agi > phase_out_start:
            phase_out_amount = ((agi - phase_out_start) // 1000) * 50
            credit = max(0, max_credit - phase_out_amount)
        else:
            credit = max_credit

        refundable_portion = min(credit, credit_info['refundable_portion'] * num_children)

        return {
            'credit': credit,
            'refundable': refundable_portion,
            'non_refundable': credit - refundable_portion
        }

    def calculate_earned_income_credit(self, earned_income: float, agi: float, num_children: int, filing_status: FilingStatus) -> float:
        """Calculate Earned Income Tax Credit"""
        eic_info = self.tax_credits['earned_income_credit']
        max_credit = eic_info['max_amounts'].get(min(num_children, 3), 0)

        # Simplified EIC calculation (actual calculation is more complex)
        if filing_status == FilingStatus.MARRIED_FILING_JOINTLY:
            income_limit = 25220 + (num_children * 5000)
        else:
            income_limit = 17640 + (num_children * 4000)

        if agi > income_limit:
            return 0.0

        # Phase-in and phase-out calculation (simplified)
        if earned_income < 10000:
            credit = earned_income * 0.34  # Simplified rate
        else:
            credit = max_credit * (1 - ((agi - 10000) / income_limit))

        return max(0, min(credit, max_credit))

    def calculate_business_tax(self, business_income: float, business_expenses: float, business_type: str) -> Dict:
        """Calculate business tax based on business type"""
        net_income = business_income - business_expenses

        if business_type == 'sole_proprietorship':
            # Schedule C - reported on personal return
            se_tax = self.calculate_self_employment_tax(net_income)
            return {
                'net_income': net_income,
                'self_employment_tax': se_tax,
                'schedule_c_income': net_income
            }

        elif business_type == 'c_corp':
            # Corporate tax rates (simplified)
            if net_income <= 50000:
                corp_tax = net_income * 0.15
            elif net_income <= 75000:
                corp_tax = 7500 + (net_income - 50000) * 0.25
            else:
                corp_tax = net_income * 0.21  # Flat 21% for 2023

            return {
                'net_income': net_income,
                'corporate_tax': corp_tax,
                'effective_rate': (corp_tax / net_income * 100) if net_income > 0 else 0
            }

        elif business_type == 's_corp':
            # S-Corp passes through to personal return
            return {
                'net_income': net_income,
                'pass_through_income': net_income,
                'self_employment_tax': 0  # S-Corp owners don't pay SE tax on distributions
            }

        return {'net_income': net_income}

    def calculate_comprehensive_tax(self, tax_data: Dict) -> Dict:
        """
        Comprehensive tax calculation including all income types, deductions, and credits
        """
        # Extract data
        filing_status = FilingStatus(tax_data.get('filing_status', 'single'))
        state = tax_data.get('state', 'CA')

        # Income calculations
        w2_income = sum([income.get('amount', 0) for income in tax_data.get('w2_income', [])])
        self_employment_income = sum([income.get('amount', 0) for income in tax_data.get('self_employment_income', [])])
        interest_income = sum([income.get('amount', 0) for income in tax_data.get('interest_income', [])])
        dividend_income = sum([income.get('amount', 0) for income in tax_data.get('dividend_income', [])])
        capital_gains = sum([income.get('amount', 0) for income in tax_data.get('capital_gains', [])])
        business_income = tax_data.get('business_income', 0)
        business_expenses = tax_data.get('business_expenses', 0)

        # Total income
        total_income = (w2_income + self_employment_income + interest_income + 
                       dividend_income + capital_gains + business_income)

        # Self-employment tax
        se_tax_calc = self.calculate_self_employment_tax(self_employment_income)
        se_tax_deduction = se_tax_calc['deductible_portion']

        # Adjusted Gross Income
        agi = total_income - se_tax_deduction

        # Deductions
        itemized_deductions = sum([ded.get('amount', 0) for ded in tax_data.get('itemized_deductions', [])])
        standard_deduction = self.standard_deductions[filing_status]
        total_deductions = max(itemized_deductions, standard_deduction)

        # Taxable income
        taxable_income = max(0, agi - total_deductions)

        # Federal tax
        federal_tax_calc = self.calculate_federal_tax(taxable_income, filing_status)
        federal_tax = federal_tax_calc['tax_owed']

        # State tax
        state_tax_calc = self.calculate_state_tax(taxable_income, state, filing_status)
        state_tax = state_tax_calc['tax_owed']

        # Credits
        num_children = tax_data.get('num_children', 0)
        child_tax_credit = self.calculate_child_tax_credit(num_children, agi, filing_status)
        eic = self.calculate_earned_income_credit(w2_income + self_employment_income, agi, num_children, filing_status)

        total_credits = child_tax_credit['credit'] + eic

        # Final calculations
        total_tax_before_credits = federal_tax + state_tax + se_tax_calc['total_tax']
        total_tax_after_credits = max(0, total_tax_before_credits - total_credits)

        # Withholdings and payments
        federal_withholding = sum([income.get('federal_withholding', 0) for income in tax_data.get('w2_income', [])])
        state_withholding = sum([income.get('state_withholding', 0) for income in tax_data.get('w2_income', [])])
        estimated_payments = tax_data.get('estimated_payments', 0)

        total_payments = federal_withholding + state_withholding + estimated_payments

        # Refund or amount owed
        if total_payments > total_tax_after_credits:
            refund = total_payments - total_tax_after_credits
            amount_owed = 0
        else:
            refund = 0
            amount_owed = total_tax_after_credits - total_payments

        return {
            'total_income': round(total_income, 2),
            'adjusted_gross_income': round(agi, 2),
            'taxable_income': round(taxable_income, 2),
            'standard_deduction': standard_deduction,
            'itemized_deductions': round(itemized_deductions, 2),
            'total_deductions': round(total_deductions, 2),
            'federal_tax': round(federal_tax, 2),
            'state_tax': round(state_tax, 2),
            'self_employment_tax': round(se_tax_calc['total_tax'], 2),
            'total_tax_before_credits': round(total_tax_before_credits, 2),
            'child_tax_credit': round(child_tax_credit['credit'], 2),
            'earned_income_credit': round(eic, 2),
            'total_credits': round(total_credits, 2),
            'total_tax_after_credits': round(total_tax_after_credits, 2),
            'total_payments': round(total_payments, 2),
            'refund_amount': round(refund, 2),
            'amount_owed': round(amount_owed, 2),
            'effective_tax_rate': round((total_tax_after_credits / agi * 100) if agi > 0 else 0, 2),
            'marginal_tax_rate': federal_tax_calc.get('marginal_rate', 0)
        }

# Utility functions for tax calculations
class TaxUtilities:
    @staticmethod
    def calculate_quarterly_estimated_payments(annual_tax_owed: float, withholdings: float) -> List[float]:
        """Calculate quarterly estimated tax payments"""
        remaining_tax = max(0, annual_tax_owed - withholdings)
        quarterly_payment = remaining_tax / 4
        return [quarterly_payment] * 4

    @staticmethod
    def calculate_penalties(amount_owed: float, days_late: int) -> float:
        """Calculate penalties for late payment"""
        if days_late <= 0:
            return 0.0

        # Simplified penalty calculation (0.5% per month or part of month)
        months_late = (days_late + 29) // 30  # Round up to nearest month
        penalty_rate = 0.005  # 0.5% per month
        max_penalty_rate = 0.25  # Maximum 25%

        penalty = min(amount_owed * penalty_rate * months_late, amount_owed * max_penalty_rate)
        return round(penalty, 2)

    @staticmethod
    def calculate_interest(amount_owed: float, days_late: int, annual_rate: float = 0.08) -> float:
        """Calculate interest on unpaid taxes"""
        if days_late <= 0:
            return 0.0

        daily_rate = annual_rate / 365
        interest = amount_owed * daily_rate * days_late
        return round(interest, 2)
