"""Render checked-in social artwork with development-only Playwright/Chromium."""
from functools import partial
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
from threading import Thread
from playwright.sync_api import sync_playwright
root=Path(__file__).resolve().parent.parent
server=ThreadingHTTPServer(('127.0.0.1',0),partial(SimpleHTTPRequestHandler,directory=str(root)))
Thread(target=server.serve_forever,daemon=True).start()
try:
    with sync_playwright() as p:
        browser=p.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox'])
        page=browser.new_page(viewport={'width':1200,'height':630},device_scale_factor=1)
        page.goto(f'http://127.0.0.1:{server.server_port}/scripts/share-preview.html')
        page.evaluate('document.fonts.ready')
        page.wait_for_function('Array.from(document.images).every(i=>i.complete&&i.naturalWidth>0)')
        page.screenshot(path=str(root/'static/community/imagery/tk-zone-share.png'))
        browser.close()
finally:
    server.shutdown()
    server.server_close()
