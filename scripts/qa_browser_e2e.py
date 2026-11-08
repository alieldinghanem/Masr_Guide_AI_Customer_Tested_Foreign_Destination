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
import json
from playwright.sync_api import sync_playwright, expect

URL = os.getenv('FRONTEND_URL', 'http://127.0.0.1:8000').rstrip('/')


def test_country_language(browser):
    # Intercept the country lookup before the browser sends a request. This
    # exercises the compiled UI without disclosing the test machine's IP.
    for country, expected, browser_locale in (
        ('EG', 'ar', 'en-US'), ('SA', 'ar', 'en-US'),
        ('US', 'en', 'ar-EG'), ('FR', 'en', 'ar-EG'),
    ):
        context = browser.new_context(locale=browser_locale)
        requests = []
        def country_reply(route):
            requests.append(route.request.url)
            route.fulfill(status=200, content_type='application/json', body=json.dumps({'country': country}))
        context.route('https://api.country.is/', country_reply)
        page = context.new_page()
        try:
            page.goto(f'{URL}/#/home', wait_until='domcontentloaded', timeout=20000)
            page.wait_for_function("code => sessionStorage.getItem('masr-guide-visitor-country-v1') === code", arg=country, timeout=10000)
            expect(page.locator('html')).to_have_attribute('lang', expected)
            expect(page.locator('html')).to_have_attribute('dir', 'rtl' if expected == 'ar' else 'ltr')
            assert len(requests) == 1, f'Expected one intercepted lookup for {country}'
            if country == 'US':
                page.locator('.lang-toggle').click()
                expect(page.locator('html')).to_have_attribute('lang', 'ar')
                page.reload(wait_until='domcontentloaded')
                expect(page.locator('html')).to_have_attribute('lang', 'ar')
                assert len(requests) == 1, 'Manual choice should skip another country lookup'
        finally:
            context.close()
    print('PASS country-language browser integration: simulated EG/SA/US/FR and saved manual choice; no third-party lookup')


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
    context.add_init_script("if (!localStorage.getItem('masr-guide-lang')) localStorage.setItem('masr-guide-lang', 'en')")
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
        chat_box = page.locator('.mg-chat-home .chat-panel').bounding_box()
        assert chat_box and abs(chat_box['x'] - (width - chat_box['width']) / 2) < 4, f'{label}: homepage chat is off center'
        if width <= 620:
            expect(page.locator('.mg-mobile-tabs')).to_be_visible()
            page.locator('.mobile-toggle').click()
        else:
            page.locator('.nav-discover').hover()
        expect(page.locator('.nav-discover-submenu')).to_be_visible()
        page.locator('.nav-discover-submenu').get_by_role('button', name='Beaches & sea').click()
        expect(page).to_have_url(re.compile(r'#\/coast$'))
        expect(page.get_by_role('heading', name='Beaches & coastal escapes')).to_be_visible()
        expect(page.locator('.mg-discovery-nav').get_by_role('link', name='History & heritage')).to_be_visible()
        page.goto(f'{URL}/#/heritage', wait_until='domcontentloaded')
        expect(page.locator('.mg-category-grid .mg-place-card').first).to_be_visible(timeout=15000)
        assert [name.strip() for name in page.locator('.mg-category-grid .mg-place-card h2').all_text_contents()[:3]] == [
            'Pyramids of Giza', 'Grand Egyptian Museum', 'Bab Zuwayla',
        ]
        assert page.locator('.mg-religious-group h3').all_text_contents() == ['Mosques', 'Churches & monasteries', 'Synagogues']
        expect(page.locator('.mg-religious-group').last).to_contain_text('Ben Ezra Synagogue')
        # Real Chromium geometry (not jsdom): mobile cards must be readable,
        # one per row, with a generous image and 44px touch targets.
        if width <= 620:
            for phone_width in (360, 390, 430):
                page.set_viewport_size({'width': phone_width, 'height': height})
                cards = page.locator('.mg-category-grid .mg-place-card')
                first = cards.nth(0).bounding_box()
                second = cards.nth(1).bounding_box()
                image = cards.nth(0).locator('.mg-place-photo').bounding_box()
                assert first and second and image, 'Mobile photo cards must have layout boxes'
                assert abs(first['x'] - second['x']) < 2, f'Cards not single-column at {phone_width}px'
                assert second['y'] > first['y'], f'Cards overlap at {phone_width}px'
                assert image['height'] >= 170, f'Photo cropped into a narrow strip at {phone_width}px'
                action = cards.nth(0).locator('.mg-place-actions button').last.bounding_box()
                assert action and action['width'] >= 44 and action['height'] >= 44, 'Touch target too small'
                assert page.evaluate('document.documentElement.scrollWidth <= window.innerWidth + 2'), f'Horizontal overflow at {phone_width}px'
            focus = page.locator('.mg-place-card').filter(has_text='Mosque of Ahmad Ibn Tulun')
            expect(focus.locator('img')).to_have_css('object-position', '50% 67%')
            page.set_viewport_size({'width': width, 'height': height})
            print('PASS mobile imagery: 360/390/430px single column, crop, tap targets and overflow')
        page.goto(f'{URL}/#/coast', wait_until='domcontentloaded')
        expect(page.locator('.mg-coastal-guides')).to_be_visible(timeout=15000)
        expect(page.locator('.mg-coastal-guides-grid > article')).to_have_count(17)
        assert page.locator('.mg-coast-group').count() == 0, 'Coastal places must appear in one list'
        assert page.get_by_role('link', name='Destination source').count() == 0
        assert page.locator('.mg-coastal-guide').count() == 10
        photos = page.locator('.mg-coastal-guide-photo')
        expect(photos).to_have_count(10)
        for photo in photos.all():
            photo.scroll_into_view_if_needed()
            photo.evaluate('(image) => image.decode()')
            assert photo.evaluate('(image) => image.naturalWidth >= 600'), 'Beach destination photo did not load'
        assert page.locator('.mg-coastal-photo-credit').count() == 10
        assert page.locator('.mg-coastal-guides-grid .mg-place-card').count() == 7
        assert page.get_by_text('Bibliotheca Alexandrina').count() == 0, 'Cultural venues must not be presented as beaches'
        assert page.get_by_text('Citadel of Qaitbay').count() == 0, 'Historic fortress must appear under heritage, not beaches'
        assert page.get_by_text('Montaza Gardens').count() == 0, 'Seaside gardens are not a beach activity'
        page.get_by_role('button', name='More details about Marsa Alam').click()
        expect(page).to_have_url(re.compile(r'#/coast/marsa-alam$'))
        expect(page.get_by_role('heading', name='Marsa Alam', exact=True)).to_be_visible()
        expect(page.get_by_role('heading', name='Visitor comments')).to_be_visible()
        page.get_by_role('button', name='Beaches & coastal places').click()
        expect(page).to_have_url(re.compile(r'#/coast$'))
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
        expect(page.locator('.place-row')).to_have_count(53)
        expect(page.locator('.place-row .place-mini img')).to_have_count(53)
        if width > 780:
            photo_sizes = page.locator('.place-row .place-mini img').evaluate_all("""async images =>
              Promise.all(images.map(async image => {
                image.loading = 'eager'
                await image.decode()
                return { source: image.getAttribute('src'), width: image.naturalWidth }
              }))""")
            assert len(photo_sizes) == 53 and all(photo['source'].startswith('/assets/places/') and photo['width'] >= 300 for photo in photo_sizes), 'Catalog thumbnails must load from bundled local files'
        assert page.locator('.mg-place-group-heading').all_text_contents() == [
            'History & museums', 'Beaches & sea', 'Nature, culture & more',
            'Historic mosques', 'Churches & monasteries', 'Synagogues',
        ]
        expect(page.locator('.place-row').filter(has_text='Citadel of Qaitbay')).to_have_count(1)
        if width <= 780:
            assert page.locator('.place-row').first.bounding_box()['y'] < height - 80, 'First place hidden below mobile navigation'
        field.fill('Karnak')
        expect(page.get_by_text('Karnak Temple Complex').first).to_be_visible(timeout=15000)
        if width <= 780:
            page.locator('.place-row').first.click()
            page.wait_for_function("document.querySelector('.place-detail').getBoundingClientRect().top < window.innerHeight", timeout=5000)
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
        prompt.fill('We want history and beaches with our kids, at an easy pace')
        page.get_by_role('button', name='Send message').click()
        expect(page.locator('.msg.assistant')).to_have_count(1, timeout=25000)
        expect(page.locator('.msg.assistant')).to_contain_text('How many days')
        prompt.fill('Seven days')
        page.get_by_role('button', name='Send message').click()
        expect(page.locator('.consult-days > .consult-day')).to_have_count(7, timeout=25000)
        expect(page.locator('.msg.assistant').last).to_contain_text('Cairo')
        expect(page.locator('.msg.assistant').last).to_contain_text('Hurghada')
        page.locator('.chat-clear').click()
        expect(page.locator('.consult-days > .consult-day')).to_have_count(0)
        print(f'PASS {label}: preferences survive duration follow-up in the real chat')

        prompt.fill('Tell me about Karnak Temple')
        page.get_by_role('button', name='Send message').click()
        expect(page.locator('.msg.assistant')).to_have_count(1, timeout=25000)
        prompt.fill('I am visiting Egypt for two weeks: first week for history in Cairo and Luxor, second week for Red Sea beaches in Hurghada')
        page.get_by_role('button', name='Send message').click()
        expect(page.locator('.consult-days > .consult-day')).to_have_count(14, timeout=25000)
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
        page.get_by_role('button', name='Create an account').click()
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
        page.get_by_role('button', name='View', exact=True).first.click()
        expect(page.get_by_text('Day 2 —')).to_be_visible(timeout=15000)
        page.get_by_role('button', name='Open in planner to edit').click()
        page.get_by_label('Number of days').fill('3')
        page.get_by_role('button', name='Generate my itinerary').click()
        expect(page.locator('.day-card')).to_have_count(3, timeout=20000)
        page.get_by_role('button', name='Save this plan').click()
        page.goto(f'{URL}/#/account', wait_until='domcontentloaded')
        page.get_by_role('button', name='View', exact=True).first.click()
        page.once('dialog', lambda dialog: dialog.accept())
        with page.expect_response(lambda response: '/api/my/trips/' in response.url and
                                  response.request.method == 'PUT', timeout=15000) as cloud_update:
            page.get_by_role('button', name='Replace with my current planner itinerary').click()
        assert cloud_update.value.status == 200
        expect(page.get_by_text('Day 3 —')).to_be_visible(timeout=15000)
        assert page.get_by_role('button', name='View', exact=True).count() == 1, 'Update must not create duplicate cloud trips'
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



