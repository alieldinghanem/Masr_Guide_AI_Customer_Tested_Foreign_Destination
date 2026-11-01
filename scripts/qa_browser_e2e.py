"""Real Chromium smoke tests for the compiled React app and the dependency-free demo.

Prerequisites:
  pip install playwright && python -m playwright install chromium
  cd frontend && npm ci && npm run build
  cd ../backend && python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
  cd .. && FRONTEND_URL=http://127.0.0.1:8000 python scripts/qa_browser_e2e.py

Never claim React E2E passed when this script only executed the /demo tests.
"""
import os
import re
import shutil
from playwright.sync_api import sync_playwright, expect

URL = os.getenv('FRONTEND_URL', 'http://127.0.0.1:8000').rstrip('/')


def test_demo(browser):
    context = browser.new_context(viewport={'width': 1280, 'height': 800})
    page = context.new_page()
    errors = []
    page.on('pageerror', lambda error: errors.append(str(error)))
    try:
        page.goto(f'{URL}/demo', wait_until='domcontentloaded', timeout=20000)
        expect(page.locator('#headline')).to_contain_text('Egypt trip')
        page.locator('#question').fill('I am visiting Egypt for two weeks: first week for ancient history in Cairo and Luxor, second week for Red Sea beaches in Hurghada')
        page.locator('#send').click()
        expect(page.locator('#days details.day')).to_have_count(14, timeout=25000)
        expect(page.locator('#export')).to_be_enabled()
        page.locator('#question').fill('Replace Hurghada with Sharm El Sheikh')
        page.locator('#send').click()
        expect(page.locator('#days details.day').last).to_contain_text('Sharm El Sheikh', timeout=25000)
        page.locator('#reset').click()
        expect(page.locator('#days details.day')).to_have_count(0)
        assert not errors, f'Demo JavaScript errors: {errors}'
        print('PASS demo: actual Chromium chat, 14-day plan, edit, reset')
    finally:
        context.close()


