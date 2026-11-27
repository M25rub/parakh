/* OWNER: Person 1. Shared logic for all pages: talks to the server and draws trace + results.
   You can restyle everything in style.css without touching this file. */
const Parakh = (() => {
  const RISK_LABEL = {
    likely_scam: "Likely scam", suspicious: "Suspicious",
    verified: "Verified", not_opportunity: "Not an opportunity",
  };
  const STATUS_ICON = { pass: "✓", warn: "!", fail: "✕", unverified: "?", skipped: "–" };

  const $ = (id) => document.getElementById(id);
  const el = (tag, cls, text) => {
    const n = document.createElement(tag);
    if (cls) n.className = cls;
    if (text !== undefined) n.textContent = text;
    return n;
  };

  async function showMockBadge() {
    try {
      const r = await fetch("/api/health");
      const h = await r.json();
      if (h.mock && $("mock-badge")) $("mock-badge").hidden = false;
    } catch (_) { /* server down: ignore */ }
  }

  function addTrace(ev) {
    const li = el("li", `trace-item trace-${ev.kind}${ev.via_mcp ? " trace-mcp" : ""}`);
    if (ev.via_mcp) li.append(el("span", "trace-mcp-tag", `${ev.via_mcp} MCP`));
    if (ev.tool) li.append(el("span", "trace-tool", ev.tool));
    li.append(el("span", "trace-msg", ev.message));
    $("trace").append(li);
    li.scrollIntoView({ block: "nearest", behavior: "smooth" });
  }

  function renderVerdict(v) {
    const card = el("article", `verdict verdict-${v.risk}`);
    const head = el("header", "verdict-head");
    head.append(el("span", `risk-badge risk-${v.risk}`, RISK_LABEL[v.risk] || v.risk));
    head.append(el("span", "confidence", `${Math.round(v.confidence * 100)}% confident`));
    card.append(head);
    card.append(el("h3", "verdict-subject", v.subject || "(no subject)"));
    card.append(el("p", "verdict-sender", v.sender));
    if (v.memory_hit) card.append(el("p", "memory-hit", "Recognised from shared scam memory"));
    card.append(el("p", "verdict-explanation", v.explanation));
    if (v.gmail_label_applied) card.append(el("p", "label-applied", `Gmail label: ${v.gmail_label_applied}`));

    const ev = el("details", "evidence");
    ev.append(el("summary", "evidence-title", `Evidence (${v.checks.length} checks)`));
    const list = el("ul", "evidence-list");
    v.checks.forEach((c) => {
      const li = el("li", `check check-${c.status}`);
      li.append(el("span", "check-icon", STATUS_ICON[c.status] || "?"));
      li.append(el("span", "check-name", c.check.replace(/_/g, " ")));
      li.append(el("span", "check-summary", c.summary));
      list.append(li);
    });
    ev.append(list);
    card.append(ev);
    $("results").append(card);

    if (v.deadline && $("deadlines")) {
      const d = el("li", "deadline");
      d.append(el("span", "deadline-date", v.deadline.date));
      d.append(el("span", "deadline-title", v.deadline.title));
      if (v.deadline.calendar_event_created) d.append(el("span", "deadline-cal", "Added to Google Calendar"));
      $("deadlines").append(d);
    }
  }

  function showError(msg) {
    $("results").append(el("p", "error", `Something went wrong: ${msg}`));
  }

  // Calls the server and reads the live stream of 'trace', 'result' and 'error' events.
  async function run(url, options, button) {
    $("trace").innerHTML = ""; $("results").innerHTML = "";
    if ($("deadlines")) $("deadlines").innerHTML = "";
    if (button) { button.disabled = true; button.classList.add("loading"); }
    try {
      const resp = await fetch(url, options);
      const reader = resp.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";
      while (true) {
        const { value, done } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        let cut;
        while ((cut = buffer.indexOf("\n\n")) !== -1) {
          const chunk = buffer.slice(0, cut); buffer = buffer.slice(cut + 2);
          const kind = (chunk.match(/^event: (.*)$/m) || [])[1];
          const data = JSON.parse((chunk.match(/^data: (.*)$/m) || [])[1] || "{}");
          if (kind === "trace") addTrace(data);
          else if (kind === "result") data.verdicts.forEach(renderVerdict);
          else if (kind === "error") showError(data.message);
        }
      }
    } catch (e) {
      showError(e.message);
    } finally {
      if (button) { button.disabled = false; button.classList.remove("loading"); }
    }
  }

  return { run, showMockBadge };
})();
