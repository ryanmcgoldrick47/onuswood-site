#!/usr/bin/env python3
"""Build the Onus Wood static site into ./docs (GitHub Pages serves that folder).

How to rebuild: run `python3 build.py` in this folder, then commit and push.
Pages live in src/pages, products and timbers in content/products.json, shared header and footer in src/partials.
"""
import html, json, re, shutil
from pathlib import Path

ROOT = Path(__file__).parent
SRC, OUT = ROOT / "src", ROOT / "docs"
DATA = json.loads((ROOT / "content/products.json").read_text())
CREDITS = {Path(c["file"]).stem: c for c in json.loads((ROOT / "content/image-credits.json").read_text())}
TIMBERS, PRODUCTS, CATS = DATA["timbers"], DATA["products"], DATA["categories"]
SITE = "https://onuswood.com"
PARTS = {n: (SRC / "partials" / f"{n}.html").read_text() for n in ("head", "header", "footer")}
sitemap = []


def money(n):
    return f"${n:,.0f}"


def esc(s):
    return html.escape(str(s), quote=True)


def root_for(path):
    if path.endswith(".html"):
        return "/"
    return "../" * len([p for p in path.strip("/").split("/") if p])


def fill(text, values):
    return re.sub(r"\{\{(\w+)\}\}", lambda m: str(values.get(m[1], m[0])), text)


def img(name, alt, root, eager=False, cls="photo"):
    c = CREDITS[name]
    w, h = c["size"]
    load = 'fetchpriority="high"' if eager else 'loading="lazy"'
    return (f'<img class="{cls}" src="{root}images/{name}.webp" alt="{esc(alt)}" width="{w}" height="{h}" '
            f'{load} decoding="async">')


def img_tokens(text, root):
    def rep(m):
        parts = m[1].split("|")
        return img(parts[0], parts[1], root, eager=len(parts) > 2 and parts[2] == "eager")
    return re.sub(r"\{\{img:([^}]+)\}\}", rep, text)


def price_range(p):
    lows = [s["price"] for s in p["sizes"]]
    ups = list(p.get("timberUpcharge", {}).values()) or [0]
    return min(lows), max(lows) + max(ups)


def page(path, title, description, body, ogimage="/brand/og-image.jpg", jsonld="", ogtype="website", noindex=False):
    root = root_for(path)
    vals = {"path": path, "title": esc(title), "description": esc(description), "ogimage": ogimage,
            "jsonld": jsonld, "ogtype": ogtype, "root": root,
            "robots": '<meta name="robots" content="noindex">' if noindex else ""}
    body = img_tokens(fill(body, vals), root)
    doc = fill(PARTS["head"], vals) + fill(PARTS["header"], vals) + body + fill(PARTS["footer"], vals)
    if path.endswith(".html"):
        dest = OUT / path.lstrip("/")
    else:
        dest = OUT / path.strip("/") / "index.html" if path != "/" else OUT / "index.html"
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(doc)
    if not noindex:
        sitemap.append(path)


def card(p, root):
    lo, _ = price_range(p)
    dots = "".join(f'<span class="grain" style="--wood:{TIMBERS[t]["tone"]}" title="{esc(TIMBERS[t]["name"])}"></span>' for t in p["timbers"])
    data = (f'data-cat="{p["category"]}" data-timbers="{" ".join(p["timbers"])}" data-price="{lo}" data-lead="{p["leadWeeks"]}"')
    return (f'    <li {data}><a class="card" href="{root}product/{p["slug"]}/">'
            f'<div class="frame">{img(p["images"][0], p["alt"], root)}</div>'
            f'<span class="card-top"><span class="card-name">{esc(p["name"])} {esc(p["type"].lower())}</span><span class="card-price">From {money(lo)}</span></span>'
            f'<span class="card-meta">{esc(p["leadTime"])}</span>'
            f'<span class="card-dots" aria-label="Available in {len(p["timbers"])} timbers">{dots}</span></a></li>')


def jsonld_home():
    org = {"@context": "https://schema.org", "@type": "Organization", "name": "Onus Wood", "url": SITE,
           "logo": SITE + "/brand/favicon-512.png", "email": "hello@onuswood.com",
           "sameAs": ["https://instagram.com/onuswood"]}
    biz = {"@context": "https://schema.org", "@type": "LocalBusiness", "name": "Onus Wood", "url": SITE,
           "image": SITE + "/brand/og-image.jpg", "email": "hello@onuswood.com", "priceRange": "$$$",
           "address": {"@type": "PostalAddress", "addressRegion": "NSW", "addressCountry": "AU"}, "areaServed": "AU"}
    return "\n".join(f'<script type="application/ld+json">{json.dumps(x)}</script>' for x in (org, biz))