def test_mobile_photo_layout(browser):
    """Isolate customer-visible photo UX from unrelated account/AI workflows."""
    context = browser.new_context(viewport={'width': 390, 'height': 844})
    context.add_init_script("if (!localStorage.getItem('masr-guide-lang')) localStorage.setItem('masr-guide-lang', 'en')")
    page = context.new_page()
    try:
        page.goto(f'{URL}/#/heritage', wait_until='domcontentloaded', timeout=20000)
        cards = page.locator('.mg-category-grid .mg-place-card')
        expect(cards.nth(1)).to_be_visible(timeout=15000)
        assert [name.strip() for name in cards.locator('h2').all_text_contents()[:3]] == [
            'Pyramids of Giza', 'Grand Egyptian Museum', 'Bab Zuwayla',
        ], 'The requested heritage sites must lead the catalog'
        for phone_width in (360, 390, 430):
            page.set_viewport_size({'width': phone_width, 'height': 844})
            first, second = cards.nth(0).bounding_box(), cards.nth(1).bounding_box()
            photo = cards.nth(0).locator('.mg-place-photo').bounding_box()
            tap = cards.nth(0).locator('.mg-place-actions button').last.bounding_box()
            assert first and second and photo and tap, f'Missing photo/card at {phone_width}'
            assert abs(first['x'] - second['x']) < 2 and second['y'] > first['y'], 'Mobile must have one card per row'
            assert photo['height'] >= 170, f'Photo area too short at {phone_width}'
            assert tap['width'] >= 44 and tap['height'] >= 44, f'Touch area too small at {phone_width}'
            assert page.evaluate('document.documentElement.scrollWidth <= window.innerWidth + 2'), 'Horizontal scrolling'
        tulun = cards.filter(has_text='Mosque of Ahmad Ibn Tulun')
        expect(tulun.locator('img')).to_have_css('object-position', '50% 67%')
        assert tulun.locator('img').get_attribute('src') == '/assets/places/ibn-tulun-mosque.jpg'
        page.locator('.lang-toggle').click()
        expect(page.locator('html')).to_have_attribute('dir', 'rtl')
        assert page.evaluate('document.documentElement.scrollWidth <= window.innerWidth + 2'), 'RTL overflow'
        page.goto(f'{URL}/#/coast', wait_until='domcontentloaded')
        coast = page.locator('.mg-coastal-guides-grid .mg-place-card')
        expect(page.locator('.mg-coastal-guides')).to_be_visible(timeout=15000)
        expect(coast.nth(1)).to_be_visible(timeout=15000)
        assert page.locator('.mg-coastal-guide').count() == 10, 'All requested coastal destinations must be shown'
        assert coast.count() == 7
        assert coast.nth(0).locator('h2').inner_text() == 'خليج نعمة'
        assert abs(coast.nth(0).bounding_box()['x'] - coast.nth(1).bounding_box()['x']) < 2, 'Coast mobile cards must stack'
        print('PASS mobile photo QA: 360/390/430px, Arabic RTL, unique Ibn Tulun framing, heritage/coast')
    finally:
        context.close()


