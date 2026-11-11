/* Onus Wood · menu, cart, product options, forms. Works as progressive enhancement. */
(function () {
  "use strict";
  var $ = function (s, el) { return (el || document).querySelector(s); };
  var $$ = function (s, el) { return Array.prototype.slice.call((el || document).querySelectorAll(s)); };
  var money = function (n) { return "$" + Math.round(n).toLocaleString("en-AU"); };

  // Footer year
  $$("[data-year]").forEach(function (el) { el.textContent = new Date().getFullYear(); });

  // Phone menu
  var menuBtn = $("[data-menu]"), nav = $("#main-nav");
  if (menuBtn && nav) {
    menuBtn.addEventListener("click", function () {
      var open = menuBtn.getAttribute("aria-expanded") !== "true";
      menuBtn.setAttribute("aria-expanded", String(open));
      nav.classList.toggle("is-open", open);
    });
    document.addEventListener("keydown", function (e) {
      if (e.key === "Escape" && nav.classList.contains("is-open")) {
        menuBtn.setAttribute("aria-expanded", "false"); nav.classList.remove("is-open"); menuBtn.focus();
      }
    });
  }

  // Cart, stored on this device only
  var KEY = "onuswood-cart";
  var load = function () { try { return JSON.parse(localStorage.getItem(KEY)) || []; } catch (e) { return []; } };
  var save = function (c) { try { localStorage.setItem(KEY, JSON.stringify(c)); } catch (e) {} };
  var cart = load();

  var drawer = $("[data-drawer]"), lastFocus = null;
  function render() {
    var lines = $("[data-cart-lines]"), total = 0, count = 0;
    if (!lines) return;
    lines.innerHTML = "";
    cart.forEach(function (item, i) {
      total += item.price * item.qty; count += item.qty;
      var li = document.createElement("li");
      var sw = document.createElement("span"); sw.className = "swatch grain"; sw.style.setProperty("--wood", item.tone || "#B4895A");
      var info = document.createElement("div");
      var name = document.createElement("strong"); name.textContent = item.name;
      var meta = document.createElement("div"); meta.className = "cart-line-meta"; meta.textContent = item.timber + " · " + item.size + (item.qty > 1 ? " · x" + item.qty : "");
      var rm = document.createElement("button"); rm.type = "button"; rm.className = "text-link cart-line-remove"; rm.textContent = "Remove";
      rm.setAttribute("aria-label", "Remove " + item.name + " from cart");
      rm.addEventListener("click", function () { cart.splice(i, 1); save(cart); render(); });
      info.appendChild(name); info.appendChild(meta); info.appendChild(rm);
      var price = document.createElement("span"); price.textContent = money(item.price * item.qty);
      li.appendChild(sw); li.appendChild(info); li.appendChild(price);
      lines.appendChild(li);
    });
    $("[data-cart-empty]").hidden = cart.length > 0;
    $("[data-cart-foot]").hidden = cart.length === 0;
    $("[data-cart-total]").textContent = money(total);
    $$("[data-cart-count]").forEach(function (b) { b.textContent = count; b.hidden = count === 0; });
    var field = $("[data-cart-field]");
    if (field) field.value = cart.map(function (c) { return c.qty + " x " + c.name + " (" + c.timber + ", " + c.size + ") " + money(c.price * c.qty); }).join("; ") + " | Total " + money(total);
  }
  function showCheckout(on) {
    $("[data-cart-view]").hidden = on; $("[data-checkout-view]").hidden = !on;
    $("[data-cart-foot]").hidden = on || cart.length === 0;
  }
  function openDrawer() {
    lastFocus = document.activeElement; showCheckout(false); render();
    drawer.hidden = false; document.body.style.overflow = "hidden";
    $(".drawer-head .icon-button", drawer).focus();
  }
  function closeDrawer() {
    drawer.hidden = true; document.body.style.overflow = "";
    if (lastFocus) lastFocus.focus();
  }
  if (drawer) {
    $$("[data-cart-open]").forEach(function (b) { b.addEventListener("click", openDrawer); });
    $$("[data-cart-close]").forEach(function (b) { b.addEventListener("click", closeDrawer); });
    document.addEventListener("keydown", function (e) { if (e.key === "Escape" && !drawer.hidden) closeDrawer(); });
    $("[data-checkout]").addEventListener("click", function () { showCheckout(true); $("[data-checkout-view] input[name=name]").focus(); });
    $("[data-checkout-back]").addEventListener("click", function () { showCheckout(false); });
    render();
  }

  // Product options: price follows timber and size
  var product = $("[data-product]");
  if (product) {
    var data = JSON.parse(product.getAttribute("data-product"));
    var form = $("[data-options]", product);
    var tones = {};
    $$("input[name=timber]", form).forEach(function (r) { var s = r.nextElementSibling; tones[r.value] = s ? s.style.getPropertyValue("--wood") : ""; });
    var current = function () {
      var t = (form.querySelector("input[name=timber]:checked") || {}).value;
      var sid = (form.querySelector("input[name=size]:checked") || form.querySelector("input[name=size]") || {}).value;
      var size = data.sizes.filter(function (s) { return s.id === sid; })[0] || data.sizes[0];
      return { timber: t, size: size, price: size.price + (data.upcharge[t] || 0) };
    };
    var update = function () {
      var c = current();
      $("[data-price]", product).textContent = money(c.price);
      $("[data-timber-name]", product).textContent = data.timbers[c.timber];
    };
    form.addEventListener("change", update); update();
    form.addEventListener("submit", function (e) {
      e.preventDefault();
      var c = current();
      if (data.checkoutUrl) { window.location.href = data.checkoutUrl; return; }
      var id = data.slug + "|" + c.timber + "|" + c.size.id;
      var found = cart.filter(function (x) { return x.id === id; })[0];
      if (found) found.qty += 1;
      else cart.push({ id: id, name: data.name, timber: data.timbers[c.timber], size: c.size.label, price: c.price, qty: 1, tone: tones[c.timber] });
      save(cart); render();
      $("[data-add-status]", product).textContent = "Added to your cart.";
      if (drawer) openDrawer();
    });
  }

  // Shop filters
  var filters = $("[data-filters]"), grid = $("[data-grid]");
  if (filters && grid) {
    var items = $$("li[data-cat]", grid);
    var apply = function () {
      var cats = $$("input[name=cat]:checked", filters).map(function (i) { return i.value; });
      var tims = $$("input[name=timber]:checked", filters).map(function (i) { return i.value; });
      var pr = ($("input[name=price]:checked", filters) || {}).value || "";
      var lead = ($("input[name=lead]:checked", filters) || {}).value || "";
      var lo = pr ? +pr.split("-")[0] : 0, hi = pr ? +pr.split("-")[1] : Infinity, shown = 0;
      items.forEach(function (li) {
        var ok = (!cats.length || cats.indexOf(li.dataset.cat) !== -1) &&
          (!tims.length || li.dataset.timbers.split(" ").some(function (t) { return tims.indexOf(t) !== -1; })) &&
          (+li.dataset.price >= lo && +li.dataset.price < hi) && (!lead || +li.dataset.lead <= +lead);
        li.hidden = !ok; if (ok) shown++;
      });
      $("[data-filter-count]").textContent = shown === items.length ? "Showing all " + shown + " pieces" : "Showing " + shown + " of " + items.length + " pieces";
      $("[data-empty]").hidden = shown > 0;
    };
    filters.addEventListener("change", apply);
    filters.addEventListener("reset", function () { setTimeout(apply, 0); });
    var ft = $("[data-filters-toggle]");
    if (ft) ft.addEventListener("click", function () {
      var open = ft.getAttribute("aria-expanded") !== "true";
      ft.setAttribute("aria-expanded", String(open)); filters.classList.toggle("is-open", open);
    });
  }

  // Contact form: prefill the subject from ?subject=
  var subj = $("[data-subject-field]");
  if (subj) { try { var q = new URLSearchParams(location.search).get("subject"); if (q) subj.value = q; } catch (e) {} }

  // Forms: Formspree once FORMSPREE_ID is replaced, otherwise a clear placeholder message
  $$("form[data-form]").forEach(function (f) {
    f.addEventListener("submit", function (e) {
      var status = $("[data-form-status]", f);
      if (f.action.indexOf("FORMSPREE_ID") !== -1) {
        e.preventDefault();
        status.textContent = "Thanks. Forms aren't connected yet (placeholder), so nothing was sent. Email hello@onuswood.com for now.";
        return;
      }
      e.preventDefault();
      status.textContent = "Sending...";
      fetch(f.action, { method: "POST", body: new FormData(f), headers: { Accept: "application/json" } })
        .then(function (r) {
          if (!r.ok) throw new Error();
          status.textContent = "Thank you. We'll be in touch within two working days.";
          f.reset();
          if (f.getAttribute("data-form") === "order") { cart = []; save(cart); render(); }
        })
        .catch(function () { status.textContent = "Sorry, that didn't send. Please email hello@onuswood.com."; });
    });
  });
})();
