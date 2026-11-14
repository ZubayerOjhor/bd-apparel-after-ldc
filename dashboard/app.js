/* Bangladesh apparel after LDC graduation: dashboard. Reads data/apparel.json written by `python -m apparel export`. */

const COLORS = { CN: "#2a78d6", VN: "#eb6834", BD: "#1baf7a", KH: "#eda100", IN: "#e87ba4" };
const ORDER = ["CN", "VN", "BD", "KH", "IN"];
const INK = "#0f1b2d", MUTED = "#7d8aa0", LINE = "#e3e8ef";
const charts = {};
let D;

const pct = (v, d = 1) => (v == null ? "-" : `${(v * 100).toFixed(d)}%`);
const pp = v => `${v >= 0 ? "+" : ""}${(v * 100).toFixed(1)}`;
const eurBn = v => `EUR ${(v / 1e9).toFixed(1)}bn`;
const usdBn = v => `$${(v / 1e9).toFixed(1)}bn`;
const signPct = (v, d = 1) => `${v >= 0 ? "+" : ""}${(v * 100).toFixed(d)}%`;
const name = e => D.meta.exporters[e];
const monthName = m => new Date(m + "-01T00:00:00").toLocaleDateString("en-GB", { month: "long" });

function chart(id) {
  if (!charts[id]) charts[id] = echarts.init(document.getElementById(id), null, { renderer: "canvas" });
  return charts[id];
}
const axis = { axisLine: { lineStyle: { color: LINE } }, axisTick: { show: false }, axisLabel: { color: MUTED, fontSize: 11.5 },
               splitLine: { lineStyle: { color: "#eef1f5" } } };
const base = { textStyle: { fontFamily: "Inter, sans-serif" }, grid: { left: 52, right: 96, top: 24, bottom: 30 },
               tooltip: { trigger: "axis", backgroundColor: "#fff", borderColor: LINE, textStyle: { color: INK, fontSize: 12 } } };

function kpi(label, value, detail, focus) {
  return `<div class="kpi${focus ? " focus" : ""}"><div class="l">${label}</div><div class="v">${value}</div><div class="d">${detail}</div></div>`;
}

function shareSeries(market, exporters, years) {
  return exporters.map(e => {
    const rows = D.share_market.filter(r => r.market === market && r.exporter === e).sort((a, b) => a.year - b.year);
    return {
      name: name(e), type: "line", smooth: false, symbol: "circle", symbolSize: e === "BD" ? 7 : 5, showSymbol: false,
      lineStyle: { width: e === "BD" ? 3.5 : 2, color: COLORS[e] }, itemStyle: { color: COLORS[e] }, z: e === "BD" ? 5 : 2,
      endLabel: { show: true, formatter: p => `${name(e)} ${p.value[1].toFixed(1)}%`, color: INK, fontSize: 11.5, fontWeight: e === "BD" ? 700 : 500 },
      labelLayout: { moveOverlap: "shiftY" },
      data: rows.filter(r => !years || years.includes(r.year)).map(r => [String(r.year), r.share * 100]),
    };
  });
}

