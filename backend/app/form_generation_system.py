
from typing import Dict, List, Optional, Any
import json
from datetime import datetime
from decimal import Decimal
from app.models import FilingStatus, TaxReturn, User, IncomeRecord, DeductionRecord

class TaxFormGenerator:
    """
    Comprehensive tax form generation system supporting IRS forms and state forms
    """

    def __init__(self):
        self.form_templates = self._load_form_templates()
        self.state_forms = self._load_state_form_templates()

    def _load_form_templates(self) -> Dict:
        """Load federal tax form templates"""
        return {
            '1040': {
                'title': 'U.S. Individual Income Tax Return',
                'fields': {
                    'filing_status': {'line': 1, 'type': 'checkbox', 'required': True},
                    'first_name': {'line': 2, 'type': 'text', 'required': True},
                    'last_name': {'line': 2, 'type': 'text', 'required': True},
                    'ssn': {'line': 3, 'type': 'ssn', 'required': True},
                    'spouse_first_name': {'line': 4, 'type': 'text', 'required': False},
                    'spouse_last_name': {'line': 4, 'type': 'text', 'required': False},
                    'spouse_ssn': {'line': 5, 'type': 'ssn', 'required': False},
                    'address': {'line': 6, 'type': 'text', 'required': True},
                    'city_state_zip': {'line': 7, 'type': 'text', 'required': True},
                    'wages_salaries': {'line': '1a', 'type': 'currency', 'required': True},
                    'tax_exempt_interest': {'line': '2a', 'type': 'currency', 'required': False},
                    'taxable_interest': {'line': '2b', 'type': 'currency', 'required': False},
                    'qualified_dividends': {'line': '3a', 'type': 'currency', 'required': False},
                    'ordinary_dividends': {'line': '3b', 'type': 'currency', 'required': False},
                    'ira_distributions': {'line': '4a', 'type': 'currency', 'required': False},
                    'taxable_ira': {'line': '4b', 'type': 'currency', 'required': False},
                    'pensions_annuities': {'line': '5a', 'type': 'currency', 'required': False},
                    'taxable_pensions': {'line': '5b', 'type': 'currency', 'required': False},
                    'social_security': {'line': '6a', 'type': 'currency', 'required': False},
                    'taxable_social_security': {'line': '6b', 'type': 'currency', 'required': False},
                    'capital_gain_loss': {'line': '7', 'type': 'currency', 'required': False},
                    'other_income': {'line': '8', 'type': 'currency', 'required': False},
                    'total_income': {'line': '9', 'type': 'currency', 'calculated': True},
                    'adjustments_to_income': {'line': '10', 'type': 'currency', 'required': False},
                    'adjusted_gross_income': {'line': '11', 'type': 'currency', 'calculated': True},
                    'standard_deduction': {'line': '12a', 'type': 'currency', 'calculated': True},
                    'itemized_deductions': {'line': '12b', 'type': 'currency', 'required': False},
                    'qualified_business_income': {'line': '13', 'type': 'currency', 'required': False},
                    'taxable_income': {'line': '15', 'type': 'currency', 'calculated': True},
                    'tax': {'line': '16', 'type': 'currency', 'calculated': True},
                    'child_tax_credit': {'line': '19', 'type': 'currency', 'calculated': True},
                    'total_credits': {'line': '20', 'type': 'currency', 'calculated': True},
                    'tax_after_credits': {'line': '22', 'type': 'currency', 'calculated': True},
                    'self_employment_tax': {'line': '23', 'type': 'currency', 'calculated': True},
                    'total_tax': {'line': '24', 'type': 'currency', 'calculated': True},
                    'federal_withholding': {'line': '25a', 'type': 'currency', 'required': True},
                    'estimated_payments': {'line': '26', 'type': 'currency', 'required': False},
                    'earned_income_credit': {'line': '27a', 'type': 'currency', 'calculated': True},
                    'total_payments': {'line': '33', 'type': 'currency', 'calculated': True},
                    'refund': {'line': '34', 'type': 'currency', 'calculated': True},
                    'amount_owed': {'line': '37', 'type': 'currency', 'calculated': True}
                }
            },
            'schedule_c': {
                'title': 'Profit or Loss From Business',
                'fields': {
                    'business_name': {'line': 'A', 'type': 'text', 'required': True},
                    'business_code': {'line': 'B', 'type': 'text', 'required': True},
                    'business_address': {'line': 'C', 'type': 'text', 'required': True},
                    'accounting_method': {'line': 'F', 'type': 'checkbox', 'required': True},
                    'gross_receipts': {'line': '1', 'type': 'currency', 'required': True},
                    'returns_allowances': {'line': '2', 'type': 'currency', 'required': False},
                    'cost_of_goods_sold': {'line': '4', 'type': 'currency', 'required': False},
                    'gross_profit': {'line': '7', 'type': 'currency', 'calculated': True},
                    'advertising': {'line': '8', 'type': 'currency', 'required': False},
                    'car_truck_expenses': {'line': '9', 'type': 'currency', 'required': False},
                    'commissions_fees': {'line': '10', 'type': 'currency', 'required': False},
                    'contract_labor': {'line': '11', 'type': 'currency', 'required': False},
                    'depletion': {'line': '12', 'type': 'currency', 'required': False},
                    'depreciation': {'line': '13', 'type': 'currency', 'required': False},
                    'employee_benefit_programs': {'line': '14', 'type': 'currency', 'required': False},
                    'insurance': {'line': '15', 'type': 'currency', 'required': False},
                    'interest_mortgage': {'line': '16a', 'type': 'currency', 'required': False},
                    'interest_other': {'line': '16b', 'type': 'currency', 'required': False},
                    'legal_professional': {'line': '17', 'type': 'currency', 'required': False},
                    'office_expense': {'line': '18', 'type': 'currency', 'required': False},
                    'pension_plans': {'line': '19', 'type': 'currency', 'required': False},
                    'rent_lease_vehicles': {'line': '20a', 'type': 'currency', 'required': False},
                    'rent_lease_other': {'line': '20b', 'type': 'currency', 'required': False},
                    'repairs_maintenance': {'line': '21', 'type': 'currency', 'required': False},
                    'supplies': {'line': '22', 'type': 'currency', 'required': False},
                    'taxes_licenses': {'line': '23', 'type': 'currency', 'required': False},
                    'travel_meals': {'line': '24a', 'type': 'currency', 'required': False},
                    'utilities': {'line': '25', 'type': 'currency', 'required': False},
                    'wages': {'line': '26', 'type': 'currency', 'required': False},
                    'other_expenses': {'line': '27a', 'type': 'currency', 'required': False},
                    'total_expenses': {'line': '28', 'type': 'currency', 'calculated': True},
                    'net_profit_loss': {'line': '31', 'type': 'currency', 'calculated': True}
                }
            },
            'schedule_d': {
                'title': 'Capital Gains and Losses',
                'fields': {
                    'short_term_totals': {'line': '7', 'type': 'currency', 'calculated': True},
                    'long_term_totals': {'line': '15', 'type': 'currency', 'calculated': True},
                    'net_capital_gain_loss': {'line': '16', 'type': 'currency', 'calculated': True}
                }
            },
            'schedule_se': {
                'title': 'Self-Employment Tax',
                'fields': {
                    'net_earnings_from_self_employment': {'line': '4a', 'type': 'currency', 'required': True},
                    'self_employment_tax': {'line': '12', 'type': 'currency', 'calculated': True},
                    'deductible_part_se_tax': {'line': '13', 'type': 'currency', 'calculated': True}
                }
            },
            'schedule_a': {
                'title': 'Itemized Deductions',
                'fields': {
                    'medical_dental': {'line': '4', 'type': 'currency', 'required': False},
                    'state_local_taxes': {'line': '5a', 'type': 'currency', 'required': False},
                    'real_estate_taxes': {'line': '5b', 'type': 'currency', 'required': False},
                    'personal_property_taxes': {'line': '5c', 'type': 'currency', 'required': False},
                    'other_taxes': {'line': '5d', 'type': 'currency', 'required': False},
                    'home_mortgage_interest': {'line': '8a', 'type': 'currency', 'required': False},
                    'home_mortgage_points': {'line': '8b', 'type': 'currency', 'required': False},
                    'investment_interest': {'line': '9', 'type': 'currency', 'required': False},
                    'gifts_to_charity_cash': {'line': '11', 'type': 'currency', 'required': False},
                    'gifts_to_charity_other': {'line': '12', 'type': 'currency', 'required': False},
                    'casualty_theft_losses': {'line': '15', 'type': 'currency', 'required': False},
                    'unreimbursed_employee_expenses': {'line': '16', 'type': 'currency', 'required': False},
                    'tax_preparation_fees': {'line': '17', 'type': 'currency', 'required': False},
                    'other_miscellaneous': {'line': '18', 'type': 'currency', 'required': False},
                    'total_itemized_deductions': {'line': '29', 'type': 'currency', 'calculated': True}
                }
            }
        }

    def _load_state_form_templates(self) -> Dict:
        """Load state tax form templates"""
        return {
            'CA': {
                '540': {
                    'title': 'California Resident Income Tax Return',
                    'fields': {
                        'federal_agi': {'line': '13', 'type': 'currency', 'required': True},
                        'ca_adjustments': {'line': '21', 'type': 'currency', 'required': False},
                        'ca_agi': {'line': '19', 'type': 'currency', 'calculated': True},
                        'ca_standard_deduction': {'line': '31', 'type': 'currency', 'calculated': True},
                        'ca_itemized_deductions': {'line': '32', 'type': 'currency', 'required': False},
                        'ca_taxable_income': {'line': '33', 'type': 'currency', 'calculated': True},
                        'ca_tax': {'line': '40', 'type': 'currency', 'calculated': True},
                        'ca_withholding': {'line': '62', 'type': 'currency', 'required': True}
                    }
                }
            },
            'NY': {
                'IT-201': {
                    'title': 'New York State Resident Income Tax Return',
                    'fields': {
                        'federal_agi': {'line': '32', 'type': 'currency', 'required': True},
                        'ny_additions': {'line': '33', 'type': 'currency', 'required': False},
                        'ny_subtractions': {'line': '34', 'type': 'currency', 'required': False},
                        'ny_agi': {'line': '35', 'type': 'currency', 'calculated': True},
                        'ny_standard_deduction': {'line': '36', 'type': 'currency', 'calculated': True},
                        'ny_itemized_deductions': {'line': '37', 'type': 'currency', 'required': False},
                        'ny_taxable_income': {'line': '39', 'type': 'currency', 'calculated': True},
                        'ny_tax': {'line': '40', 'type': 'currency', 'calculated': True}
                    }
                }
            }
        }

    def generate_form_1040(self, tax_return: Dict, user_data: Dict) -> Dict:
        """Generate Form 1040 with calculated values"""
        form_data = {}

        # Personal information
        form_data['first_name'] = user_data.get('first_name', '')
        form_data['last_name'] = user_data.get('last_name', '')
        form_data['ssn'] = user_data.get('ssn', '')
        form_data['address'] = user_data.get('address', '')
        form_data['city_state_zip'] = f"{user_data.get('city', '')}, {user_data.get('state', '')} {user_data.get('zip_code', '')}"

        # Filing status
        filing_status = tax_return.get('filing_status', 'single')
        form_data['filing_status'] = filing_status

        if filing_status in ['married_filing_jointly', 'married_filing_separately']:
            form_data['spouse_first_name'] = tax_return.get('spouse_first_name', '')
            form_data['spouse_last_name'] = tax_return.get('spouse_last_name', '')
            form_data['spouse_ssn'] = tax_return.get('spouse_ssn', '')

        # Income
        form_data['wages_salaries'] = tax_return.get('w2_wages', 0)
        form_data['taxable_interest'] = tax_return.get('interest_income', 0)
        form_data['ordinary_dividends'] = tax_return.get('dividend_income', 0)
        form_data['qualified_dividends'] = tax_return.get('qualified_dividends', 0)
        form_data['capital_gain_loss'] = tax_return.get('capital_gains', 0)
        form_data['other_income'] = tax_return.get('other_income', 0)

        # Calculate total income
        income_fields = ['wages_salaries', 'taxable_interest', 'ordinary_dividends', 'capital_gain_loss', 'other_income']
        form_data['total_income'] = sum(form_data.get(field, 0) for field in income_fields)

        # Adjustments and AGI
        form_data['adjustments_to_income'] = tax_return.get('adjustments', 0)
        form_data['adjusted_gross_income'] = form_data['total_income'] - form_data['adjustments_to_income']

        # Deductions
        form_data['standard_deduction'] = tax_return.get('standard_deduction', 0)
        form_data['itemized_deductions'] = tax_return.get('itemized_deductions', 0)
        form_data['qualified_business_income'] = tax_return.get('qbi_deduction', 0)

        # Taxable income
        deduction_amount = max(form_data['standard_deduction'], form_data['itemized_deductions'])
        form_data['taxable_income'] = max(0, form_data['adjusted_gross_income'] - deduction_amount - form_data['qualified_business_income'])

        # Tax calculations
        form_data['tax'] = tax_return.get('federal_tax', 0)
        form_data['child_tax_credit'] = tax_return.get('child_tax_credit', 0)
        form_data['total_credits'] = tax_return.get('total_credits', 0)
        form_data['tax_after_credits'] = max(0, form_data['tax'] - form_data['total_credits'])
        form_data['self_employment_tax'] = tax_return.get('self_employment_tax', 0)
        form_data['total_tax'] = form_data['tax_after_credits'] + form_data['self_employment_tax']

        # Payments
        form_data['federal_withholding'] = tax_return.get('federal_withholding', 0)
        form_data['estimated_payments'] = tax_return.get('estimated_payments', 0)
        form_data['earned_income_credit'] = tax_return.get('earned_income_credit', 0)
        form_data['total_payments'] = (form_data['federal_withholding'] + 
                                     form_data['estimated_payments'] + 
                                     form_data['earned_income_credit'])

        # Refund or amount owed
        if form_data['total_payments'] > form_data['total_tax']:
            form_data['refund'] = form_data['total_payments'] - form_data['total_tax']
            form_data['amount_owed'] = 0
        else:
            form_data['refund'] = 0
            form_data['amount_owed'] = form_data['total_tax'] - form_data['total_payments']

        return {
            'form_name': '1040',
            'form_title': 'U.S. Individual Income Tax Return',
            'tax_year': tax_return.get('tax_year', 2023),
            'form_data': form_data,
            'generated_date': datetime.now().isoformat()
        }

    def generate_schedule_c(self, business_data: Dict) -> Dict:
        """Generate Schedule C for business income"""
        form_data = {}

        # Business information
        form_data['business_name'] = business_data.get('business_name', '')
        form_data['business_code'] = business_data.get('business_code', '')
        form_data['business_address'] = business_data.get('business_address', '')
        form_data['accounting_method'] = business_data.get('accounting_method', 'cash')

        # Income
        form_data['gross_receipts'] = business_data.get('gross_receipts', 0)
        form_data['returns_allowances'] = business_data.get('returns_allowances', 0)
        form_data['cost_of_goods_sold'] = business_data.get('cost_of_goods_sold', 0)
        form_data['gross_profit'] = (form_data['gross_receipts'] - 
                                   form_data['returns_allowances'] - 
                                   form_data['cost_of_goods_sold'])

        # Expenses
        expense_fields = [
            'advertising', 'car_truck_expenses', 'commissions_fees', 'contract_labor',
            'depletion', 'depreciation', 'employee_benefit_programs', 'insurance',
            'interest_mortgage', 'interest_other', 'legal_professional', 'office_expense',
            'pension_plans', 'rent_lease_vehicles', 'rent_lease_other', 'repairs_maintenance',
            'supplies', 'taxes_licenses', 'travel_meals', 'utilities', 'wages', 'other_expenses'
        ]

        total_expenses = 0
        for field in expense_fields:
            amount = business_data.get(field, 0)
            form_data[field] = amount
            total_expenses += amount

        form_data['total_expenses'] = total_expenses
        form_data['net_profit_loss'] = form_data['gross_profit'] - total_expenses

        return {
            'form_name': 'Schedule C',
            'form_title': 'Profit or Loss From Business',
            'form_data': form_data,
            'generated_date': datetime.now().isoformat()
        }

    def generate_schedule_a(self, itemized_deductions: Dict) -> Dict:
        """Generate Schedule A for itemized deductions"""
        form_data = {}

        # Medical and dental expenses
        form_data['medical_dental'] = itemized_deductions.get('medical_dental', 0)

        # Taxes
        form_data['state_local_taxes'] = itemized_deductions.get('state_local_taxes', 0)
        form_data['real_estate_taxes'] = itemized_deductions.get('real_estate_taxes', 0)
        form_data['personal_property_taxes'] = itemized_deductions.get('personal_property_taxes', 0)
        form_data['other_taxes'] = itemized_deductions.get('other_taxes', 0)

        # Interest
        form_data['home_mortgage_interest'] = itemized_deductions.get('home_mortgage_interest', 0)
        form_data['home_mortgage_points'] = itemized_deductions.get('home_mortgage_points', 0)
        form_data['investment_interest'] = itemized_deductions.get('investment_interest', 0)

        # Charitable contributions
        form_data['gifts_to_charity_cash'] = itemized_deductions.get('gifts_to_charity_cash', 0)
        form_data['gifts_to_charity_other'] = itemized_deductions.get('gifts_to_charity_other', 0)

        # Other deductions
        form_data['casualty_theft_losses'] = itemized_deductions.get('casualty_theft_losses', 0)
        form_data['unreimbursed_employee_expenses'] = itemized_deductions.get('unreimbursed_employee_expenses', 0)
        form_data['tax_preparation_fees'] = itemized_deductions.get('tax_preparation_fees', 0)
        form_data['other_miscellaneous'] = itemized_deductions.get('other_miscellaneous', 0)

        # Calculate total
        deduction_fields = [
            'medical_dental', 'state_local_taxes', 'real_estate_taxes', 'personal_property_taxes',
            'other_taxes', 'home_mortgage_interest', 'home_mortgage_points', 'investment_interest',
            'gifts_to_charity_cash', 'gifts_to_charity_other', 'casualty_theft_losses',
            'unreimbursed_employee_expenses', 'tax_preparation_fees', 'other_miscellaneous'
        ]

        form_data['total_itemized_deductions'] = sum(form_data.get(field, 0) for field in deduction_fields)

        return {
            'form_name': 'Schedule A',
            'form_title': 'Itemized Deductions',
            'form_data': form_data,
            'generated_date': datetime.now().isoformat()
        }

    def generate_state_form(self, state: str, form_name: str, tax_data: Dict) -> Dict:
        """Generate state tax forms"""
        if state not in self.state_forms or form_name not in self.state_forms[state]:
            return {'error': f'Form {form_name} not available for state {state}'}

        form_template = self.state_forms[state][form_name]
        form_data = {}

        if state == 'CA' and form_name == '540':
            # California Form 540
            form_data['federal_agi'] = tax_data.get('adjusted_gross_income', 0)
            form_data['ca_adjustments'] = tax_data.get('ca_adjustments', 0)
            form_data['ca_agi'] = form_data['federal_agi'] + form_data['ca_adjustments']
            form_data['ca_standard_deduction'] = tax_data.get('ca_standard_deduction', 5202)
            form_data['ca_itemized_deductions'] = tax_data.get('ca_itemized_deductions', 0)

            deduction = max(form_data['ca_standard_deduction'], form_data['ca_itemized_deductions'])
            form_data['ca_taxable_income'] = max(0, form_data['ca_agi'] - deduction)
            form_data['ca_tax'] = tax_data.get('state_tax', 0)
            form_data['ca_withholding'] = tax_data.get('state_withholding', 0)

        elif state == 'NY' and form_name == 'IT-201':
            # New York Form IT-201
            form_data['federal_agi'] = tax_data.get('adjusted_gross_income', 0)
            form_data['ny_additions'] = tax_data.get('ny_additions', 0)
            form_data['ny_subtractions'] = tax_data.get('ny_subtractions', 0)
            form_data['ny_agi'] = (form_data['federal_agi'] + 
                                 form_data['ny_additions'] - 
                                 form_data['ny_subtractions'])
            form_data['ny_standard_deduction'] = tax_data.get('ny_standard_deduction', 8000)
            form_data['ny_itemized_deductions'] = tax_data.get('ny_itemized_deductions', 0)

            deduction = max(form_data['ny_standard_deduction'], form_data['ny_itemized_deductions'])
            form_data['ny_taxable_income'] = max(0, form_data['ny_agi'] - deduction)
            form_data['ny_tax'] = tax_data.get('state_tax', 0)

        return {
            'form_name': form_name,
            'form_title': form_template['title'],
            'state': state,
            'form_data': form_data,
            'generated_date': datetime.now().isoformat()
        }

    def generate_complete_tax_package(self, tax_return_data: Dict, user_data: Dict) -> Dict:
        """Generate complete tax filing package with all required forms"""
        package = {
            'tax_year': tax_return_data.get('tax_year', 2023),
            'filing_status': tax_return_data.get('filing_status', 'single'),
            'forms': [],
            'generated_date': datetime.now().isoformat()
        }

        # Generate Form 1040
        form_1040 = self.generate_form_1040(tax_return_data, user_data)
        package['forms'].append(form_1040)

        # Generate Schedule C if business income exists
        if tax_return_data.get('has_business_income', False):
            business_data = tax_return_data.get('business_data', {})
            schedule_c = self.generate_schedule_c(business_data)
            package['forms'].append(schedule_c)

        # Generate Schedule A if itemizing deductions
        if tax_return_data.get('itemize_deductions', False):
            itemized_deductions = tax_return_data.get('itemized_deductions', {})
            schedule_a = self.generate_schedule_a(itemized_deductions)
            package['forms'].append(schedule_a)

        # Generate state forms if applicable
        state = user_data.get('state', '')
        if state in self.state_forms:
            for form_name in self.state_forms[state]:
                state_form = self.generate_state_form(state, form_name, tax_return_data)
                if 'error' not in state_form:
                    package['forms'].append(state_form)

        return package

    def validate_form_data(self, form_name: str, form_data: Dict) -> Dict:
        """Validate form data against form requirements"""
        if form_name not in self.form_templates:
            return {'valid': False, 'errors': [f'Unknown form: {form_name}']}

        template = self.form_templates[form_name]
        errors = []

        for field_name, field_config in template['fields'].items():
            if field_config.get('required', False) and field_name not in form_data:
                errors.append(f'Required field missing: {field_name}')

            if field_name in form_data:
                value = form_data[field_name]
                field_type = field_config.get('type', 'text')

                if field_type == 'currency' and not isinstance(value, (int, float)):
                    errors.append(f'Field {field_name} must be a number')
                elif field_type == 'ssn' and not self._validate_ssn(value):
                    errors.append(f'Invalid SSN format for field {field_name}')

        return {
            'valid': len(errors) == 0,
            'errors': errors
        }

    def _validate_ssn(self, ssn: str) -> bool:
        """Validate SSN format"""
        if not ssn:
            return False

        # Remove dashes and spaces
        clean_ssn = ssn.replace('-', '').replace(' ', '')

        # Check if it's 9 digits
        return len(clean_ssn) == 9 and clean_ssn.isdigit()

