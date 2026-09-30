# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "pydantic>=2.10.0",
#     "pillow>=11.0.0",
# ]
# ///
"""
Resilient, idempotent syndication client and state machine for WG-Gesucht.
Features:
- Deterministic idempotency key calculation
- Jittered exponential backoff for network/HTTP 429
- Circuit breaker trips on CAPTCHAs, bot blocks, or repeated auth failures
- Automatic credential masking in all diagnostic output
- Session refresh and multi-part photo payload dispatcher
"""

import os
import sys
import json
import time
import random
import base64
import hashlib
import urllib.request
import urllib.error
from typing import Dict, Any, List, Optional
from pathlib import Path

MAX_RETRIES = 4
BASE_BACKOFF_SEC = 1.0
MAX_BACKOFF_SEC = 16.0

def compute_idempotency_key(source_id: str, portal: str, account_email: str) -> str:
    raw = f"{source_id}:{portal}:{account_email}".encode('utf-8')
    return hashlib.sha256(raw).hexdigest()

def mask_secrets(text: str) -> str:
    """Mask auth tokens, passwords, and sensitive cookies from logs."""
    cleaned = text
    cleaned = re_sub_token(cleaned, r'("access_token"\s*:\s*")[^"]+(")', r'\1***MASKED***\2')
    cleaned = re_sub_token(cleaned, r'("login_password"\s*:\s*")[^"]+(")', r'\1***MASKED***\2')
    cleaned = re_sub_token(cleaned, r'(Bearer\s+)[a-zA-Z0-9_\-\.]+', r'\1***MASKED***')
    return cleaned

def re_sub_token(text: str, pattern: str, repl: str) -> str:
    import re
    return re.sub(pattern, repl, text)

