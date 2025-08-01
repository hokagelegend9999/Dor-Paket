# kmsp_api.py
import requests
import config
import logging

logger = logging.getLogger(__name__)

BASE_URLS = {
    # URL Lama
    "accesstokenlist": "https://golang-openapi-accesstokenlist-xltembakservice.kmsp-store.com/v1",
    "purchase": "https://golang-openapi-packagepurchase-xltembakservice.kmsp-store.com/v1",
    # URL Baru dari Panel Modern
    "reqotp": "https://golang-openapi-reqotp-xltembakservice.kmsp-store.com/v1",
    "login": "https://golang-openapi-login-xltembakservice.kmsp-store.com/v1",
    "subscriberinfo": "https://golang-openapi-subscriberinfo-xltembakservice.kmsp-store.com/v1",
    "subscriberlocation": "https://golang-openapi-subscriberlocation-xltembakservice.kmsp-store.com/v1",
    "quotadetails": "https://golang-openapi-quotadetails-xltembakservice.kmsp-store.com/v1",
    "unregpackage": "https://golang-openapi-unregpackage-xltembakservice.kmsp-store.com/v1"
}

def _api_get(url, params={}):
    """Fungsi helper untuk melakukan request GET ke API."""
    try:
        params['api_key'] = config.KMSP_API_KEY
        headers = {'User-Agent': 'PPOB-Bot-Python'}
        response = requests.get(url, params=params, headers=headers, timeout=30)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        logger.error(f"API request error: {e}")
        return {'status': False, 'message': f"Gagal menghubungi server API: {e}"}

# --- Fungsi untuk Pembelian (sudah ada) ---
def purchase_package(package_code, phone_number, payment_method, price_or_fee):
    # ... (kode fungsi ini tidak berubah, bisa dibiarkan)
    pass # Placeholder

# --- Fungsi-Fungsi Baru untuk Panel XL ---
def request_otp(phone):
    """Meminta OTP ke nomor telepon."""
    params = {'phone': phone, 'method': 'OTP'}
    return _api_get(BASE_URLS['reqotp'], params)

def login_with_otp(phone, auth_id, otp):
    """Login menggunakan OTP untuk mendapatkan access_token."""
    params = {'phone': phone, 'method': 'OTP', 'auth_id': auth_id, 'otp': otp}
    return _api_get(BASE_URLS['login'], params)

def get_subscriber_info(access_token):
    """Cek Pulsa & Masa Aktif."""
    params = {'access_token': access_token}
    return _api_get(BASE_URLS['subscriberinfo'], params)

def get_subscriber_location(access_token):
    """Cek Lokasi Kartu."""
    params = {'access_token': access_token}
    return _api_get(BASE_URLS['subscriberlocation'], params)

def get_quota_details(access_token):
    """Cek Paket Aktif."""
    params = {'access_token': access_token}
    return _api_get(BASE_URLS['quotadetails'], params)

def unreg_package(access_token, encrypted_code):
    """Stop/Unreg paket aktif."""
    params = {'access_token': access_token, 'encrypted_package_code': encrypted_code}
    return _api_get(BASE_URLS['unregpackage'], params)