/* ---------- The answer ---------- */
function renderAnswer() {
  const h = D.headline;
  const ytd = D.eu_ytd.find(r => r.exporter === "BD");
  document.getElementById("answer-text").innerHTML =
    `<b>Defend knitwear in the EU, take woven growth to the US and UK, and build man-made-fibre capacity for the categories China is leaving.</b> ` +
    `Bangladesh's EU share rose from ${pct(h.eu_share_2015)} in 2015 to ${pct(h.eu_share_2022)} in 2022, then slipped to ${pct(h.eu_share_2025)} as China came back. ` +
    `If EU access is lost, 2025's sales would have paid ${eurBn(h.duty_lost_eur)} in duty, and ${eurBn(h.risk_lost_low)} to ${eurBn(h.risk_lost_high)} of sales would be at risk to duty-free Vietnam and India.`;
  document.getElementById("kpis").innerHTML = [
    kpi("EU share, 2025", pct(h.eu_share_2025), `Peak ${pct(h.eu_share_2022)} in 2022; China back to ${pct(h.eu_cn_2025)}`),
    kpi("US share, 2025", pct(h.us_share_2025), `From ${pct(h.us_share_2015)} in 2015; Vietnam ${pct(h.us_vn_2025)}`),
    kpi(`EU imports, Jan to ${monthName(h.eu_ytd_month)} 2026`, `<span class="down">${signPct(h.eu_ytd_change_bd)}</span>`,
        `In euros. Share ${pct(ytd.share_this_year)} vs ${pct(ytd.share_last_year)} a year earlier`, true),
    kpi("Duty if EU access is lost", eurBn(h.duty_lost_eur), `12% on 2025 sales; ${eurBn(h.duty_gsp_eur)} under GSP+`, true),
  ].join("");

  const ex = D.exposure;
  const knit = ex.filter(r => r.fabric === "Knit").reduce((s, r) => s + r.value_eur, 0);
  const total = ex.reduce((s, r) => s + r.value_eur, 0);
  const gsp = D.scenario_totals.find(r => r.scenario === "gsp_plus");
  document.getElementById("bet1").innerHTML =
    `Knitwear is ${eurBn(knit)} of ${eurBn(total)} Bangladesh sold to the EU in 2025 (${pct(knit / total, 0)}). It mostly uses local fabric, so it can pass GSP+'s two-stage origin rule. ` +
    `Under GSP+ the duty bill falls from ${eurBn(h.duty_lost_eur)} to ${eurBn(gsp.duty_eur)}.`;
  const us = g => D.share_group.find(r => r.market === "US" && r.group === g && r.exporter === "BD" && r.year === 2025);
  const usCN = (g, y) => D.share_group.find(r => r.market === "US" && r.group === g && r.exporter === "CN" && r.year === y);
  const tr = us("Trousers and shorts, woven"), sh = us("Shirts and blouses");
  document.getElementById("bet2").innerHTML =
    `Woven garments are the EU's weak spot: 60% of their fabric is imported, so they fail GSP+ origin. The US has no origin preference to lose and the UK now accepts imported fabric. ` +
    `Woven trousers are the US's biggest category (${usdBn(tr.world_usd)}); Bangladesh already has ${pct(tr.share)}, and ${pct(sh.share)} of shirts.`;
  const groups = ["Outerwear", "Underwear and nightwear", "Sweaters and sweatshirts"];
  const lines = groups.map(g => {
    const b = us(g), c19 = usCN(g, 2019), c25 = usCN(g, 2025);
    return `${g.toLowerCase()} (China ${pct(c19.share, 0)} → ${pct(c25.share, 0)}, Bangladesh ${pct(b.share, 0)})`;
  });
  document.getElementById("bet3").innerHTML =
    `China's US share has collapsed in ${lines.join("; ")}. Vietnam took most of it. These are largely synthetic-fibre products, where Bangladesh's cotton-based supply chain is thin.`;

  const c = chart("c-headline");
  const eu = D.share_market.filter(r => r.market === "EU" && r.exporter === "BD").sort((a, b) => a.year - b.year);
  const usr = D.share_market.filter(r => r.market === "US" && r.exporter === "BD").sort((a, b) => a.year - b.year);
  c.setOption({ ...base, grid: { ...base.grid, right: 70 },
    xAxis: { type: "category", data: eu.map(r => String(r.year)), ...axis },
    yAxis: { type: "value", ...axis, axisLabel: { ...axis.axisLabel, formatter: "{value}%" } },
    tooltip: { ...base.tooltip, valueFormatter: v => `${v.toFixed(1)}%` },
    series: [
      { name: "EU", type: "line", data: eu.map(r => r.share * 100), lineStyle: { width: 3, color: COLORS.BD }, itemStyle: { color: COLORS.BD }, showSymbol: false,
        endLabel: { show: true, formatter: p => `EU ${p.value.toFixed(1)}%`, color: INK, fontWeight: 700 } },
      { name: "US", type: "line", data: usr.map(r => r.share * 100), lineStyle: { width: 3, color: COLORS.CN }, itemStyle: { color: COLORS.CN }, showSymbol: false,
        endLabel: { show: true, formatter: p => `US ${p.value.toFixed(1)}%`, color: INK, fontWeight: 700 } },
    ] });
}

