/* Конфигуратор Zeekr (общий для 9X, 8X и других моделей). Данные – window.ZEEKR_CFG (js/zeekr-data.js).
 * Картинки – официальные рендеры Zeekr выбранной сборки. Цен нет намеренно. Без зависимостей.
 * Для сайта: событие "zeekr:change" на блоке [data-z9] (detail: text, lines, config, url),
 * window.ZeekrCfg.get() – текущая сборка; заявка из формы уходит POST JSON на data-endpoint формы,
 * а если он пуст – событием "zeekr:lead" (detail: name, phone, text, url). */
(function () {
  "use strict";

  var D = window.ZEEKR_CFG;
  var root = document.querySelector("[data-z9]");
  if (!D || !root) return;

  var $ = function (sel) { return root.querySelector(sel); };
  var esc = function (s) { return String(s).replace(/[&<>"]/g, function (c) { return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]; }); };
  var O = D.options;
  var opt = function (id) { return O[id] || { name: id || "", note: "", mutex: [], cascade: [], sku: "" }; };
  var defOf = function (list) { for (var i = 0; i < list.length; i++) if (list[i].def) return list[i].id; return list.length ? list[0].id : null; };
  var INT = {}; D.int.forEach(function (c) { INT[c] = true; });
  var conflict = function (a, b) { return opt(a).mutex.indexOf(b) !== -1 || opt(b).mutex.indexOf(a) !== -1; };
  var versionById = function (id) { for (var i = 0; i < D.versions.length; i++) if (D.versions[i].id === id) return D.versions[i]; return null; };
  var versionsOf = function (g) { return D.versions.filter(function (v) { return v.group === g; }); };
  var PREFIX = (D.versions[0].level[0].opts[0].id.match(/^Z0\d\dPC/) || ["Z011PC"])[0];
  // в адресе коды сокращаются (Z011PC012 → 012); коды другого вида (у 001: Z001C001) идут целиком
  var SHORT = function (pc) { return pc.indexOf(PREFIX) === 0 ? pc.slice(PREFIX.length) : pc; };
  var LONG = function (s) { return /^Z\d/.test(s) ? s : PREFIX + s; };

  // все группы опций версии: уровень (батарея, H7/H9) + секции
  function groupsOf(V) { return V.level.concat(V.secs); }
  function groupByRole(V, role) { var g = groupsOf(V).filter(function (x) { return x.role === role; }); return g[0] || null; }

  // ---------- состояние ----------
  var state = { version: null, sel: {}, shot: "hero" };
  function sig(id) { return opt(id).name + "|" + opt(id).note; }
  function defaults(V, keep) {
    var old = state.sel; state.sel = {};
    var oldSig = {}; for (var s in old) if (old[s]) oldSig[sig(old[s])] = true;
    groupsOf(V).forEach(function (g) {
      if (g.role === "extra") {
        var o = g.opts[0];
        state.sel[g.sku] = (o.def || (keep && oldSig[sig(o.id)])) ? o.id : null;
        return;
      }
      // при смене версии сохраняем выбор по названию (у версий бывают разные коды одной опции)
      var keepId = null;
      if (keep) g.opts.forEach(function (o) { if (!keepId && !o.promo && oldSig[sig(o.id)]) keepId = o.id; });
      state.sel[g.sku] = keepId || defOf(g.opts);
    });
  }
  var first = D.versions.filter(function (v) { return /^Ultra$/.test(v.name); })[0] || D.versions[0];
  state.version = first.id; defaults(first, false);

  (function readHash() {
    var h = location.hash.replace(/^#/, ""); if (!h) return;
    var q = {}; h.split("&").forEach(function (kv) { var p = kv.split("="); q[p[0]] = decodeURIComponent(p[1] || ""); });
    var V = versionById(q.v); if (!V) return;
    state.version = V.id; defaults(V, false);
    groupsOf(V).forEach(function (g) { if (g.role === "extra" && !g.opts[0].def) state.sel[g.sku] = null; });
    if (q.o) q.o.split(".").forEach(function (s) { var pc = LONG(s), o = O[pc]; if (o && o.sku in state.sel) state.sel[o.sku] = pc; });
  })();
  var version = function () { return versionById(state.version); };

  // Сборка в порядок: несовместимое подбирается заново, начиная с того, что человек выбрал последним.
  function normalize(prioSku) {
    var V = version(), groups = groupsOf(V).filter(function (g) { return g.role !== "extra"; });
    groups.sort(function (a, b) { return (b.sku === prioSku) - (a.sku === prioSku); });
    var fixed = [];
    groups.forEach(function (g) {
      var ids = g.opts.map(function (o) { return o.id; });
      var valid = function (x) {
        if (ids.indexOf(x) === -1) return false;
        for (var i = 0; i < fixed.length; i++) {
          var f = fixed[i], cf = opt(f).cascade, cx = opt(x).cascade;
          if (conflict(x, f)) return false;
          if (cf.some(function (c) { return opt(c).sku === g.sku; }) && cf.indexOf(x) === -1) return false;
          if (cx.some(function (c) { return opt(c).sku === opt(f).sku; }) && cx.indexOf(f) === -1) return false;
        }
        return true;
      };
      var cur = state.sel[g.sku];
      var isPrio = g.sku === prioSku && ids.indexOf(cur) !== -1;
      if (!isPrio && !valid(cur)) {
        var pick = valid(defOf(g.opts)) ? defOf(g.opts) : null;
        if (!pick) for (var i = 0; i < g.opts.length; i++) if (valid(g.opts[i].id)) { pick = g.opts[i].id; break; }
        state.sel[g.sku] = pick || defOf(g.opts);
      }
      fixed.push(state.sel[g.sku]);
    });
  }

  // ---------- картинки ----------
  function codeFor(skus, drop) {
    return skus.map(function (s) { return drop && drop.indexOf(s) !== -1 ? null : state.sel[s]; }).filter(Boolean).join("_");
  }
  function extCode() {
    var V = version(), c = codeFor(V.vehicleSkus);
    if (D.have[c]) return c;
    var tail = "_" + codeFor(V.vehicleSkus.slice(1));
    for (var k in D.have) if (k.slice(-tail.length) === tail) return k;
    return Object.keys(D.have)[0];
  }
  function intCode() {
    var V = version(), c = codeFor(V.interiorSkus);
    if (INT[c]) return c;
    var extras = V.interiorSkus.filter(function (s) { var g = groupsOf(V).filter(function (x) { return x.sku === s; })[0]; return g && g.role === "extra"; });
    c = codeFor(V.interiorSkus, extras);
    return INT[c] ? c : null;
  }
  // ракурсы у Zeekr строятся по своему списку групп (angleSkus), он бывает короче, чем у главного кадра
  function angCode() {
    var V = version();
    if (!D.ang || !V.angleSkus) return extCode();
    var c = codeFor(V.angleSkus);
    return D.ang[c] ? c : null;
  }
  function angShots() {
    if (D.ang && version().angleSkus) { var a = angCode(); return a ? D.ang[a] : []; }
    return (D.have[extCode()] || []).filter(function (s) { return s !== "hero"; });
  }
  function shotsNow() {
    var have = ["hero"].concat(angShots());
    return D.shots.filter(function (s) { return s.id === "int" ? !!intCode() : have.indexOf(s.id) !== -1; });
  }
  function fixShot() { if (!shotsNow().some(function (s) { return s.id === state.shot; })) state.shot = "hero"; }
  function srcFor(shot) {
    if (shot === "int") return D.paths.int.replace("{code}", intCode());
    return D.paths.ext.replace("{code}", shot === "hero" ? extCode() : (angCode() || extCode())).replace("{shot}", shot);
  }
  var cache = {};
  function preload(src) {
    if (cache[src]) return cache[src];
    var img = new Image(); img.decoding = "async";
    cache[src] = new Promise(function (res) { img.onload = img.onerror = function () { res(src); }; });
    img.src = src; return cache[src];
  }
  function warm() { shotsNow().forEach(function (s) { preload(srcFor(s.id)); }); }

  var stage = $(".z9__stage"), front = $(".z9__shot--a"), back = $(".z9__shot--b"), token = 0;
  function show() {
    var my = ++token, src = srcFor(state.shot), hero = state.shot === "hero";
    stage.classList.add("is-loading");
    preload(src).then(function () {
      if (my !== token) return;
      var img = back.querySelector("img"); img.src = src; img.alt = altText();
      back.classList.toggle("is-hero", hero); back.classList.add("is-front"); front.classList.remove("is-front");
      var t = front; front = back; back = t; stage.classList.remove("is-loading"); warm();
    });
  }
  function selRole(role) { var g = groupByRole(version(), role); return g ? state.sel[g.sku] : null; }
  function altText() {
    if (state.shot === "int") return "Салон " + D.car + ", " + opt(selRole("int")).name;
    return D.car + " " + version().name + ", " + opt(selRole("paint")).name + ", диски " + opt(selRole("wheel")).name;
  }

  // ---------- отрисовка ----------
  // заголовок и вид группы – из данных (title, kind); у уровня версии – свои
  var LEVEL_TITLE = { battery: "Батарея", adas: "Помощь водителю" };
  function titleOf(g) { return g.title || LEVEL_TITLE[g.role] || ""; }
  function kindOf(g) { return g.kind || "seg"; }
  // группы выбора по порядку: уровень версии, затем секции из данных (без галочек)
  function choiceGroups(V) { return V.level.concat(V.secs.filter(function (g) { return g.role !== "extra"; })); }

  function range(V, wheel) {
    var r = V.ranges[selRole("battery")] || {};
    return r[wheel || selRole("wheel")] || null;
  }
  function renderGroup(V, g) {
    var cur = state.sel[g.sku], kind = kindOf(g), single = g.opts.length === 1, html;
    if (kind === "swatch") {
      html = '<div class="z9__swatches">' + g.opts.map(function (o) {
        var on = o.id === cur, p = opt(o.id);
        return '<button type="button" class="z9__swatch' + (on ? " is-active" : "") + '" data-sku="' + g.sku + '" data-pc="' + o.id + '" title="' + esc(p.name) + '" aria-label="' + esc(p.name) + '" aria-pressed="' + on + '">' +
          (p.icon ? '<img src="' + p.icon + '" alt="" width="44" height="44">' : "<i></i>") + "</button>";
      }).join("") + "</div>";
    } else if (kind === "option") {
      html = '<div class="z9__options">' + g.opts.map(function (o) {
        var on = o.id === cur, p = opt(o.id), note = p.note;
        if (g.role === "wheel") { var r = range(V, o.id); if (r) note += (note ? " · " : "") + r.ev + " км на электричестве"; if (o.promo) note += " · сейчас Zeekr по акции ставит вместо них " + (o.promoTo || "диски больше"); }
        return '<button type="button" class="z9__option' + (on ? " is-active" : "") + (single ? " is-single" : "") + '" data-sku="' + g.sku + '" data-pc="' + o.id + '" aria-pressed="' + on + '">' +
          (p.icon ? '<img src="' + p.icon + '" alt="" width="56" height="56" loading="lazy">' : "<span></span>") +
          '<span class="z9__option-text"><span class="z9__option-name">' + esc(p.name) + '</span><span class="z9__option-note">' + esc(note) + "</span></span></button>";
      }).join("") + "</div>";
    } else {
      html = '<div class="z9__segs">' + g.opts.map(function (o) {
        var p = opt(o.id), sub = p.note, on = o.id === cur;
        if (g.role === "battery") { var rr = (V.ranges[o.id] || {})[selRole("wheel")]; if (rr) sub = rr.ev + " км на электричестве · " + rr.total + " км всего"; }
        return '<button type="button" class="z9__seg' + (on ? " is-active" : "") + (single ? " is-single" : "") + '" data-sku="' + g.sku + '" data-pc="' + o.id + '" aria-pressed="' + on + '"><b>' +
          esc((g.role === "adas" ? "Пакет " : "") + p.name) + "</b>" + (sub ? "<span>" + esc(sub) + "</span>" : "") + "</button>";
      }).join("") + "</div>";
    }
    var picked = kind === "swatch" ? '<span class="z9__picked">' + esc(opt(cur).name) + "</span>" : "";
    return '<div class="z9__block"><div class="z9__head"><h2 class="z9__title">' + esc(titleOf(g)) + "</h2>" + picked + "</div>" + html + noteFor(g) + "</div>";
  }
  function noteFor(g) {
    var t = "";
    if (g.role === "choice" && g.img === "ext" && g.opts.some(function (o) { return conflict(o.id, selRole("paint")); })) t = "Часть вариантов сочетается только с определёнными цветами кузова – при выборе цвет подстроится.";
    if (g.role === "wheel") {
      version().secs.forEach(function (x) { var sel = state.sel[x.sku]; if (x.sku !== g.sku && sel && opt(sel).cascade.some(function (c) { return opt(c).sku === g.sku; })) t = "С выбранным пакетом – только его фирменные диски."; });
    }
    return t ? '<p class="z9__opt-note">' + esc(t) + "</p>" : "";
  }

  function render() {
    var V = version(), html = "";
    if (D.groups.length > 1) {
      html += '<div class="z9__block"><div class="z9__head"><h2 class="z9__title">Мест в салоне</h2></div><div class="z9__segs">' +
        D.groups.map(function (g) { var on = g.id === V.group; return '<button type="button" class="z9__seg' + (on ? " is-active" : "") + '" data-group="' + g.id + '" aria-pressed="' + on + '"><b>' + esc(g.label) + "</b><span>" + esc(g.sub) + "</span></button>"; }).join("") + "</div></div>";
    }
    html += '<div class="z9__block"><div class="z9__head"><h2 class="z9__title">Версия</h2></div><div class="z9__trims">' +
      (D.groups.length > 1 ? versionsOf(V.group) : D.versions).map(function (v) {
        var on = v.id === state.version;
        return '<button type="button" class="z9__trim' + (on ? " is-active" : "") + '" data-version="' + v.id + '" aria-pressed="' + on + '"><span class="z9__trim-name">' + esc(D.short + " " + v.name) + '</span><span class="z9__trim-tag">' + esc(v.tag) + "</span></button>";
      }).join("") + "</div></div>";
    choiceGroups(V).forEach(function (g) { html += renderGroup(V, g); });
    var extras = V.secs.filter(function (g) { return g.role === "extra"; });
    if (extras.length) {
      html += '<div class="z9__block"><div class="z9__head"><h2 class="z9__title">Дополнительно</h2></div><div class="z9__checks">' + extras.map(function (g) {
        var o = g.opts[0], on = state.sel[g.sku] === o.id;
        return '<label class="z9__check"><input type="checkbox" data-extra="' + g.sku + '" value="' + o.id + '"' + (on ? " checked" : "") + (o.def ? " disabled" : "") + "> " + esc(opt(o.id).name) + (o.def ? " <small>в комплектации</small>" : "") + "</label>";
      }).join("") + "</div></div>";
    }
    $("[data-slot=groups]").innerHTML = html;
    renderThumbs(); renderSummary();
  }
  function renderThumbs() {
    $("[data-slot=thumbs]").innerHTML = shotsNow().map(function (s) {
      var on = s.id === state.shot;
      return '<button type="button" class="z9__thumb' + (s.id === "hero" ? " is-hero" : "") + (on ? " is-active" : "") + '" data-shot="' + s.id + '" aria-pressed="' + on + '"><img src="' + srcFor(s.id) + '" alt="" loading="lazy" width="160" height="100"><span>' + esc(s.label) + "</span></button>";
    }).join("");
  }

  function config() {
    var V = version(), r = range(V);
    var gl = D.groups.filter(function (g) { return g.id === V.group; })[0];
    var lines = [["Версия", D.short + " " + V.name + (gl && D.groups.length > 1 ? ", " + gl.label : "")]];
    if (V.drive) lines.push(["Привод", V.drive]);
    choiceGroups(V).forEach(function (g) {
      var role = g.role, p = opt(state.sel[g.sku]), val = p.name;
      if (!state.sel[g.sku]) return;
      if (role === "adas") val = "Пакет " + p.name;
      if (role === "wheel") val = p.name + (p.note ? ", " + p.note : "");
      lines.push([titleOf(g), val]);
      if (role === "battery" && r) lines.push(["Запас хода (CLTC)", r.ev + " км на электричестве, " + r.total + " км всего"]);
    });
    var ex = V.secs.filter(function (g) { return g.role === "extra" && state.sel[g.sku]; }).map(function (g) { return opt(state.sel[g.sku]).name; });
    if (ex.length) lines.push(["Дополнительно", ex.join(", ")]);
    var text = D.car + " " + V.name + ": " + lines.slice(1).map(function (l) { return l[0].charAt(0).toLowerCase() + l[0].slice(1) + " – " + l[1]; }).join("; ");
    var codes = Object.keys(state.sel).map(function (s) { return state.sel[s]; }).filter(Boolean);
    return { text: text, lines: lines, hash: "#v=" + V.id + "&o=" + codes.map(SHORT).join("."), codes: codes };
  }
  function renderSummary() {
    var c = config(), V = version();
    $("[data-slot=summary-config]").textContent = D.car + " " + V.name;
    $("[data-slot=summary-lines]").innerHTML = c.lines.map(function (l) { return '<div class="z9__row"><dt>' + esc(l[0]) + "</dt><dd>" + esc(l[1]) + "</dd></div>"; }).join("");
    $("[data-slot=stage-name]").textContent = D.car + " " + V.name;
    $("[data-slot=stage-note]").textContent = [opt(selRole("paint")).name, opt(selRole("wheel")).name, selRole("int") ? "салон " + opt(selRole("int")).name : ""].filter(Boolean).join(" · ");
    if (history.replaceState) history.replaceState(null, "", c.hash);
    var detail = { text: c.text, lines: c.lines, config: c.codes, url: location.href.split("#")[0] + c.hash };
    window.ZeekrCfg = { get: function () { return detail; } };
    root.dispatchEvent(new CustomEvent("zeekr:change", { bubbles: true, detail: detail }));
  }
  function update(prio, img) { normalize(prio); fixShot(); render(); if (img !== false) show(); }

  // ---------- события ----------
  function step(dir) {
    var list = shotsNow().map(function (x) { return x.id; }), i = list.indexOf(state.shot);
    state.shot = list[(i + dir + list.length) % list.length]; renderThumbs(); show();
  }
  root.addEventListener("click", function (e) {
    var b = e.target.closest("button"); if (!b || !root.contains(b)) return;
    var d = b.dataset;
    if (d.group) {
      var V0 = version(); if (d.group === V0.group) return;
      var list = versionsOf(d.group), V = list.filter(function (v) { return v.name === V0.name; })[0] || list[0];
      state.version = V.id; defaults(V, true); update(null);
    } else if (d.version) {
      if (d.version === state.version) return;
      state.version = d.version; defaults(version(), true); update(null);
    } else if (d.sku && d.pc) {
      var g = groupsOf(version()).filter(function (x) { return x.sku === d.sku; })[0], role = g ? g.role : "";
      state.sel[d.sku] = d.pc;
      if (role === "wheel") state.shot = "side";
      else if (role === "paint" || role === "adas") { if (state.shot === "int") state.shot = "hero"; }
      else if (role === "int" || role === "screen" || (g && g.img === "int")) state.shot = "int";
      else if (g && g.img === "ext") state.shot = "hero";                // декор, крыша, зеркала, спойлер – всегда первый кадр
      update(d.sku, role !== "battery");
    } else if (d.shot) { state.shot = d.shot; renderThumbs(); show();
    } else if (d.nav) { step(d.nav === "next" ? 1 : -1);
    } else if (b.hasAttribute("data-send")) {
      var f = $("form.z9__form"); f.hidden = false; b.hidden = true; f.querySelector("input[name=phone]").focus();
    }
  });
  root.addEventListener("change", function (e) {
    var sku = e.target.getAttribute("data-extra");
    if (sku) { state.sel[sku] = e.target.checked ? e.target.value : null; update(null, false); if (state.shot === "int") show(); }
    if (e.target.name === "agree") $("form.z9__form button[type=submit]").disabled = !e.target.checked;
  });
  stage.addEventListener("keydown", function (e) { if (e.key === "ArrowLeft" || e.key === "ArrowRight") { e.preventDefault(); step(e.key === "ArrowRight" ? 1 : -1); } });
  (function swipe() {
    var x0 = null;
    stage.addEventListener("pointerdown", function (e) { x0 = e.clientX; });
    stage.addEventListener("pointerup", function (e) { if (x0 === null) return; var dx = e.clientX - x0; x0 = null; if (Math.abs(dx) >= 40) step(dx < 0 ? 1 : -1); });
  })();

  // ссылка на сборку
  var copy = $("[data-copy]");
  if (copy) copy.addEventListener("click", function (e) {
    e.preventDefault();
    var url = window.ZeekrCfg.get().url, st = $("[data-slot=copy-status]");
    var ok = function () { st.textContent = "Ссылка скопирована"; };
    if (navigator.clipboard) navigator.clipboard.writeText(url).then(ok, function () { st.textContent = url; }); else st.textContent = url;
  });

  // заявка
  var form = $("form.z9__form");
  if (form) form.addEventListener("submit", function (e) {
    e.preventDefault();
    var st = form.querySelector(".z9__form-status"), phone = form.phone.value.replace(/\D/g, "");
    if (phone.length < 9) { st.textContent = "Проверьте номер телефона"; st.className = "z9__form-status is-error"; return; }
    var cfg = window.ZeekrCfg.get();
    var data = { name: form.elements.name.value.trim(), phone: form.code.value + " " + form.phone.value.trim(), text: cfg.text, url: cfg.url, lines: cfg.lines, source: "Конфигуратор " + D.car, page: location.href.split("#")[0] };
    var done = function () { form.reset(); form.querySelector("button[type=submit]").disabled = true; form.hidden = true; $("[data-slot=sent]").hidden = false; };
    var endpoint = form.getAttribute("data-endpoint");
    if (!endpoint) { root.dispatchEvent(new CustomEvent("zeekr:lead", { bubbles: true, detail: data })); console.warn("[zeekr] data-endpoint не задан, заявка:", data); done(); return; }
    fetch(endpoint, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(data) })
      .then(function (r) { if (!r.ok) throw new Error(r.status); done(); })
      .catch(function () { st.textContent = "Не удалось отправить. Попробуйте ещё раз или позвоните нам."; st.className = "z9__form-status is-error"; });
  });

  // тема
  var tb = document.querySelector("[data-theme-toggle]");
  if (tb) {
    var upd = function () { var dk = document.documentElement.getAttribute("data-theme") === "dark"; tb.textContent = dk ? "☀" : "☾"; tb.title = dk ? "Светлая тема" : "Тёмная тема"; };
    tb.addEventListener("click", function () { var n = document.documentElement.getAttribute("data-theme") === "dark" ? "light" : "dark"; document.documentElement.setAttribute("data-theme", n); try { localStorage.setItem("tema", n); } catch (er) {} upd(); });
    upd();
  }

  normalize(null); fixShot(); render();
  var img0 = front.querySelector("img"); img0.src = srcFor(state.shot); img0.alt = altText();
  front.classList.add("is-front"); front.classList.toggle("is-hero", state.shot === "hero");
  window.addEventListener("load", function () { setTimeout(warm, 600); });
})();
