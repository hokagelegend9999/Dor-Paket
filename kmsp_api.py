# kmsp_api.py
import requests
import config

BASE_URLS = {
    "accesstokenlist": "https://golang-openapi-accesstokenlist-xltembakservice.kmsp-store.com/v1",
    "login": "https://golang-openapi-login-xltembakservice.kmsp-store.com/v1",
    "purchase": "https://golang-openapi-packagepurchase-xltembakservice.kmsp-store.com/v1"
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
        print(f"API request error: {e}")
        return {'status': False, 'message': f"Gagal menghubungi server API: {e}"}

def get_logged_in_numbers():
    """Mendapatkan daftar nomor yang sudah login beserta token dan session_id."""
    response = _api_get(BASE_URLS['accesstokenlist'])
    nomor_map = {}
    if response and response.get('status') and response.get('data'):
        for item in response['data']:
            if item.get('msisdn'):
                nomor_map[item['msisdn']] = {'token': item.get('token'), 'session_id': item.get('session_id')}
    return nomor_map

def _extend_session(phone, session_id, token):
    """Mencoba refresh token (extend session)."""
    params = {'phone': phone, 'method': 'LOGIN_BY_ACCESS_TOKEN', 'auth_id': f"{session_id}:{token}"}
    return _api_get(BASE_URLS['login'], params)

def purchase_package(package_code, phone_number, payment_method, price_or_fee):
    """Fungsi utama untuk pembelian paket, termasuk auto-refresh token."""
    if phone_number.startswith('08'):
        phone_number = '62' + phone_number[1:]
    
    logged_in_numbers = get_logged_in_numbers()
    if phone_number not in logged_in_numbers:
        return {'status': False, 'message': 'Nomor ini belum login OTP atau token expired.'}
    
    active_number_data = logged_in_numbers[phone_number]
    access_token = active_number_data['token']
    params = {"package_code": package_code, "phone": phone_number, "access_token": access_token, "payment_method": payment_method, "price_or_fee": price_or_fee}
    
    purchase_result = _api_get(BASE_URLS['purchase'], params)

    # Jika token invalid, coba refresh otomatis sekali
    if (purchase_result and not purchase_result.get('status') and 
        'invalid access token' in purchase_result.get('message', '').lower()):
        
        session_id = active_number_data['session_id']
        extend_result = _extend_session(phone_number, session_id, access_token)
        
        if extend_result and extend_result.get('status') and 'access_token' in extend_result.get('data', {}):
            params['access_token'] = extend_result['data']['access_token']
            purchase_result = _api_get(BASE_URLS['purchase'], params)

    return purchase_result