/* ---------- Market share ---------- */
let market = "EU";
function renderShare() {
  const seg = document.getElementById("seg-market");
  seg.innerHTML = Object.entries(D.meta.markets).map(([k, v]) => `<button data-m="${k}" class="${k === market ? "on" : ""}">${v}</button>`).join("");
  seg.querySelectorAll("button").forEach(b => b.onclick = () => { market = b.dataset.m; renderShare(); });
  document.getElementById("share-title").textContent = `Share of ${D.meta.markets[market]} apparel imports`;
  const c = chart("c-share");
  const years = [...new Set(D.share_market.map(r => r.year))].sort();
  c.setOption({ ...base, legend: { show: false },
    xAxis: { type: "category", data: years.map(String), ...axis },
    yAxis: { type: "value", ...axis, axisLabel: { ...axis.axisLabel, formatter: "{value}%" } },
    tooltip: { ...base.tooltip, valueFormatter: v => `${(+v).toFixed(1)}%` },
    series: shareSeries(market, ORDER) }, true);

  const at = (e, y) => (D.share_market.find(r => r.market === market && r.exporter === e && r.year === y) || {}).share;
  const gains = ORDER.map(e => ({ e, v: (at(e, 2025) - at(e, 2019)) * 100 })).sort((a, b) => a.v - b.v);
  chart("c-gain").setOption({ ...base, grid: { left: 90, right: 50, top: 10, bottom: 30 },
    xAxis: { type: "value", ...axis, axisLabel: { ...axis.axisLabel, formatter: "{value}" } },
    yAxis: { type: "category", data: gains.map(g => name(g.e)), ...axis, axisLabel: { color: INK, fontSize: 12 } },
    tooltip: { ...base.tooltip, trigger: "item", formatter: p => `${p.name}: ${p.value >= 0 ? "+" : ""}${p.value.toFixed(1)} points` },
    series: [{ type: "bar", barWidth: 22, data: gains.map(g => ({ value: g.v, itemStyle: { color: COLORS[g.e], borderRadius: g.v >= 0 ? [0, 4, 4, 0] : [4, 0, 0, 4] } })),
      label: { show: true, position: "right", color: INK, formatter: p => `${p.value >= 0 ? "+" : ""}${p.value.toFixed(1)}` } }] }, true);

  const rows = D.meta.groups.map(g => {
    const get = (e, y) => D.share_group.find(r => r.market === market && r.group === g && r.exporter === e && r.year === y);
    const b25 = get("BD", 2025);
    if (!b25) return "";
    const d = e => { const a = get(e, 2025), b = get(e, 2019); return a && b ? (a.share - b.share) : null; };
    const chip = v => v == null ? "-" : `<span class="chip ${v > 0.005 ? "g" : v < -0.005 ? "r" : "n"}">${pp(v)}</span>`;
    return `<tr><td>${g}</td><td class="n">${usdBn(b25.world_usd)}</td><td class="n"><b>${pct(b25.share)}</b></td>` +
           ORDER.map(e => `<td class="n">${chip(d(e))}</td>`).join("") + "</tr>";
  }).join("");
  document.getElementById("groups-hint").textContent = market === "EU"
    ? "Share in 2025 and change since 2019, points. EU product detail leaves out EUR 4bn (4.5%) recorded without product codes, mostly from China."
    : "Share in 2025 and change since 2019, percentage points";
  document.getElementById("t-groups").innerHTML =
    `<tr><th>Product group</th><th class="n">Market size 2025</th><th class="n">Bangladesh share</th>${ORDER.map(e => `<th class="n">${name(e)}</th>`).join("")}</tr>${rows}`;
}