def test_react(browser, label, width, height):
    context = browser.new_context(viewport={'width': width, 'height': height})
    page = context.new_page()
    errors = []
    page.on('pageerror', lambda error: errors.append(str(error)))
    try:
        page.goto(f'{URL}/#/home', wait_until='domcontentloaded', timeout=20000)
        expect(page.locator('.site-header')).to_be_visible(timeout=15000)
        # A fresh production build must include the actual React bundle, never
        # a fallback response containing a non-mounted empty #root.
        expect(page.locator('.site-header .nav-actions')).to_be_visible()
        print(f'PASS {label}: React application mounts')
        # Current product navigation: chat is the homepage, not a marketing
        # landing page; historical and beach collections are independent.
        expect(page.locator('.mg-chat-home .chat-panel')).to_be_visible()
        if width <= 620:
            expect(page.locator('.mg-mobile-tabs')).to_be_visible()
        page.goto(f'{URL}/#/heritage', wait_until='domcontentloaded')
        expect(page.locator('.mg-category-grid .mg-place-card').first).to_be_visible(timeout=15000)
        expect(page.locator('.mg-category-grid .mg-place-card')).to_have_count(31, timeout=15000)
        page.goto(f'{URL}/#/coast', wait_until='domcontentloaded')
        expect(page.locator('.mg-category-grid .mg-place-card')).to_have_count(7, timeout=15000)
        assert page.get_by_text('Bibliotheca Alexandrina').count() == 0, 'Cultural venues must not be presented as beaches'
        page.goto(f'{URL}/#/home', wait_until='domcontentloaded')
        page.locator('.lang-toggle').click()
        expect(page.locator('html')).to_have_attribute('dir', 'rtl')
        expect(page.locator('.mg-chat-home .chat-panel')).to_be_visible()
        page.locator('.lang-toggle').click()
        expect(page.locator('html')).to_have_attribute('dir', 'ltr')
        print(f'PASS {label}: chat homepage, heritage, beaches, AR/EN and mobile nav')

        page.goto(f'{URL}/#/explore', wait_until='domcontentloaded')
        field = page.get_by_role('textbox', name='Search places')
        expect(field).to_be_visible(timeout=15000)
        field.fill('Karnak')
        expect(page.get_by_text('Karnak Temple Complex').first).to_be_visible(timeout=15000)
        print(f'PASS {label}: catalog and search')

        page.goto(f'{URL}/#/planner', wait_until='domcontentloaded')
        days = page.get_by_label('Number of days')
        expect(days).to_be_visible(timeout=15000)
        days.fill('2')
        page.get_by_role('button', name='Generate my itinerary').click()
        expect(page.locator('.day-card')).to_have_count(2, timeout=20000)
        page.get_by_role('button', name='Save this plan').click()
        expect(page.get_by_role('button', name='Saved to this browser')).to_be_visible(timeout=5000)
        print(f'PASS {label}: create and save real itinerary')

        page.goto(f'{URL}/#/guide', wait_until='domcontentloaded')
        prompt = page.get_by_role('textbox', name='Ask the tour guide')
        expect(prompt).to_be_visible(timeout=15000)
        prompt.fill('Tell me about Karnak Temple')
        page.get_by_role('button', name='Send message').click()
        expect(page.locator('.msg.assistant')).to_have_count(1, timeout=25000)
        prompt.fill('I am visiting Egypt for two weeks: first week for history in Cairo and Luxor, second week for Red Sea beaches in Hurghada')
        page.get_by_role('button', name='Send message').click()
        expect(page.locator('.consult-day')).to_have_count(14, timeout=25000)
        print(f'PASS {label}: offline chat and conversational 14-day plan')

        # Navigation should preserve conversation in an active browser session.
        page.goto(f'{URL}/#/explore', wait_until='domcontentloaded')
        page.goto(f'{URL}/#/guide', wait_until='domcontentloaded')
        expect(page.locator('.msg.user')).to_have_count(2, timeout=15000)
        assert not errors, f'{label} React runtime errors: {errors}'
        assert page.evaluate('document.documentElement.scrollWidth <= window.innerWidth + 2'), f'{label}: horizontal overflow'
        print(f'PASS {label}: session context, no runtime errors or horizontal overflow')
        # Register a unique ephemeral test traveler and persist a generated trip.
        # This verifies frontend -> FastAPI -> SQLite, not just localStorage.
        page.goto(f'{URL}/#/account', wait_until='domcontentloaded')
        page.get_by_role('button', name='Create an account?').click()
        from uuid import uuid4
        demo_email = f'qa-{uuid4().hex[:12]}@example.org'
        page.get_by_label('Email').fill(demo_email)
        page.get_by_label('Password').fill('QA-test-account-Password-2026')
        page.get_by_role('button', name='Register').click()
        expect(page.get_by_text(f'Signed in as')).to_be_visible(timeout=15000)
        page.goto(f'{URL}/#/planner', wait_until='domcontentloaded')
        page.get_by_label('Number of days').fill('2')
        page.get_by_role('button', name='Generate my itinerary').click()
        expect(page.locator('.day-card')).to_have_count(2, timeout=20000)
        page.get_by_role('button', name='Save this plan').click()
        page.goto(f'{URL}/#/account', wait_until='domcontentloaded')
        expect(page.get_by_text('2-day itinerary available to save.')).to_be_visible(timeout=15000)
        page.get_by_role('button', name='Save to my account').click()
        expect(page.get_by_text('My Egypt Journey', exact=True).first).to_be_visible(timeout=15000)
        # A traveler must be able to revise the *same* cloud record, not create
        # duplicates. This uses the real Planner and conditional PUT If-Match.
        page.get_by_role('button', name='View').first.click()
        expect(page.get_by_text('Day 2 —')).to_be_visible(timeout=15000)
        page.get_by_role('button', name='Open in planner to edit').click()
        page.get_by_label('Number of days').fill('3')
        page.get_by_role('button', name='Generate my itinerary').click()
        expect(page.locator('.day-card')).to_have_count(3, timeout=20000)
        page.get_by_role('button', name='Save this plan').click()
        page.goto(f'{URL}/#/account', wait_until='domcontentloaded')
        page.get_by_role('button', name='View').first.click()
        page.once('dialog', lambda dialog: dialog.accept())
        with page.expect_response(lambda response: '/api/my/trips/' in response.url and
                                  response.request.method == 'PUT', timeout=15000) as cloud_update:
            page.get_by_role('button', name='Replace with my current planner itinerary').click()
        assert cloud_update.value.status == 200
        expect(page.get_by_text('Day 3 —')).to_be_visible(timeout=15000)
        assert page.get_by_role('button', name='View').count() == 1, 'Update must not create duplicate cloud trips'
        print(f'PASS {label}: saved trip revised via real conditional cloud update')
        # Account-backed favorites must persist after reload, remain scoped to
        # this visitor, and be cleared from the UI on logout. Requires the real
        # React build; the dependency-free demo cannot substitute for this.
        page.goto(f'{URL}/#/explore', wait_until='domcontentloaded')
        field = page.get_by_role('textbox', name='Search places')
        field.fill('Karnak')
        expect(page.get_by_role('button', name='Save place')).to_be_visible(timeout=15000)
        with page.expect_response(lambda response: '/api/my/favorites/karnak' in response.url and
                                  response.request.method == 'POST', timeout=15000) as favorite_write:
            page.get_by_role('button', name='Save place').click()
        assert favorite_write.value.status == 200
        expect(page.get_by_role('button', name='Saved · Remove')).to_be_visible(timeout=15000)
        page.reload(wait_until='domcontentloaded')
        page.get_by_role('textbox', name='Search places').fill('Karnak')
        expect(page.get_by_role('button', name='Saved · Remove')).to_be_visible(timeout=15000)
        page.goto(f'{URL}/#/saved', wait_until='domcontentloaded')
        expect(page.get_by_text('Synced with your travel account.')).to_be_visible(timeout=15000)
        expect(page.get_by_text('1 saved places')).to_be_visible(timeout=15000)
        print(f'PASS {label}: cloud favorites survive reload')
        page.goto(f'{URL}/#/account', wait_until='domcontentloaded')
        page.get_by_role('button', name='Sign out').click()
        expect(page.get_by_role('button', name='Sign in')).to_be_visible(timeout=15000)
        page.goto(f'{URL}/#/saved', wait_until='domcontentloaded')
        expect(page.get_by_text('0 saved places')).to_be_visible(timeout=15000)
        print(f'PASS {label}: real traveler registration, saved trip, favorites and logout')

    finally:
        context.close()


def run():
    with sync_playwright() as p:
        exe = os.getenv('BROWSER_EXECUTABLE') or shutil.which('chromium') or shutil.which('google-chrome')
        browser = p.chromium.launch(headless=True, args=['--no-sandbox'], **({'executable_path':exe} if exe else {}))
        try:
            test_demo(browser)
            # Must be the compiled React entry point served by the backend.
            test_react(browser, 'desktop', 1366, 900)
            test_react(browser, 'mobile', 390, 844)
        finally:
            browser.close()
    print('PASS: compiled React desktop/mobile E2E and quick demo')


if __name__ == '__main__':
    run()