def jsonld_product(p):
    lo, hi = price_range(p)
    d = {"@context": "https://schema.org", "@type": "Product", "name": f'{p["name"]} {p["type"].lower()}',
         "description": p["short"], "brand": {"@type": "Brand", "name": "Onus Wood"},
         "image": [f'{SITE}/images/{i}.webp' for i in p["images"]], "sku": p["slug"],
         "offers": {"@type": "AggregateOffer", "priceCurrency": "AUD", "lowPrice": lo, "highPrice": hi,
                    "offerCount": len(p["sizes"]) * len(p["timbers"]), "availability": "https://schema.org/MadeToOrder"}}
    return f'<script type="application/ld+json">{json.dumps(d)}</script>'


def build_product(p):
    path = f'/product/{p["slug"]}/'
    root = root_for(path)
    up = p.get("timberUpcharge", {})
    opts = []
    for i, tid in enumerate(p["timbers"]):
        t = TIMBERS[tid]
        extra = f'<span class="swatch-extra">+{money(up[tid])}</span>' if tid in up else ""
        opts.append(f'          <label class="swatch-option"><input type="radio" name="timber" value="{tid}"'
                    f'{" checked" if i == 0 else ""}><span class="swatch grain" style="--wood:{t["tone"]}"></span>'
                    f'<span class="swatch-name">{esc(t["name"])}{extra}</span></label>')
    if len(p["sizes"]) > 1:
        sizes = "".join(f'<label class="pill"><input type="radio" name="size" value="{s["id"]}"{" checked" if i == 0 else ""}>'
                        f'<span>{esc(s["label"])}, {money(s["price"])}</span></label>' for i, s in enumerate(p["sizes"]))
        size_fs = f'<fieldset><legend>Size</legend><div class="pills">{sizes}</div></fieldset>'
    else:
        s = p["sizes"][0]
        size_fs = f'<input type="hidden" name="size" value="{s["id"]}"><p class="size-single">Size: {esc(s["label"])} ({esc(s["dims"])})</p>'
    specs = "\n".join(f'      <div><dt>{esc(k)}</dt><dd>{esc(v)}</dd></div>' for k, v in p["specs"].items())
    dims = "<br>".join(esc(s["dims"]) for s in p["sizes"])
    # gallery: extra photos first, then grain swatches of the first timbers
    thumbs = [f'      <div class="frame">{img(n, p["alt"] + ", another view", root)}</div>' for n in p["images"][1:3]]
    for tid in p["timbers"]:
        if len(thumbs) >= 3:
            break
        thumbs.append(f'      <div class="frame" role="img" aria-label="{esc(TIMBERS[tid]["name"])} grain swatch"><span class="grain" style="--wood:{TIMBERS[tid]["tone"]};display:block;width:100%;height:100%"></span></div>')
    same = [o for o in PRODUCTS if o["category"] == p["category"] and o["slug"] != p["slug"]]
    other = [o for o in PRODUCTS if o["category"] != p["category"] and o.get("featured")]
    related = "\n".join(card(o, root) for o in (same + other)[:3])
    pj = {"slug": p["slug"], "name": f'{p["name"]} {p["type"].lower()}', "sizes": p["sizes"], "upcharge": up,
          "timbers": {tid: TIMBERS[tid]["name"] for tid in p["timbers"]}, "checkoutUrl": p.get("checkoutUrl", "")}
    lo, _ = price_range(p)
    body = fill((SRC / "templates/product.html").read_text(), {
        "category": p["category"], "categoryName": CATS[p["category"]]["name"], "name": esc(p["name"]),
        "type": esc(p["type"]), "short": esc(p["short"]), "story": esc(p["story"]), "namedFor": esc(p["namedFor"]),
        "mainImage": img(p["images"][0], p["alt"], root, eager=True), "thumbs": "\n".join(thumbs),
        "fromPrice": money(lo), "firstTimberName": esc(TIMBERS[p["timbers"][0]]["name"]),
        "timberOptions": "\n".join(opts), "sizeFieldset": size_fs, "leadTime": esc(p["leadTime"]),
        "specRows": specs, "dimsList": dims, "slug": p["slug"], "related": related,
        "productJson": esc(json.dumps(pj)), "root": "{{root}}"})
    title = f'{p["name"]} {p["type"].lower()} in Australian timber: Onus Wood'
    desc = f'{p["short"]} Made in {", ".join(TIMBERS[t]["name"] for t in p["timbers"])}. From {money(lo)} including GST. {p["leadTime"]}.'
    page(path, title, desc, body, ogimage=f'/images/{p["images"][0]}.webp', jsonld=jsonld_product(p), ogtype="product")


def build_categories():
    for cid, c in CATS.items():
        path = f"/shop/{cid}/"
        root = root_for(path)
        items = [p for p in PRODUCTS if p["category"] == cid]
        others = ", ".join(f'<a class="text-link" href="{root}shop/{o}/">{CATS[o]["name"]}</a>' for o in CATS if o != cid)
        body = fill((SRC / "templates/category.html").read_text(), {
            "catName": c["name"], "catIntro": esc(c["intro"]), "catImage": img(c["image"], c["alt"], root, eager=True),
            "count": {2: "Two", 3: "Three"}.get(len(items), str(len(items))), "cards": "\n".join(card(p, root) for p in items),
            "otherLinks": others + f', or <a class="text-link" href="{root}bespoke/">bespoke</a>.', "root": "{{root}}"})
        lo = min(price_range(p)[0] for p in items)
        page(path, f'Timber {c["name"].lower()}: Onus Wood', f'{c["intro"].split(". ")[0]}. Made to order in Australian timber, from {money(lo)}.', body)