/* ---------- Price ---------- */
let pmarket = "US", pgroup = "T-shirts and vests";
function renderPrice() {
  const seg = document.getElementById("seg-pmarket");
  seg.innerHTML = Object.entries(D.meta.markets).map(([k, v]) => `<button data-m="${k}" class="${k === pmarket ? "on" : ""}">${v}</button>`).join("");
  seg.querySelectorAll("button").forEach(b => b.onclick = () => { pmarket = b.dataset.m; renderPrice(); });
  const sel = document.getElementById("sel-group");
  sel.innerHTML = D.meta.groups.map(g => `<option ${g === pgroup ? "selected" : ""}>${g}</option>`).join("");
  sel.onchange = () => { pgroup = sel.value; renderPrice(); };
  const eu = pmarket === "EU", key = eu ? "eur_per_kg" : "usd_per_item";
  document.getElementById("price-title").textContent = `${pgroup}: ${eu ? "price per kilogram" : "price per item"}, ${D.meta.markets[pmarket]}`;
  document.getElementById("price-hint").textContent = eu ? "EUR per kg" : "USD per item";
  const years = [...new Set(D.unit_value.map(r => r.year))].sort();
  const fmt = v => eu ? `EUR ${v.toFixed(1)}` : `$${v.toFixed(2)}`;
  chart("c-price").setOption({ ...base,
    xAxis: { type: "category", data: years.map(String), ...axis }, yAxis: { type: "value", ...axis },
    tooltip: { ...base.tooltip, valueFormatter: v => v == null ? "-" : fmt(+v) },
    series: ORDER.map(e => ({ name: name(e), type: "line", showSymbol: false, z: e === "BD" ? 5 : 2,
      lineStyle: { width: e === "BD" ? 3.5 : 2, color: COLORS[e] }, itemStyle: { color: COLORS[e] },
      endLabel: { show: true, formatter: p => `${name(e)} ${fmt(p.value)}`, color: INK, fontSize: 11.5, fontWeight: e === "BD" ? 700 : 500 },
      labelLayout: { moveOverlap: "shiftY" },
      data: years.map(y => { const r = D.unit_value.find(u => u.market === pmarket && u.group === pgroup && u.exporter === e && u.year === y); return r && r[key] ? r[key] : null; }),
    })) }, true);
  const rel = D.meta.groups.filter(g => !g.startsWith("Other")).map(g => {
    const f = e => (D.unit_value.find(u => u.market === pmarket && u.group === g && u.exporter === e && u.year === 2025) || {})[key];
    const b = f("BD"), v = f("VN");
    return b && v ? { g, v: b / v * 100 } : null;
  }).filter(Boolean).sort((a, b) => a.v - b.v);
  chart("c-relprice").setOption({ ...base, grid: { left: 210, right: 50, top: 34, bottom: 30 },
    xAxis: { type: "value", ...axis, max: v => Math.max(110, Math.ceil(v.max / 10) * 10) },
    yAxis: { type: "category", data: rel.map(r => r.g), ...axis, axisLabel: { color: INK, fontSize: 11.5 } },
    tooltip: { ...base.tooltip, trigger: "item", formatter: p => `${p.name}: Bangladesh at ${p.value.toFixed(0)}% of Vietnam's price` },
    series: [{ type: "bar", barWidth: 16, data: rel.map(r => ({ value: r.v, itemStyle: { color: COLORS.BD, borderRadius: [0, 4, 4, 0] } })),
      label: { show: true, position: "right", color: INK, formatter: p => p.value.toFixed(0) },
      markLine: { symbol: "none", data: [{ xAxis: 100 }], lineStyle: { color: COLORS.VN, type: "dashed", width: 2 },
                  label: { formatter: "Vietnam", color: COLORS.VN, fontWeight: 700 } } }] }, true);
}

