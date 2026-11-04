"""Manual live locale check from the current runner's real network location.

This contacts api.country.is twice (preflight and in Chrome) and must only run
with authorization to disclose that runner's public IP to the service.
The output contains a country code, never the IP address.
"""
import json
import os
from urllib.request import Request, urlopen

from playwright.sync_api import expect, sync_playwright


COUNTRY_API = 'https://api.country.is/'
SITE = os.getenv('LIVE_SITE_URL', 'https://masr-guide-ai-customer-tested-foreign-8aro.onrender.com').rstrip('/')
ARAB_COUNTRIES = {
    'AE', 'BH', 'DJ', 'DZ', 'EG', 'IQ', 'JO', 'KM', 'KW', 'LB', 'LY',
    'MA', 'MR', 'OM', 'PS', 'QA', 'SA', 'SD', 'SO', 'SY', 'TN', 'YE',
}


def lookup_country():
    request = Request(COUNTRY_API, headers={'User-Agent': 'MasrGuideAI-Manual-Geo-QA/1.0'})
    with urlopen(request, timeout=20) as response:
        country = json.load(response).get('country', '')
    if not isinstance(country, str) or len(country) != 2 or not country.isalpha():
        raise AssertionError('Country lookup did not return an ISO alpha-2 country code')
    return country.upper()


def main():
    preflight = lookup_country()
    expected = 'ar' if preflight in ARAB_COUNTRIES else 'en'
    # Oppose the location result so browser-language fallback cannot fake a pass.
    browser_locale = 'en-US' if expected == 'ar' else 'ar-EG'
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True, executable_path=os.getenv('BROWSER_EXECUTABLE') or None)
        context = browser.new_context(locale=browser_locale)
        page = context.new_page()
        country_requests = []
        page.on('request', lambda request: country_requests.append(request.url) if request.url.startswith(COUNTRY_API) else None)
        with page.expect_response(lambda response: response.url.startswith(COUNTRY_API), timeout=60000) as pending:
            page.goto(f'{SITE}/#/home', wait_until='domcontentloaded', timeout=60000)
        result = pending.value
        assert result.status == 200, f'Browser country lookup HTTP {result.status}'
        detected = result.json().get('country', '').upper()
        assert detected == preflight, f'Browser egress country {detected} differs from preflight {preflight}'
        page.wait_for_function("country => sessionStorage.getItem('masr-guide-visitor-country-v1') === country", arg=detected, timeout=12000)
        expect(page.locator('html')).to_have_attribute('lang', expected)
        expect(page.locator('html')).to_have_attribute('dir', 'rtl' if expected == 'ar' else 'ltr')
        assert len(country_requests) == 1
        print(f'PASS live country={detected}: browser locale={browser_locale}, site language={expected}')

        page.locator('.lang-toggle').click()
        manual = 'en' if expected == 'ar' else 'ar'
        expect(page.locator('html')).to_have_attribute('lang', manual)
        page.reload(wait_until='domcontentloaded')
        expect(page.locator('html')).to_have_attribute('lang', manual)
        assert len(country_requests) == 1, 'Manual choice should prevent another lookup'
        print(f'PASS manual language={manual} persists after reload')
        context.close()
        browser.close()


if __name__ == '__main__':
    main()