def timber_cards():
    out = []
    for t in TIMBERS.values():
        uses = [p for p in PRODUCTS if any(TIMBERS[x] is t for x in p["timbers"])]
        out.append(f'    <li class="timber-card"><span class="swatch grain" style="--wood:{t["tone"]}"></span><h3>{esc(t["name"])}</h3>'
                   f'<dl><div><dt>Colour</dt><dd>{esc(t["colour"])}</dd></div><div><dt>Grain</dt><dd>{esc(t["grain"])}</dd></div>'
                   f'<div><dt>Grows</dt><dd>{esc(t["grows"])}</dd></div></dl><p>{esc(t["character"])}</p>'
                   f'<p class="fine">Used in {len(uses)} {"piece" if len(uses) == 1 else "pieces"}.</p></li>')
    return "\n".join(out)


def build_pages():
    for f in sorted((SRC / "pages").glob("*.html")):
        text = f.read_text()
        m = re.match(r"<!--meta (\{.*?\}) -->\n", text, re.S)
        meta = json.loads(m[1])
        body = text[m.end():]
        root = root_for(meta["path"])
        cat_filters = "\n".join(f'        <label><input type="checkbox" name="cat" value="{k}"> {v["name"]}</label>' for k, v in CATS.items())
        tim_filters = "\n".join(f'        <label><input type="checkbox" name="timber" value="{k}"> {v["name"]}</label>' for k, v in TIMBERS.items())
        body = (body.replace("{{featured}}", "\n".join(card(p, root) for p in PRODUCTS if p.get("featured")))
                    .replace("{{allCards}}", "\n".join(card(p, root) for p in PRODUCTS))
                    .replace("{{filterCategories}}", cat_filters).replace("{{filterTimbers}}", tim_filters)
                    .replace("{{timberCards}}", timber_cards()))
        page(meta["path"], meta["title"], meta["description"], body,
             jsonld=jsonld_home() if meta.get("jsonld") == "home" else "", noindex=meta.get("noindex", False))


def placeholder_pdfs():
    from PIL import Image, ImageDraw
    names = [f"{p['slug']}-spec-sheet" for p in PRODUCTS] + [f"{p['slug']}-install-guide" for p in PRODUCTS] + \
            ["onus-wood-catalogue", "onus-wood-spec-sheets", "onus-wood-timber-guide"]
    (OUT / "downloads").mkdir(exist_ok=True)
    for n in names:
        im = Image.new("RGB", (1240, 1754), "#FBFAF7")
        d = ImageDraw.Draw(im)
        d.text((120, 160), "ONUS WOOD", fill="#2A211C")
        d.text((120, 220), n.replace("-", " ").title(), fill="#2A211C")
        d.text((120, 280), "PLACEHOLDER: this document will be available once the range is finalised.", fill="#6B2A1F")
        d.text((120, 320), "Questions: hello@onuswood.com", fill="#5C5148")
        im.save(OUT / "downloads" / f"{n}.pdf", "PDF", resolution=150)


def main():
    if OUT.exists():
        shutil.rmtree(OUT)
    OUT.mkdir()
    for d in ("assets", "brand", "images"):
        shutil.copytree(SRC / d, OUT / d)
    (OUT / ".nojekyll").write_text("")
    (OUT / "CNAME").write_text("onuswood.com\n")
    build_pages()
    build_categories()
    for p in PRODUCTS:
        build_product(p)
    placeholder_pdfs()
    urls = "\n".join(f"  <url><loc>{SITE}{p}</loc></url>" for p in sitemap)
    (OUT / "sitemap.xml").write_text(f'<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n{urls}\n</urlset>\n')
    (OUT / "robots.txt").write_text(f"User-agent: *\nAllow: /\nDisallow: /brand/\n\nSitemap: {SITE}/sitemap.xml\n")
    lines = [f"- [{p['name']} {p['type'].lower()}]({SITE}/product/{p['slug']}/): {p['short']} From {money(price_range(p)[0])}." for p in PRODUCTS]
    (OUT / "llms.txt").write_text("# Onus Wood\n\n> Australian timber lighting, made to order: pendants, wall sconces, floor lamps, task lamps and candelabras in a choice of Australian hardwoods. Prices in AUD including GST.\n\n## Pieces\n" + "\n".join(lines) +
                                  f"\n\n## Pages\n- [Timbers]({SITE}/timbers/)\n- [Bespoke]({SITE}/bespoke/)\n- [Trade]({SITE}/trade/)\n- [Contact]({SITE}/contact/)\n")
    print(f"Built {len(sitemap)} indexed pages into {OUT}")


if __name__ == "__main__":
    main()