/* ---------- Tariffs ---------- */
let scen = "lost";
function renderTariff() {
  const seg = document.getElementById("seg-scen");
  seg.innerHTML = Object.entries(D.meta.scenarios).map(([k, v]) => `<button data-s="${k}" class="${k === scen ? "on" : ""}">${v.label}</button>`).join("");
  seg.querySelectorAll("button").forEach(b => b.onclick = () => { scen = b.dataset.s; renderTariff(); });
  document.getElementById("scen-note").textContent = D.meta.scenarios[scen].note;
  const t = D.scenario_totals.find(r => r.scenario === scen);
  document.getElementById("scen-kpis").innerHTML = [
    kpi("Bangladesh's EU sales, 2025", eurBn(t.value_eur), "The base for every scenario"),
    kpi("Duty on that trade", eurBn(t.duty_eur), `Effective rate ${t.effective_rate.toFixed(1)}%`, scen !== "kept"),
    kpi("Sales at risk", t.duty_eur ? `EUR ${(t.exports_at_risk_low / 1e9).toFixed(1)} to ${(t.exports_at_risk_high / 1e9).toFixed(1)}bn` : "None",
        `Against duty-free competitors, σ = ${D.meta.sigma.join(" to ")}`, scen !== "kept"),
    kpi("Share of EU sales at risk", t.duty_eur ? `${pct(t.exports_at_risk_low / t.value_eur, 0)} to ${pct(t.exports_at_risk_high / t.value_eur, 0)}` : "0%",
        "A range, not a forecast"),
  ].join("");
  const rows = D.scenario_groups.filter(r => r.scenario === scen).sort((a, b) => a.duty_eur - b.duty_eur);
  chart("c-duty").setOption({ ...base, grid: { left: 210, right: 70, top: 10, bottom: 30 },
    xAxis: { type: "value", ...axis },
    yAxis: { type: "category", data: rows.map(r => r.group), ...axis, axisLabel: { color: INK, fontSize: 11.5 } },
    tooltip: { ...base.tooltip, trigger: "item", formatter: p => { const r = rows[p.dataIndex];
      return `${r.group}<br>Sales EUR ${(r.value_eur / 1e6).toFixed(0)}m · duty EUR ${(r.duty_eur / 1e6).toFixed(0)}m (${r.effective_rate.toFixed(1)}%)`; } },
    series: [{ type: "bar", barWidth: 16, data: rows.map(r => ({ value: r.duty_eur / 1e6, itemStyle: { color: "#42506a", borderRadius: [0, 4, 4, 0] } })),
      label: { show: true, position: "right", color: INK, formatter: p => p.value.toFixed(0) } }] }, true);
  document.getElementById("t-regimes").innerHTML = "<tr><th>Exporter</th><th>Today</th><th>After 2032</th></tr>" +
    D.regimes.map(r => `<tr><td><b>${name(r.exporter)}</b></td><td>${r.today}<div class="sub">${r.tariff_today}</div></td><td><a href="${r.source}" target="_blank" rel="noopener">${r.after_2032}</a></td></tr>`).join("");
}