class FormPDFGenerator:
    """Generate PDF versions of tax forms"""

    def __init__(self):
        pass

    def generate_pdf(self, form_data: Dict) -> bytes:
        """Generate PDF from form data (placeholder - would use reportlab or similar)"""
        # This would integrate with a PDF generation library
        # For now, return a placeholder
        pdf_content = f"""
        PDF Generation for {form_data.get('form_name', 'Unknown Form')}
        Generated on: {form_data.get('generated_date', 'Unknown Date')}

        Form Data:
        {json.dumps(form_data.get('form_data', {}), indent=2)}
        """
        return pdf_content.encode('utf-8')

    def generate_complete_package_pdf(self, tax_package: Dict) -> bytes:
        """Generate complete PDF package for all forms"""
        # This would combine all forms into a single PDF
        pdf_content = f"""
        Complete Tax Filing Package
        Tax Year: {tax_package.get('tax_year', 'Unknown')}
        Filing Status: {tax_package.get('filing_status', 'Unknown')}
        Generated: {tax_package.get('generated_date', 'Unknown')}

        Forms Included:
        """

        for form in tax_package.get('forms', []):
            pdf_content += f"\n- {form.get('form_name', 'Unknown')}: {form.get('form_title', 'Unknown Title')}"

        return pdf_content.encode('utf-8')
