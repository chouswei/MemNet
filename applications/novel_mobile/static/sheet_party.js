/** Party view in narrative pane (scrollable story area) — USR-driven roster display. */
window.NovelPartyPanel = (function () {
  const C = window.NovelSheetCommon;
  const TAB = "party";
  const PANEL_ID = "narrative-party";

  let open = false;
  let panelData = null;
  let selectedId = null;

  function panel() {
    return document.getElementById(PANEL_ID);
  }

  function setStoryHidden(hidden) {
    document.getElementById("narrative").classList.toggle("hidden", hidden);
    const hud = document.getElementById("narrative-hud");
    if (hidden) {
      hud.classList.add("hidden");
    } else if (hud.textContent.trim()) {
      hud.classList.remove("hidden");
      hud.style.display = "";
    } else {
      hud.classList.add("hidden");
    }
    const opts = document.getElementById("narrative-options");
    if (hidden) {
      opts.classList.add("hidden");
    } else if (opts.innerHTML.trim()) {
      opts.classList.remove("hidden");
    }
    panel().classList.toggle("hidden", !hidden);
  }

  function close() {
    open = false;
    selectedId = null;
    setStoryHidden(false);
    C.updateTabBar(null);
  }

  async function openPanel() {
    C.closeAll();
    open = true;
    setStoryHidden(true);
    C.updateTabBar(TAB);
    const pane = document.getElementById("narrative-pane");
    if (pane) pane.scrollTop = 0;
    try {
      const data = await window.NovelApp.api("/api/party/panel");
      render(data);
    } catch {
      render({ members: [], ui_note: "" });
    }
  }

  function isOpen() {
    return open;
  }

  function bind() {
    /* tab wired in sheet.js */
  }

  function line(text, className) {
    const p = document.createElement("p");
    p.className = className || "party-line";
    p.textContent = text;
    return p;
  }

  function relDimLine(label, value) {
    const n = Number(value);
    const cls =
      !Number.isNaN(n) && n < 0 ? "party-rel-dim party-rel-negative" : "party-rel-dim";
    return line(label + "：" + value, cls);
  }

  function renderMemberDetail(member, panelData) {
    const wrap = document.createElement("div");
    wrap.className = "party-member-detail";

    const plrName = (panelData && panelData.plr_name) || "你";
    const memberName = member.name || member.id || "同伴";

    const sections = member.sections || [];
    if (sections.includes("attrs") && member.attrs && member.attrs.length) {
      wrap.appendChild(C.sectionTitle("屬性"));
      member.attrs.forEach((a) => {
        wrap.appendChild(line(a.label + "：" + a.value));
      });
    }

    if (sections.includes("summary") && member.summary) {
      if (member.summary.skills) {
        wrap.appendChild(C.sectionTitle("技能摘要"));
        wrap.appendChild(line(member.summary.skills));
      }
      if (member.summary.items) {
        wrap.appendChild(C.sectionTitle("物品摘要"));
        wrap.appendChild(line(member.summary.items));
      }
    }

    if (sections.includes("skills")) {
      if (member.skills && member.skills.length) {
        wrap.appendChild(C.sectionTitle("技能"));
        member.skills.forEach((s) => {
          const rank = s.rank ? "·" + s.rank : "";
          wrap.appendChild(line("· " + s.name + rank));
        });
      }
      if (member.body_stats && member.body_stats.length) {
        wrap.appendChild(C.sectionTitle("根基"));
        member.body_stats.forEach((s) => {
          const rank = s.rank ? "·" + s.rank : "";
          wrap.appendChild(line("· " + s.kind + rank));
        });
      }
    }

    if (sections.includes("items") && member.items && member.items.length) {
      wrap.appendChild(C.sectionTitle("物品"));
      member.items.forEach((it) => {
        wrap.appendChild(line("· " + it.name + "×" + it.qty));
      });
    }

    if (sections.includes("relations") && member.relations) {
      const rel = member.relations;
      const outbound = rel.plr_to_member || rel.to_member;
      const inbound = rel.member_to_plr || rel.from_member;
      if ((outbound && outbound.dims && outbound.dims.length) || (inbound && inbound.dims && inbound.dims.length)) {
        wrap.appendChild(line("有向分數，雙向可不一致。", "party-rel-hint"));
      }
      if (outbound && outbound.dims && outbound.dims.length) {
        wrap.appendChild(C.sectionTitle(plrName + " → " + memberName));
        outbound.dims.forEach((d) => {
          wrap.appendChild(relDimLine(d.label, d.value));
        });
        if (outbound.note) {
          wrap.appendChild(line(outbound.note, "party-rel-note"));
        }
      }
      if (inbound && inbound.dims && inbound.dims.length) {
        wrap.appendChild(C.sectionTitle(memberName + " → " + plrName));
        inbound.dims.forEach((d) => {
          wrap.appendChild(relDimLine(d.label, d.value));
        });
        if (inbound.note) {
          wrap.appendChild(line(inbound.note, "party-rel-note"));
        }
      }
    }

    if (!wrap.childNodes.length) {
      wrap.appendChild(C.emptyHint("此成員無可顯示資料"));
    }
    return wrap;
  }

  function render(data) {
    panelData = data;
    selectedId = null;
    const el = panel();
    if (!el) return;
    el.innerHTML = "";

    const heading = document.createElement("h2");
    heading.className = "narrative-party-title";
    heading.textContent = "【隊伍】";
    el.appendChild(heading);

    const members = data.members || [];
    if (!members.length) {
      el.appendChild(C.emptyHint("尚無隊伍成員"));
      return;
    }

    if (data.ui_note) {
      const note = document.createElement("p");
      note.className = "party-ui-note";
      note.textContent = data.ui_note;
      el.appendChild(note);
    }

    const picker = document.createElement("div");
    picker.className = "party-member-picker";
    members.forEach((member) => {
      const btn = document.createElement("button");
      btn.type = "button";
      btn.className = "party-member-btn";
      const role = member.role === "plr" ? "主角" : member.role === "npc" ? "同伴" : "";
      btn.textContent = role ? member.name + "（" + role + "）" : member.name;
      btn.addEventListener("click", () => {
        selectedId = member.id;
        picker.querySelectorAll(".party-member-btn").forEach((b) => b.classList.remove("selected"));
        btn.classList.add("selected");
        const detailHost = el.querySelector(".party-member-detail-host");
        if (detailHost) {
          detailHost.innerHTML = "";
          detailHost.appendChild(renderMemberDetail(member, panelData));
        }
      });
      picker.appendChild(btn);
    });
    el.appendChild(picker);

    const detailHost = document.createElement("div");
    detailHost.className = "party-member-detail-host";
    el.appendChild(detailHost);

    const first = members[0];
    selectedId = first.id;
    picker.querySelector(".party-member-btn")?.classList.add("selected");
    detailHost.appendChild(renderMemberDetail(first, panelData));
  }

  return { TAB, bind, open: openPanel, close, isOpen, render };
})();