/* ---------- 2026 so far ---------- */
function renderNow() {
  const h = D.headline, ytd = Object.fromEntries(D.eu_ytd.map(r => [r.exporter, r]));
  const mn = monthName(h.eu_ytd_month);
  document.getElementById("ytd-title").textContent = `January to ${mn} 2026 against the same months of 2025`;
  document.getElementById("now-kpis").innerHTML = [
    kpi(`Bangladesh, Jan to ${mn.slice(0, 3)}`, `<span class="down">${signPct(h.eu_ytd_change_bd)}</span>`, `${eurBn(ytd.BD.this_year)} against ${eurBn(ytd.BD.last_year)}`, true),
    kpi("China", `<span class="up">${signPct(h.eu_ytd_change_cn)}</span>`, `${eurBn(ytd.CN.this_year)}`),
    kpi("Vietnam", `<span class="up">${signPct(h.eu_ytd_change_vn)}</span>`, `${eurBn(ytd.VN.this_year)}`),
    kpi("Bangladesh's share", pct(ytd.BD.share_this_year), `${pct(ytd.BD.share_last_year)} in the same months of 2025`, true),
  ].join("");
  const months = [...new Set(D.eu_monthly.map(r => r.month))].sort();
  chart("c-month").setOption({ ...base,
    xAxis: { type: "category", data: months, ...axis, axisLabel: { ...axis.axisLabel, formatter: v => v.endsWith("-01") ? v.slice(0, 4) : v.slice(5) } },
    yAxis: { type: "value", ...axis },
    tooltip: { ...base.tooltip, valueFormatter: v => `EUR ${(+v).toFixed(2)}bn` },
    series: ["CN", "BD", "VN"].map(e => ({ name: name(e), type: "line", showSymbol: false, lineStyle: { width: e === "BD" ? 3.5 : 2, color: COLORS[e] },
      itemStyle: { color: COLORS[e] }, endLabel: { show: true, formatter: name(e), color: INK, fontWeight: e === "BD" ? 700 : 500 },
      data: months.map(m => { const r = D.eu_monthly.find(x => x.exporter === e && x.month === m); return r ? r.value_eur / 1e9 : null; }) })) }, true);
  const ex = [...ORDER, "WORLD"].map(e => ({ e, v: ytd[e].change * 100 })).sort((a, b) => a.v - b.v);
  chart("c-ytd").setOption({ ...base, grid: { left: 90, right: 60, top: 10, bottom: 30 },
    xAxis: { type: "value", ...axis, axisLabel: { ...axis.axisLabel, formatter: "{value}%" } },
    yAxis: { type: "category", data: ex.map(x => x.e === "WORLD" ? "All suppliers" : name(x.e)), ...axis, axisLabel: { color: INK, fontSize: 12 } },
    tooltip: { ...base.tooltip, trigger: "item", formatter: p => `${p.name}: ${p.value >= 0 ? "+" : ""}${p.value.toFixed(1)}%` },
    series: [{ type: "bar", barWidth: 20, data: ex.map(x => ({ value: x.v, itemStyle: { color: COLORS[x.e] || "#9aa6b8", borderRadius: x.v >= 0 ? [0, 4, 4, 0] : [4, 0, 0, 4] } })),
      label: { show: true, position: "right", color: INK, formatter: p => `${p.value >= 0 ? "+" : ""}${p.value.toFixed(1)}%` } }] }, true);
}

const RENDER = { answer: renderAnswer, share: renderShare, price: renderPrice, tariff: renderTariff, now: renderNow, method: () => {} };
function show(tab) {
  document.querySelectorAll(".tabs button").forEach(b => b.classList.toggle("on", b.dataset.tab === tab));
  document.querySelectorAll(".page").forEach(p => p.classList.toggle("on", p.id === `p-${tab}`));
  RENDER[tab]();
  Object.values(charts).forEach(c => c.resize());
  if (location.hash !== `#${tab}`) history.replaceState(null, "", `#${tab}`);
}

fetch("data/apparel.json").then(r => r.json()).then(d => {
  D = d;
  document.getElementById("sub").textContent = `Where to compete next, by product and market · trade ${d.meta.years[0]} to ${d.meta.years[1]}, EU monthly to ${monthName(d.headline.eu_ytd_month)} 2026`;
  document.getElementById("gen").textContent = `Data built ${d.meta.generated}`;
  document.querySelectorAll(".tabs button").forEach(b => b.onclick = () => show(b.dataset.tab));
  const start = location.hash.slice(1);
  show(RENDER[start] ? start : "answer");
  window.addEventListener("resize", () => Object.values(charts).forEach(c => c.resize()));
});
