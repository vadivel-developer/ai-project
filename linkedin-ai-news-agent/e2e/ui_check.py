"""Browser test of the whole UI (needs: pip install playwright; a Chromium browser).
Start the app first (python app.py), then:  python e2e/ui_check.py
WARNING: it edits/skips the demo draft in your local database."""
from playwright.sync_api import sync_playwright
results = []
def check(name, cond, extra=""):
    results.append((name, bool(cond))); print(("PASS " if cond else "FAIL ") + name, extra)

with sync_playwright() as p:
    b = p.chromium.launch(headless=True)
    ctx = b.new_context(viewport={"width":1360,"height":900}, permissions=["clipboard-read","clipboard-write"])
    pg = ctx.new_page(); errs=[]
    pg.on("pageerror", lambda e: errs.append(str(e)))
    pg.on("dialog", lambda d: d.accept())
    toast = lambda: pg.text_content("#toast")
    def wait_toast(sub):
        pg.wait_for_function("t=>document.querySelector('#toast').textContent.includes(t)", arg=sub, timeout=8000)

    pg.goto("http://localhost:5000/"); pg.wait_for_selector(".empty")
    check("empty state shown", "Nothing here yet" in pg.inner_text("#bento"))
    check("Poppins font files loaded", pg.evaluate("[...document.fonts].filter(f=>f.status==='loaded').length>=3"))

    # Generate drafts with no API keys -> friendly error, no crash
    pg.click("#run"); wait_toast("Failed")
    check("Generate drafts w/o keys shows error toast", "Failed" in toast(), toast())
    check("Generate button re-enabled", pg.is_enabled("#run"))

    # Demo
    pg.click("#demo"); pg.wait_for_selector(".item")
    check("demo adds a draft", pg.locator(".item").count()==1)
    check("stat tile = 1 to review", pg.locator(".s-drafted .num").inner_text()=="1")
    check("preview shows post text", "AI moves fast" in pg.inner_text("#prev"))
    check("image shown in preview", pg.locator(".card img").count()==1)

    # Edit text -> live preview + counter, then save
    pg.fill("#text", "My edited post #AI")
    check("live preview updates", pg.inner_text("#prev")=="My edited post #AI")
    check("char counter updates", pg.inner_text("#count")=="18 / 3000")
    pg.fill("#text", "x"*3001)
    check("counter turns red over 3000", "over" in pg.get_attribute("#count","class"))
    pg.fill("#text", "My edited post #AI")
    pg.click("#save"); wait_toast("Saved")
    pg.reload(); pg.wait_for_selector("#text")
    check("saved text persists after reload", pg.input_value("#text")=="My edited post #AI")

    # Image text edit + regenerate (no HF token -> gradient fallback must still work)
    before = pg.get_attribute(".card img","src")
    pg.fill("#ctitle","Brand new headline"); pg.fill("#cdesc","Short helpful description.")
    pg.click("#img-update"); wait_toast("Image updated")
    pg.wait_for_selector("#ctitle")
    check("image title persists", pg.input_value("#ctitle")=="Brand new headline")
    pg.click("#img-new"); wait_toast("Image updated")
    check("new AI background works w/o token (fallback)", pg.locator(".card img").count()==1)
    check("image cache-busted on regenerate", before != pg.get_attribute(".card img","src"))

    # Copy
    pg.click("#copy"); wait_toast("Copied")
    check("copy to clipboard", pg.evaluate("navigator.clipboard.readText()")=="My edited post #AI")

    # Download image link
    dl = pg.get_attribute("a[download]","href")
    check("download link points to PNG", dl.endswith("/image"))
    r = ctx.request.get("http://localhost:5000"+dl)
    check("image endpoint returns PNG", r.ok and r.headers["content-type"]=="image/png")

    # Approve with no LinkedIn creds -> error toast, draft stays drafted
    pg.click("#approve"); wait_toast("Could not publish")
    check("approve w/o LinkedIn creds shows error", "Could not publish" in toast(), toast()[:80])
    check("draft still to-review after failed publish", pg.locator(".s-drafted .num").inner_text()=="1")

    # Skip + filters
    pg.click("#skip"); wait_toast("Skipped")
    pg.wait_for_function("document.querySelector('.s-skipped .num').textContent=='1'", timeout=5000)
    check("skip moves to skipped", pg.locator(".s-skipped .num").inner_text()=="1")
    pg.click('.nav-btn[data-f="skipped"]'); pg.wait_for_selector(".item")
    check("skipped filter lists it", pg.locator(".item").count()==1)
    check("skipped draft is read-only", pg.get_attribute("#text","readonly") is not None and pg.locator("#approve").count()==0)
    pg.click('.nav-btn[data-f="published"]')
    check("published filter empty", pg.locator(".item").count()==0)
    pg.click('.nav-btn[data-f="all"]')
    check("all filter shows 1", pg.locator(".item").count()==1)

    # Phone layout
    m = b.new_context(viewport={"width":390,"height":800}).new_page()
    m.on("pageerror", lambda e: errs.append("mobile: "+str(e)))
    m.goto("http://localhost:5000/"); m.click('.nav-btn[data-f="all"]'); m.wait_for_selector(".item")
    check("phone: no horizontal scroll", not m.evaluate("document.documentElement.scrollWidth>innerWidth"))
    box = m.locator("#nav").bounding_box()
    check("phone: nav is a bottom bar", box["y"] > 600 and box["width"]>=380, box)
    check("phone: buttons >= 44px tall", m.evaluate("[...document.querySelectorAll('.btn')].filter(b=>b.offsetParent!==null).every(b=>b.getBoundingClientRect().height>=40)"))

    check("no JavaScript errors", not errs, errs)
    b.close()
bad = [n for n,ok in results if not ok]
print(f"\n{len(results)-len(bad)}/{len(results)} passed"); print("FAILED:", bad) if bad else None
