"""Dependency-free contract checks for both Windows start helpers.

Run: python scripts/qa_local_launchers.py
These checks do not substitute for real Windows or browser E2E.
"""
from pathlib import Path
from open_local_website import healthy_backend, healthy_frontend, ROOT
from open_quick_demo import verify_demo


def run():
    index = (ROOT / 'frontend' / 'index.html').read_text(encoding='utf-8')
    demo = (ROOT / 'backend' / 'quick_demo' / 'index.html').read_text(encoding='utf-8')
    checks = {
        'backend must return ready': healthy_backend((200, '{"status":"ready"}')),
        'backend rejects 200 from unknown app': not healthy_backend((200, '{"status":"ok"}')),
        'backend rejects unreadable JSON': not healthy_backend((200, '<html>ok</html>')),
        'backend rejects 503': not healthy_backend((503, '{"status":"ready"}')),
        'frontend identifies correct Vite entry': healthy_frontend((200, index)),
        'frontend rejects unmounted template': not healthy_frontend((200, '<title>Masr Guide AI</title>')),
        'frontend rejects unknown project': not healthy_frontend((200, '<div id="root"></div><script type="module" src="/src/main.jsx"></script>')),
        'frontend rejects server errors': not healthy_frontend((502, index)),
        'demo requires live app identifiers': verify_demo((200, demo)),
        'demo rejects other pages': not verify_demo((200, '<title>Masr Guide AI</title>')),
        'demo rejects failed HTTP': not verify_demo((404, demo)),
    }
    for label, passed in checks.items():
        print(('PASS' if passed else 'FAIL') + ' ' + label)
    print(f"LOCAL LAUNCHER CONTRACTS: {sum(checks.values())}/{len(checks)} PASS")
    return 0 if all(checks.values()) else 1


if __name__ == '__main__':
    raise SystemExit(run())
