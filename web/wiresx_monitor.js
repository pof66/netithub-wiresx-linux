/* Copyright 2026 IU0NDT. SPDX-License-Identifier: Apache-2.0. */
"use strict";
const state = { payload: null };
const el = (id) => document.getElementById(id);
const node = (tag, text, className) => {
  const result = document.createElement(tag);
  result.textContent = String(text);
  if (className) result.className = className;
  return result;
};
function renderYears(s) {
  const target = el("year-chart"); target.replaceChildren();
  const entries = Object.entries(s.years || {}).sort((a,b) => Number(b[0]) - Number(a[0]));
  const max = Math.max(1, ...entries.map(([,v]) => Number(v)));
  for (const [year,count] of entries) {
    const line = node("div", "", "year-line" + (year === "2000" ? " is-placeholder" : ""));
    line.append(node("span",year,"year-label"));
    const track = node("div","","bar-track"), bar = node("div","","bar-fill");
    bar.style.width = (100 * Number(count) / max) + "%"; track.append(bar);
    line.append(track, node("span",count,"year-count")); target.append(line);
  }
  if (!entries.length) target.append(node("p", "Nessuna data disponibile.", "muted"));
  const old = el("year").value, select=el("year");
  select.replaceChildren(new Option("TUTTI GLI ANNI", ""));
  for (const [year] of entries) select.add(new Option(year === "2000" ? "2000 (da verificare)" : year, year));
  select.value = entries.some(([year]) => year === old) ? old : "";
}
function renderChannels(s) {
  const target=el("channel-list"); target.replaceChildren();
  for(const [channel,count] of Object.entries(s.receive_channels || {})) {
    const row=node("div","","channel-item");
    row.append(node("span",channel),node("span",count)); target.append(row);
  }
}
function renderRows() {
  const data=state.payload; if(!data)return;
  const query=el("search").value.trim().toLowerCase(), year=el("year").value;
  const gps=el("gps-only").checked;
  const rows=(data.rows||[]).filter(row =>
    (!year || String(row.year)===year) && (!gps || row.has_position) &&
    (!query || row.station.toLowerCase().includes(query) || row.channel.toLowerCase().includes(query))
  );
  const target=el("rows"); target.replaceChildren();
  if (!rows.length) {
    const tr=node("tr", ""); const td=node("td","Nessuna registrazione con questi filtri.","empty");
    td.colSpan=4;tr.append(td);target.append(tr);
  }
  for (const record of rows) {
    const tr=node("tr", "");
    tr.append(node("td",record.station),node("td",record.received),node("td",record.channel),
              node("td",record.has_position ? "PRESENTE" : "—",record.has_position ? "geo-tag" : ""));
    target.append(tr);
  }
  el("list-count").textContent=rows.length+" VOCI";
  el("truncated").textContent=data.truncated ? "Elenco limitato alle prime 500 righe." : "";
}
function render(data) {
  state.payload=data;
  const s=data.summary;
  el("m-total").textContent=s.total_rows;
  el("m-valid").textContent=s.other_dated_rows;
  el("m-gps").textContent=s.records_with_valid_coordinates;
  el("m-latest").textContent=s.latest_non_2000_received || "NON DISPONIBILE";
  el("privacy").textContent=data.identifiers_visible ? "NOMINATIVI VISIBILI / SOLO LOCALE" : "IDENTITÀ OSCURATE";
  renderYears(s);renderChannels(s);renderRows();
}
async function refresh() {
  try {
    const res=await fetch("/api/lastheard",{cache:"no-store"});
    if(!res.ok)throw new Error("HTTP " + res.status);
    const data=await res.json();
    if(data.schema !== "netithub-wiresx-lastheard-v1")throw new Error("Formato JSON sconosciuto");
    render(data);
    el("last-check").textContent="SYNC: "+new Date().toLocaleTimeString("it-IT");
  } catch (error) {
    el("last-check").textContent="LOG NON DISPONIBILE";
    if(!state.payload){const tbody=el("rows");tbody.replaceChildren();const tr=node("tr","");const td=node("td", "Errore di lettura. Controllare file log e console locale.","empty");td.colSpan=4;tr.append(td);tbody.append(tr);}
  }
}
for (const id of ["search","year","gps-only"]) el(id).addEventListener("input",renderRows);
refresh();setInterval(refresh,15000);
