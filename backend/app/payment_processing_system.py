
from typing import Dict, List, Optional, Any
import json
import uuid
from datetime import datetime, timedelta
from decimal import Decimal
import hashlib
import hmac
from enum import Enum

class PaymentMethod(Enum):
    BANK_TRANSFER = "bank_transfer"
    CREDIT_CARD = "credit_card"
    DEBIT_CARD = "debit_card"
    ACH = "ach"
    CHECK = "check"

class PaymentStatus(Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    REFUNDED = "refunded"

class PaymentType(Enum):
    TAX_PAYMENT = "tax_payment"
    ESTIMATED_TAX = "estimated_tax"
    PENALTY = "penalty"
    INTEREST = "interest"
    EXTENSION_FEE = "extension_fee"
    SERVICE_FEE = "service_fee"

class PaymentProcessor:
    """
    Comprehensive payment processing system for tax payments
    Supports multiple payment methods and integrates with mock payment gateways
    """

    def __init__(self):
        self.payment_gateways = self._initialize_payment_gateways()
        self.fee_structure = self._initialize_fee_structure()
        self.payment_limits = self._initialize_payment_limits()

    def _initialize_payment_gateways(self) -> Dict:
        """Initialize payment gateway configurations"""
        return {
            'stripe': {
                'name': 'Stripe',
                'api_key': 'sk_test_mock_stripe_key',
                'webhook_secret': 'whsec_mock_webhook_secret',
                'supported_methods': ['credit_card', 'debit_card', 'ach'],
                'fees': {
                    'credit_card': 0.029,  # 2.9%
                    'debit_card': 0.029,
                    'ach': 0.008  # 0.8%
                }
            },
            'plaid': {
                'name': 'Plaid',
                'api_key': 'mock_plaid_key',
                'supported_methods': ['bank_transfer', 'ach'],
                'fees': {
                    'bank_transfer': 0.005,  # 0.5%
                    'ach': 0.005
                }
            },
            'irs_eftps': {
                'name': 'IRS Electronic Federal Tax Payment System',
                'api_key': 'mock_eftps_key',
                'supported_methods': ['bank_transfer', 'ach'],
                'fees': {
                    'bank_transfer': 0.0,  # No fee for direct IRS payments
                    'ach': 0.0
                }
            }
        }

    def _initialize_fee_structure(self) -> Dict:
        """Initialize fee structure for different payment types"""
        return {
            'convenience_fees': {
                'credit_card': 1.99,  # Flat fee
                'debit_card': 1.99,
                'bank_transfer': 0.0,
                'ach': 0.0,
                'check': 0.0
            },
            'processing_fees': {
                'same_day': 25.00,
                'next_day': 10.00,
                'standard': 0.00
            },
            'minimum_fees': {
                'credit_card': 2.50,
                'debit_card': 2.50
            }
        }

    def _initialize_payment_limits(self) -> Dict:
        """Initialize payment limits for different methods"""
        return {
            'daily_limits': {
                'credit_card': 100000.00,
                'debit_card': 50000.00,
                'bank_transfer': 1000000.00,
                'ach': 1000000.00,
                'check': float('inf')
            },
            'transaction_limits': {
                'credit_card': 25000.00,
                'debit_card': 10000.00,
                'bank_transfer': 100000.00,
                'ach': 100000.00,
                'check': float('inf')
            }
        }

    def calculate_payment_fees(self, amount: float, payment_method: PaymentMethod, processing_speed: str = 'standard') -> Dict:
        """Calculate fees for a payment"""
        method_str = payment_method.value

        # Convenience fee
        convenience_fee = self.fee_structure['convenience_fees'].get(method_str, 0.0)

        # Processing fee based on speed
        processing_fee = self.fee_structure['processing_fees'].get(processing_speed, 0.0)

        # Gateway fee (percentage)
        gateway_fee = 0.0
        for gateway, config in self.payment_gateways.items():
            if method_str in config['supported_methods']:
                gateway_fee = amount * config['fees'].get(method_str, 0.0)
                break

        # Apply minimum fee if applicable
        minimum_fee = self.fee_structure['minimum_fees'].get(method_str, 0.0)
        if convenience_fee > 0 and convenience_fee < minimum_fee:
            convenience_fee = minimum_fee

        total_fees = convenience_fee + processing_fee + gateway_fee

        return {
            'convenience_fee': round(convenience_fee, 2),
            'processing_fee': round(processing_fee, 2),
            'gateway_fee': round(gateway_fee, 2),
            'total_fees': round(total_fees, 2),
            'total_amount': round(amount + total_fees, 2)
        }

    def validate_payment_limits(self, amount: float, payment_method: PaymentMethod, user_id: str) -> Dict:
        """Validate payment against limits"""
        method_str = payment_method.value

        # Check transaction limit
        transaction_limit = self.payment_limits['transaction_limits'].get(method_str, float('inf'))
        if amount > transaction_limit:
            return {
                'valid': False,
                'error': f'Amount exceeds transaction limit of ${transaction_limit:,.2f} for {method_str}'
            }

        # Check daily limit (would need to query database for user's daily total)
        daily_limit = self.payment_limits['daily_limits'].get(method_str, float('inf'))
        # Mock daily usage check
        daily_usage = self._get_daily_usage(user_id, method_str)
        if daily_usage + amount > daily_limit:
            return {
                'valid': False,
                'error': f'Amount would exceed daily limit of ${daily_limit:,.2f} for {method_str}'
            }

        return {'valid': True}

    def _get_daily_usage(self, user_id: str, payment_method: str) -> float:
        """Get user's daily payment usage (mock implementation)"""
        # In real implementation, this would query the database
        return 0.0

    def process_payment(self, payment_data: Dict) -> Dict:
        """Process a payment transaction"""
        try:
            # Validate payment data
            validation_result = self._validate_payment_data(payment_data)
            if not validation_result['valid']:
                return {
                    'success': False,
                    'error': validation_result['error'],
                    'transaction_id': None
                }

            # Generate transaction ID
            transaction_id = self._generate_transaction_id()

            # Calculate fees
            amount = payment_data['amount']
            payment_method = PaymentMethod(payment_data['payment_method'])
            processing_speed = payment_data.get('processing_speed', 'standard')

            fee_calculation = self.calculate_payment_fees(amount, payment_method, processing_speed)

            # Validate limits
            limit_validation = self.validate_payment_limits(amount, payment_method, payment_data['user_id'])
            if not limit_validation['valid']:
                return {
                    'success': False,
                    'error': limit_validation['error'],
                    'transaction_id': transaction_id
                }

            # Process with appropriate gateway
            gateway_result = self._process_with_gateway(payment_data, transaction_id, fee_calculation)

            # Create payment record
            payment_record = {
                'transaction_id': transaction_id,
                'user_id': payment_data['user_id'],
                'tax_return_id': payment_data.get('tax_return_id'),
                'amount': amount,
                'payment_method': payment_method.value,
                'payment_type': payment_data.get('payment_type', PaymentType.TAX_PAYMENT.value),
                'fees': fee_calculation,
                'status': gateway_result['status'],
                'gateway_transaction_id': gateway_result.get('gateway_transaction_id'),
                'created_at': datetime.now().isoformat(),
                'scheduled_date': payment_data.get('scheduled_date'),
                'description': payment_data.get('description', 'Tax payment')
            }

            return {
                'success': True,
                'transaction_id': transaction_id,
                'payment_record': payment_record,
                'gateway_response': gateway_result
            }

        except Exception as e:
            return {
                'success': False,
                'error': f'Payment processing failed: {str(e)}',
                'transaction_id': None
            }

    def _validate_payment_data(self, payment_data: Dict) -> Dict:
        """Validate payment data"""
        required_fields = ['user_id', 'amount', 'payment_method']

        for field in required_fields:
            if field not in payment_data:
                return {'valid': False, 'error': f'Missing required field: {field}'}

        # Validate amount
        if payment_data['amount'] <= 0:
            return {'valid': False, 'error': 'Payment amount must be greater than 0'}

        # Validate payment method
        try:
            PaymentMethod(payment_data['payment_method'])
        except ValueError:
            return {'valid': False, 'error': 'Invalid payment method'}

        # Validate payment method specific data
        method = payment_data['payment_method']
        if method in ['credit_card', 'debit_card']:
            if not self._validate_card_data(payment_data.get('card_data', {})):
                return {'valid': False, 'error': 'Invalid card data'}
        elif method in ['bank_transfer', 'ach']:
            if not self._validate_bank_data(payment_data.get('bank_data', {})):
                return {'valid': False, 'error': 'Invalid bank account data'}

        return {'valid': True}

    def _validate_card_data(self, card_data: Dict) -> bool:
        """Validate credit/debit card data"""
        required_fields = ['card_number', 'expiry_month', 'expiry_year', 'cvv']
        return all(field in card_data for field in required_fields)

    def _validate_bank_data(self, bank_data: Dict) -> bool:
        """Validate bank account data"""
        required_fields = ['account_number', 'routing_number', 'account_type']
        return all(field in bank_data for field in required_fields)

    def _generate_transaction_id(self) -> str:
        """Generate unique transaction ID"""
        return f"TXN_{datetime.now().strftime('%Y%m%d')}_{uuid.uuid4().hex[:8].upper()}"

    def _process_with_gateway(self, payment_data: Dict, transaction_id: str, fee_calculation: Dict) -> Dict:
        """Process payment with appropriate gateway (mock implementation)"""
        payment_method = payment_data['payment_method']
        amount = fee_calculation['total_amount']

        # Select gateway based on payment method
        selected_gateway = None
        for gateway, config in self.payment_gateways.items():
            if payment_method in config['supported_methods']:
                selected_gateway = gateway
                break

        if not selected_gateway:
            return {
                'status': PaymentStatus.FAILED.value,
                'error': f'No gateway available for payment method: {payment_method}'
            }

        # Mock gateway processing
        if selected_gateway == 'stripe':
            return self._process_stripe_payment(payment_data, transaction_id, amount)
        elif selected_gateway == 'plaid':
            return self._process_plaid_payment(payment_data, transaction_id, amount)
        elif selected_gateway == 'irs_eftps':
            return self._process_eftps_payment(payment_data, transaction_id, amount)

        return {
            'status': PaymentStatus.FAILED.value,
            'error': 'Unknown gateway'
        }

    def _process_stripe_payment(self, payment_data: Dict, transaction_id: str, amount: float) -> Dict:
        """Mock Stripe payment processing"""
        # In real implementation, this would call Stripe API
        gateway_transaction_id = f"pi_{uuid.uuid4().hex[:24]}"

        # Mock success/failure (90% success rate)
        import random
        if random.random() < 0.9:
            return {
                'status': PaymentStatus.COMPLETED.value,
                'gateway_transaction_id': gateway_transaction_id,
                'gateway': 'stripe',
                'processed_at': datetime.now().isoformat()
            }
        else:
            return {
                'status': PaymentStatus.FAILED.value,
                'error': 'Card declined',
                'gateway': 'stripe'
            }

    def _process_plaid_payment(self, payment_data: Dict, transaction_id: str, amount: float) -> Dict:
        """Mock Plaid payment processing"""
        gateway_transaction_id = f"plaid_{uuid.uuid4().hex[:16]}"

        return {
            'status': PaymentStatus.PROCESSING.value,  # Bank transfers typically take time
            'gateway_transaction_id': gateway_transaction_id,
            'gateway': 'plaid',
            'estimated_completion': (datetime.now() + timedelta(days=1)).isoformat()
        }

    def _process_eftps_payment(self, payment_data: Dict, transaction_id: str, amount: float) -> Dict:
        """Mock IRS EFTPS payment processing"""
        gateway_transaction_id = f"eftps_{uuid.uuid4().hex[:12]}"

        return {
            'status': PaymentStatus.PROCESSING.value,
            'gateway_transaction_id': gateway_transaction_id,
            'gateway': 'irs_eftps',
            'estimated_completion': (datetime.now() + timedelta(days=2)).isoformat()
        }

    def schedule_payment(self, payment_data: Dict, scheduled_date: str) -> Dict:
        """Schedule a future payment"""
        try:
            scheduled_datetime = datetime.fromisoformat(scheduled_date)
            if scheduled_datetime <= datetime.now():
                return {
                    'success': False,
                    'error': 'Scheduled date must be in the future'
                }

            # Add scheduled date to payment data
            payment_data['scheduled_date'] = scheduled_date
            payment_data['status'] = PaymentStatus.PENDING.value

            # Generate transaction ID for scheduled payment
            transaction_id = self._generate_transaction_id()

            return {
                'success': True,
                'transaction_id': transaction_id,
                'scheduled_date': scheduled_date,
                'status': PaymentStatus.PENDING.value
            }

        except ValueError:
            return {
                'success': False,
                'error': 'Invalid date format'
            }

    def cancel_payment(self, transaction_id: str, user_id: str) -> Dict:
        """Cancel a pending payment"""
        # In real implementation, this would update the database and potentially call gateway APIs
        return {
            'success': True,
            'transaction_id': transaction_id,
            'status': PaymentStatus.CANCELLED.value,
            'cancelled_at': datetime.now().isoformat()
        }

    def refund_payment(self, transaction_id: str, amount: Optional[float] = None, reason: str = '') -> Dict:
        """Process a refund"""
        # In real implementation, this would call the appropriate gateway's refund API
        refund_id = f"re_{uuid.uuid4().hex[:16]}"

        return {
            'success': True,
            'refund_id': refund_id,
            'transaction_id': transaction_id,
            'refund_amount': amount,
            'reason': reason,
            'status': PaymentStatus.REFUNDED.value,
            'processed_at': datetime.now().isoformat()
        }

    def get_payment_status(self, transaction_id: str) -> Dict:
        """Get current payment status"""
        # In real implementation, this would query the database and potentially the gateway
        return {
            'transaction_id': transaction_id,
            'status': PaymentStatus.COMPLETED.value,
            'last_updated': datetime.now().isoformat()
        }

    def process_webhook(self, gateway: str, payload: Dict, signature: str) -> Dict:
        """Process webhook from payment gateway"""
        # Verify webhook signature
        if not self._verify_webhook_signature(gateway, payload, signature):
            return {
                'success': False,
                'error': 'Invalid webhook signature'
            }

        # Process webhook based on gateway
        if gateway == 'stripe':
            return self._process_stripe_webhook(payload)
        elif gateway == 'plaid':
            return self._process_plaid_webhook(payload)

        return {
            'success': False,
            'error': f'Unknown gateway: {gateway}'
        }

    def _verify_webhook_signature(self, gateway: str, payload: Dict, signature: str) -> bool:
        """Verify webhook signature"""
        if gateway not in self.payment_gateways:
            return False

        webhook_secret = self.payment_gateways[gateway].get('webhook_secret', '')

        # Mock signature verification
        expected_signature = hmac.new(
            webhook_secret.encode(),
            json.dumps(payload).encode(),
            hashlib.sha256
        ).hexdigest()

        return hmac.compare_digest(signature, expected_signature)

    def _process_stripe_webhook(self, payload: Dict) -> Dict:
        """Process Stripe webhook"""
        event_type = payload.get('type', '')

        if event_type == 'payment_intent.succeeded':
            # Update payment status to completed
            return {
                'success': True,
                'action': 'payment_completed',
                'transaction_id': payload.get('data', {}).get('object', {}).get('id')
            }
        elif event_type == 'payment_intent.payment_failed':
            # Update payment status to failed
            return {
                'success': True,
                'action': 'payment_failed',
                'transaction_id': payload.get('data', {}).get('object', {}).get('id')
            }

        return {'success': True, 'action': 'ignored'}

    def _process_plaid_webhook(self, payload: Dict) -> Dict:
        """Process Plaid webhook"""
        webhook_type = payload.get('webhook_type', '')

        if webhook_type == 'TRANSACTIONS':
            return {
                'success': True,
                'action': 'transaction_update',
                'data': payload
            }

        return {'success': True, 'action': 'ignored'}

class PaymentPlanManager:
    """Manage payment plans for tax obligations"""

    def __init__(self):
        self.plan_types = {
            'short_term': {
                'max_duration_days': 120,
                'setup_fee': 0.0,
                'interest_rate': 0.005  # 0.5% per month
            },
            'long_term': {
                'max_duration_months': 72,
                'setup_fee': 149.0,
                'interest_rate': 0.005
            },
            'partial_payment': {
                'min_payment_percentage': 0.20,
                'setup_fee': 89.0,
                'interest_rate': 0.005
            }
        }

    def create_payment_plan(self, total_amount: float, plan_type: str, duration: int, user_id: str) -> Dict:
        """Create a payment plan"""
        if plan_type not in self.plan_types:
            return {
                'success': False,
                'error': f'Invalid plan type: {plan_type}'
            }

        plan_config = self.plan_types[plan_type]

        # Validate duration
        if plan_type == 'short_term' and duration > plan_config['max_duration_days']:
            return {
                'success': False,
                'error': f'Duration exceeds maximum for short-term plan: {plan_config["max_duration_days"]} days'
            }
        elif plan_type == 'long_term' and duration > plan_config['max_duration_months']:
            return {
                'success': False,
                'error': f'Duration exceeds maximum for long-term plan: {plan_config["max_duration_months"]} months'
            }

        # Calculate payment schedule
        setup_fee = plan_config['setup_fee']
        monthly_interest_rate = plan_config['interest_rate']

        if plan_type == 'short_term':
            # Simple division for short-term
            payment_amount = total_amount / (duration / 30)  # Convert days to months
        else:
            # Calculate with interest for long-term
            if monthly_interest_rate > 0:
                payment_amount = (total_amount * monthly_interest_rate * (1 + monthly_interest_rate) ** duration) /                                ((1 + monthly_interest_rate) ** duration - 1)
            else:
                payment_amount = total_amount / duration

        plan_id = f"PLAN_{datetime.now().strftime('%Y%m%d')}_{uuid.uuid4().hex[:8].upper()}"

        return {
            'success': True,
            'plan_id': plan_id,
            'plan_type': plan_type,
            'total_amount': total_amount,
            'setup_fee': setup_fee,
            'payment_amount': round(payment_amount, 2),
            'duration': duration,
            'interest_rate': monthly_interest_rate,
            'created_at': datetime.now().isoformat()
        }

    def calculate_payment_schedule(self, plan_data: Dict) -> List[Dict]:
        """Calculate detailed payment schedule"""
        schedule = []
        payment_amount = plan_data['payment_amount']
        duration = plan_data['duration']
        start_date = datetime.now()

        for i in range(duration):
            payment_date = start_date + timedelta(days=30 * i)  # Monthly payments
            schedule.append({
                'payment_number': i + 1,
                'due_date': payment_date.isoformat(),
                'amount': payment_amount,
                'status': 'pending'
            })

        return schedule