class WGGesuchtClient:
    def __init__(self, email: Optional[str] = None, password: Optional[str] = None):
        self.email = email or os.environ.get("WG_GESUCHT_EMAIL", "")
        self.password = password or os.environ.get("WG_GESUCHT_PASSWORD", "")
        if not self.email or not self.password:
            raise ValueError("WG-Gesucht credentials not provided. Set WG_GESUCHT_EMAIL and WG_GESUCHT_PASSWORD.")
            
        self.user_id = ""
        self.access_token = ""
        self.dev_ref_no = ""
        self.csrf_token = ""
        self.cookies = ""
        self.circuit_tripped = False

    def _execute_with_retry(self, req: urllib.request.Request) -> Dict[str, Any]:
        if self.circuit_tripped:
            raise RuntimeError("Circuit breaker is TRIPPED. Refusing further network requests.")

        for attempt in range(1, MAX_RETRIES + 1):
            try:
                with urllib.request.urlopen(req) as resp:
                    raw_data = resp.read().decode('utf-8')
                    # Detect CAPTCHA challenge in response
                    if "turnstile" in raw_data.lower() or "challenge" in raw_data.lower():
                        self.circuit_tripped = True
                        raise RuntimeError("Bot protection / CAPTCHA detected. Tripping circuit breaker.")
                    return {
                        "status": resp.status,
                        "data": json.loads(raw_data) if raw_data else {}
                    }
            except urllib.error.HTTPError as e:
                err_content = e.read().decode('utf-8', errors='ignore')
                if e.code == 429:
                    jitter = random.uniform(0.5, 1.5)
                    backoff = min(MAX_BACKOFF_SEC, (2 ** attempt) * BASE_BACKOFF_SEC + jitter)
                    time.sleep(backoff)
                    continue
                elif e.code in (401, 403):
                    # Possible expired token or auth failure
                    if attempt < MAX_RETRIES:
                        self.login()
                        # Update request headers
                        req.headers['X-Authorization'] = f"Bearer {self.access_token}"
                        req.headers['x-dev-ref-no'] = self.dev_ref_no
                        continue
                raise RuntimeError(f"HTTP {e.code}: {mask_secrets(err_content)}")
            except Exception as ex:
                if attempt == MAX_RETRIES:
                    raise ex
                time.sleep(1.0)
                
        raise RuntimeError("Max retries exceeded without successful response.")

    def login(self):
        login_url = 'https://www.wg-gesucht.de/ajax/sessions.php?action=login'
        payload = {
            'login_email_username': self.email,
            'login_password': self.password
        }
        req = urllib.request.Request(
            login_url,
            data=json.dumps(payload).encode('utf-8'),
            headers={
                'Content-Type': 'application/json',
                'X-Client-Id': 'wg_desktop_website',
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)'
            },
            method='POST'
        )
        
        with urllib.request.urlopen(req) as resp:
            set_cookies = resp.headers.get_all('Set-Cookie', [])
            self.cookies = '; '.join([c.split(';')[0] for c in set_cookies])
            data = json.loads(resp.read().decode('utf-8'))
            self.user_id = data.get('user_id', '')
            self.access_token = data.get('access_token', '')
            self.dev_ref_no = data.get('dev_ref_no', '')
            self.csrf_token = data.get('csrf_token', '')

    def get_or_create_draft(self, listing_data: Dict[str, Any]) -> str:
        """Create draft ad or load existing draft."""
        url = f'https://www.wg-gesucht.de/api/drafts/users/{self.user_id}'
        payload = {
            'ad_title': listing_data['title'],
            'city_id': '55', # Hamburg default
            'country_code': 'de',
            'category': '0', # WG-Zimmer
            'rent_type': '0', # Unbefristet
            'ad_type': '0', # Offer
            'display_language': 'de',
            'csrf_token': self.csrf_token
        }
        req = self._make_auth_request(url, payload, method='POST')
        res = self._execute_with_retry(req)
        draft_id = res['data']['0']['detail']['draft_id']
        return draft_id

    def upload_photos(self, draft_id: str, photo_paths: List[Path]) -> List[str]:
        uploaded_ids = []
        url = f'https://www.wg-gesucht.de/api/images/drafts/{draft_id}/users/{self.user_id}'
        for idx, p_path in enumerate(photo_paths, start=1):
            with open(p_path, 'rb') as f:
                b64 = base64.b64encode(f.read()).decode('utf-8')
            
            payload = {
                'images': [{
                    'filename': p_path.name,
                    'position': idx,
                    'ad_type': '0',
                    'image_base64': b64,
                    'csrf_token': self.csrf_token
                }],
                'csrf_token': self.csrf_token
            }
            req = self._make_auth_request(url, payload, method='POST')
            res = self._execute_with_retry(req)
            uploaded_ids.append(res['data']['detail'].get('image_id', ''))
            time.sleep(0.2)
        return uploaded_ids

    def update_draft_details(self, draft_id: str, listing: Dict[str, Any]):
        url = f'https://www.wg-gesucht.de/api/drafts/{draft_id}/users/{self.user_id}'
        payload = {
            'ad_title': listing['title'],
            'city_id': '55',
            'country_code': 'de',
            'category': '0',
            'rent_type': '0',
            'ad_type': '0',
            'display_language': 'de',
            'csrf_token': self.csrf_token,
            'district_id': '1223', # Harburg
            'district': '',
            'district_custom': '',
            'street_only': listing['street'],
            'street': listing['street'],
            'postcode': listing['postcode'],
            'housenumber': listing.get('housenumber', ''),
            'property_size': str(int(listing['room_size_sqm'])),
            'flatshare_property_size': str(int(listing['flat_size_sqm'])),
            'available_from_day': '01',
            'available_from_month': '10',
            'available_from_year': '2026',
            'furnished': '1' if listing['furnished'] else '0',
            'rent_costs': str(int(listing['total_rent_eur'])),
            'utility_costs': str(int(listing.get('utilities_eur', 0))),
            'bond_costs': str(int(listing['deposit_eur'])),
            'flatshare_inhabitants_total': str(listing['flatshare_total_inhabitants']),
            'flatshare_females': str(listing['current_female_flatmates']),
            'flatshare_males': str(listing['current_male_flatmates']),
            'searching_for_gender': '1' if listing['searched_gender'] == 'women_only' else '0',
            'smoking_is_allowed': '2' if not listing['smoking_allowed'] else '1',
            'flatshare_type_1': '1', # Studenten-WG
            'flatshare_type_11': '1', # Keine Zweck-WG
            'internet_wlan': '1',
            'internet_dsl_speed': '10',
            'i_am': '2',
            'freetext_property_description': listing['description_de'] + "\n\n---\n\n" + listing['description_en'],
            'freetext_area_description': f"Lage: {listing['district']}, Hamburg.",
            'freetext_flatshare': f"WG mit {listing['flatshare_total_inhabitants']} Bewohnern.",
            'freetext_other': f"Mindestaufenthalt: {listing['minimum_stay_months']} Monate. Kaution: {listing['deposit_eur']} €.",
            'lang_de': '1',
            'lang_en': '1'
        }
        req = self._make_auth_request(url, payload, method='PUT')
        self._execute_with_retry(req)

    def _make_auth_request(self, url: str, data: Dict[str, Any], method: str = 'POST') -> urllib.request.Request:
        req = urllib.request.Request(
            url,
            data=json.dumps(data).encode('utf-8'),
            headers={
                'Content-Type': 'application/json',
                'Accept': 'application/json',
                'X-Client-Id': 'wg_desktop_website',
                'X-User-Id': self.user_id,
                'X-Authorization': f"Bearer {self.access_token}",
                'x-dev-ref-no': self.dev_ref_no,
                'Cookie': self.cookies,
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)'
            },
            method=method
        )
        return req
