"""Phone/tablet test on 6 device sizes with touch emulation (needs: pip install playwright).
Start the app (python app.py), add a draft (click Try demo), then:  python e2e/mobile_check.py"""
from playwright.sync_api import sync_playwright
SIZES = [("iPhone SE",375,667,2),("iPhone 13",390,844,3),("Pixel 7",412,915,2.6),("Small 320",320,568,2),
         ("Landscape",844,390,3),("iPad mini",768,1024,2)]
fails = []
def check(tag, name, cond, extra=""):
    if not cond: fails.append(f"{tag}: {name} {extra}")
    print(("  ok   " if cond else "  FAIL ")+name, extra if not cond else "")

with sync_playwright() as p:
    b = p.chromium.launch(headless=True)
    for tag, w, h, dpr in SIZES:
        print(f"== {tag} {w}x{h}")
        ctx = b.new_context(viewport={"width":w,"height":h}, device_scale_factor=dpr, is_mobile=True, has_touch=True)
        pg = ctx.new_page(); errs=[]; pg.on("pageerror", lambda e: errs.append(str(e)))
        pg.goto("http://localhost:5000/"); pg.wait_for_selector(".item"); pg.wait_for_timeout(400)
        check(tag,"no horizontal scroll", not pg.evaluate("document.documentElement.scrollWidth>innerWidth"))
        phone = w <= 820 or (h <= 500 and w <= 1000)
        if phone:
            vis = lambda sel: pg.locator(sel).first.is_visible()
            check(tag,"tab strip visible", vis(".mtabs"))
            sb = pg.locator(".mtabs").bounding_box(); cb = pg.locator(".content").bounding_box()
            check(tag,"tab strip spans full width", sb["width"] >= cb["width"]-2*14-4, f"strip {sb['width']:.0f} content {cb['width']:.0f}")
            ws = pg.evaluate("[...document.querySelectorAll('.mtabs button')].map(b=>b.getBoundingClientRect().width)")
            check(tag,"3 equal tab buttons", max(ws)-min(ws) < 2 and min(ws) > sb["width"]/3-12, ws)
            lw = pg.locator(".list").bounding_box()["width"]; iw = pg.locator(".item").first.bounding_box()["width"]
            check(tag,"single draft fills the queue row", iw >= lw-30, f"item {iw:.0f} list {lw:.0f}")
            check(tag,"text tab shows only editor", vis(".editor") and not vis(".preview") and not vis(".actions"))
            pg.fill("#text", "edit survives tab switching")
            pg.tap('.mtabs button[data-t="preview"]')
            check(tag,"preview tab shows only preview", vis(".preview") and not vis(".editor") and not vis(".actions"))
            check(tag,"live preview has edited text", "edit survives" in pg.inner_text("#prev"))
            pg.tap('.mtabs button[data-t="actions"]')
            check(tag,"actions tab shows only actions", vis(".actions") and not vis(".editor") and not vis(".preview"))
            pg.tap('.mtabs button[data-t="text"]')
            check(tag,"unsaved edit kept after switching tabs", pg.input_value("#text")=="edit survives tab switching")
            fs = pg.evaluate("getComputedStyle(document.querySelector('#text')).fontSize")
            check(tag,"textarea font >= 16px (no iOS zoom)", float(fs[:-2])>=16, fs)
            # nav = bottom bar, content not hidden behind it
            nav = pg.locator("#nav").bounding_box()
            check(tag,"nav pinned to bottom", abs((nav["y"]+nav["height"])-h)<2 and nav["width"]>=w-2, nav)
            pg.tap('.mtabs button[data-t="actions"]'); pg.evaluate("scrollTo(0, document.body.scrollHeight)"); pg.wait_for_timeout(300)
            last = pg.evaluate("Math.max(...[...document.querySelectorAll('.actions > *')].map(e=>e.getBoundingClientRect().bottom))")
            check(tag,"last action not hidden behind nav", last <= nav["y"]+1, f"last={last:.0f} nav={nav['y']:.0f}")
            # queue is a swipe row
            lst = pg.evaluate("(()=>{const l=document.querySelector('.list');const c=getComputedStyle(l);return [c.display,c.scrollSnapType]})()")
            check(tag,"queue is horizontal snap row", lst[0]=="flex" and "x" in lst[1], lst)
            pg.tap('.mtabs button[data-t="preview"]')
            ib = pg.evaluate("[...document.querySelectorAll('.field input, .field textarea')].every(e=>parseFloat(getComputedStyle(e).fontSize)>=16)")
            check(tag,"image fields font >= 16px", ib)
            pg.tap('.mtabs button[data-t="actions"]')
            if tag in ("iPhone 13","Landscape"):
                for t in ("text","preview","actions"):
                    pg.tap(f'.mtabs button[data-t="{t}"]'); pg.evaluate("scrollTo(0,0)"); pg.wait_for_timeout(200)
                    pg.locator(".mtabs").scroll_into_view_if_needed()
                    pg.screenshot(path=f"/tmp/t-{tag.replace(' ','')}-{t}.png")
        else:
            check(tag,"tablet: tabs hidden, tiles stack", not pg.locator(".mtabs").first.is_visible())
        # tap targets (visible buttons / links)
        pg.tap('.mtabs button[data-t="actions"]') if phone else None
        small = pg.evaluate("""[...document.querySelectorAll('button,a.btn,input,textarea')]
            .filter(e=>e.offsetParent!==null && !e.closest('.item'))
            .map(e=>[e.id||e.className||e.tagName, Math.round(e.getBoundingClientRect().height)])
            .filter(([_,hh])=>hh<40)""")
        check(tag,"all visible controls >= 40px tall", not small, small)
        # toast sits above the nav
        pg.evaluate("document.getElementById('toast').textContent='hello';document.getElementById('toast').classList.add('show')")
        pg.wait_for_timeout(350)
        tb = pg.locator("#toast").bounding_box(); nv = pg.locator("#nav").bounding_box()
        if phone: check(tag,"toast above nav", tb["y"]+tb["height"] <= nv["y"]+1, f"toast bottom {tb['y']+tb['height']:.0f} nav top {nv['y']:.0f}")
        check(tag,"no JS errors", not errs, errs)
        pg.evaluate("document.getElementById('toast').classList.remove('show')")
        pg.tap('.mtabs button[data-t="text"]') if phone else None
        pg.evaluate("scrollTo(0,0)")
        pg.screenshot(path=f"/tmp/m-{tag.replace(' ','')}.png", full_page=False)
        ctx.close()
    b.close()
print("\nFAILED:" if fails else "\nALL PASSED"); [print(" -",f) for f in fails]