def test_visitor_ratings(browser):
    """Exercise an account-owned vote, persistence across reload, and rating order."""
    context = browser.new_context(viewport={'width': 1366, 'height': 900})
    context.add_init_script("localStorage.setItem('masr-guide-lang', 'en')")
    page = context.new_page()
    try:
        from uuid import uuid4
        page.goto(f'{URL}/#/account', wait_until='domcontentloaded', timeout=20000)
        page.get_by_role('button', name='Create an account').click()
        page.get_by_label('Email').fill(f'rating-qa-{uuid4().hex[:12]}@example.org')
        page.get_by_label('Password').fill('QA-test-account-Password-2026')
        page.get_by_role('button', name='Register').click()
        expect(page.get_by_text('Signed in as')).to_be_visible(timeout=15000)
        page.goto(f'{URL}/#/coast', wait_until='domcontentloaded', timeout=20000)
        marsa = page.locator('.mg-coastal-guide').filter(has_text='Marsa Alam')
        expect(marsa).to_be_visible(timeout=15000)
        marsa.get_by_role('button', name='Rate Marsa Alam 5 out of 5').click()
        expect(marsa.locator('.mg-rating-yours')).to_contain_text('Your rating: 5 / 5')
        page.reload(wait_until='domcontentloaded')
        marsa = page.locator('.mg-coastal-guide').filter(has_text='Marsa Alam')
        expect(marsa.locator('.mg-rating-yours')).to_contain_text('Your rating: 5 / 5', timeout=15000)
        page.get_by_role('combobox', name='Sort by').select_option('rated')
        expect(page.locator('.mg-coastal-guide h3').first).to_have_text('Marsa Alam')
        page.goto(f'{URL}/#/reviews', wait_until='domcontentloaded')
        expect(page.locator('.reviews-rank li').first).to_contain_text('Marsa Alam', timeout=15000)
        print('PASS visitor ratings: real vote, reload persistence and highest-rated sort')
    finally:
        context.close()


def test_photo_details_and_comments(browser):
    context = browser.new_context(viewport={'width': 390, 'height': 844})
    context.add_init_script("localStorage.setItem('masr-guide-lang', 'en')")
    page = context.new_page()
    try:
        page.goto(f'{URL}/#/heritage', wait_until='domcontentloaded', timeout=20000)
        photo = page.get_by_role('button', name='More details about Pyramids of Giza')
        expect(photo).to_be_visible(timeout=15000)
        photo.click()
        expect(page).to_have_url(re.compile(r'#/place/giza-pyramids$'))
        expect(page.locator('.place-full-photo img')).to_be_visible()
        expect(page.get_by_role('heading', name='Rate this place')).to_be_visible()
        expect(page.get_by_role('heading', name=re.compile('Visitor comments'))).to_be_visible()
        assert page.get_by_role('textbox', name='Display name').count() == 0
        assert page.get_by_role('button', name='Post comment').count() == 0
        page.locator('.mg-visitor-comments').get_by_role('button', name='Sign in').click()
        expect(page).to_have_url(re.compile(r'#/account$'))
        from uuid import uuid4
        page.get_by_role('button', name='Create an account').click()
        page.get_by_label('Email').fill(f'comment-qa-{uuid4().hex[:12]}@example.org')
        page.get_by_label('Password').fill('QA-test-account-Password-2026')
        page.get_by_role('button', name='Register').click()
        expect(page).to_have_url(re.compile(r'#/place/giza-pyramids$'))
        page.get_by_role('textbox', name='Your comment about this place').fill('The photo and place details are helpful.')
        page.get_by_role('button', name='Post comment').click()
        expect(page.locator('.mg-comment-list')).to_contain_text('The photo and place details are helpful.')
        page.locator('.place-back').click()
        expect(page).to_have_url(re.compile(r'#/heritage$'))
        page.get_by_role('button', name='More details about Pyramids of Giza').click()
        page.reload(wait_until='domcontentloaded')
        expect(page.locator('.mg-comment-list')).to_contain_text('The photo and place details are helpful.', timeout=15000)
        page.locator('.place-back').click()
        expect(page).to_have_url(re.compile(r'#/explore$'))
        expect(page.locator('.detail-photo')).to_be_visible(timeout=15000)
        print('PASS place details: photo click, top stars, account-gated comment, reload and illustrated Explore panel')
    finally:
        context.close()


def run():
    with sync_playwright() as p:
        exe = os.getenv('BROWSER_EXECUTABLE') or shutil.which('chromium') or shutil.which('google-chrome')
        browser = p.chromium.launch(headless=True, args=['--no-sandbox'], **({'executable_path':exe} if exe else {}))
        try:
            test_country_language(browser)
            test_demo(browser)
            test_mobile_photo_layout(browser)
            test_visitor_ratings(browser)
            test_photo_details_and_comments(browser)
            # Must be the compiled React entry point served by the backend.
            test_react(browser, 'desktop', 1366, 900)
            test_react(browser, 'mobile', 390, 844)
        finally:
            browser.close()
    print('PASS: compiled React desktop/mobile E2E and quick demo')


if __name__ == '__main__':
    run()
