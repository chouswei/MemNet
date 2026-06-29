/** Skills foreground panel — sheet (MWU/WUX) and setup catalog picks. */
window.NovelSkillsPanel = (function () {
  const C = window.NovelSheetCommon;
  const TAB = "skills";
  const IDS = {
    overlay: "skills-overlay",
    title: "skills-sheet-title",
    body: "skills-sheet-body",
    panel: "skills-panel",
    actions: "skills-actions",
    close: "skills-sheet-close",
    backdrop: "skills-sheet-backdrop",
  };
  const DEFAULT_TITLE = "技能";

  let selected = null;
  let open = false;
  let bound = false;
  let setupBusy = false;

  function panel() {
    return document.getElementById(IDS.panel);
  }

  function artDisplayName(art) {
    return art["名稱"] || art.name || art.art_id || art.id || "";
  }

  function skillLabel(art) {
    const name = artDisplayName(art);
    const rank = (art.rank || "").trim();
    return rank ? name + "·" + rank : name;
  }

  function clearSelection() {
    selected = null;
    const el = document.getElementById(IDS.actions);
    if (el) {
      el.innerHTML = "";
      el.classList.add("hidden");
    }
    panel()?.querySelectorAll(".skill-btn").forEach((b) => b.classList.remove("selected"));
  }

  function close() {
    open = false;
    C.closeOverlay(IDS);
    clearSelection();
    C.updateTabBar(null);
  }

  function openPanel(titleOverride) {
    open = true;
    C.openOverlay(IDS, IDS.title, titleOverride || DEFAULT_TITLE);
    C.updateTabBar(TAB);
  }

  function isOpen() {
    return open;
  }

  function bind() {
    if (bound) return;
    bound = true;
    C.bindOverlay(IDS, close);
  }

  function setSetupBusy(on) {
    setupBusy = on;
    panel()?.querySelectorAll(".skill-btn, .reroll-btn").forEach((b) => {
      b.disabled = on;
    });
  }

  function render(arts, bodyStats) {
    clearSelection();
    const el = panel();
    el.innerHTML = "";
    if (!arts.length && !bodyStats.length) {
      el.appendChild(C.emptyHint("尚無技能"));
      return;
    }
    if (arts.length) {
      el.appendChild(C.sectionTitle("技能"));
      arts.forEach((art) => appendSkillBtn(el, art, skillLabel(art), artDisplayName(art)));
    }
    if (bodyStats.length) {
      el.appendChild(C.sectionTitle("根基"));
      bodyStats.forEach((stat) => {
        const label = stat.kind + (stat.rank ? "·" + stat.rank : "");
        appendSkillBtn(el, stat, label, stat.kind);
      });
    }
  }

  function appendSkillBtn(el, entry, label, actionName) {
    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = "skill-btn";
    btn.textContent = label;
    btn.addEventListener("click", () => {
      const key = entry.id;
      if (selected === key) {
        clearSelection();
        return;
      }
      el.querySelectorAll(".skill-btn").forEach((b) => b.classList.remove("selected"));
      btn.classList.add("selected");
      selected = key;
      C.renderSubActions(IDS.actions, entry.actions || []);
    });
    el.appendChild(btn);
  }

  function renderSetupOffers(slot, arts) {
    const el = panel();
    el.querySelectorAll(".skill-btn").forEach((node) => node.remove());
    el.querySelectorAll("p.empty-offers").forEach((node) => node.remove());
    if (!arts.length) {
      const p = document.createElement("p");
      p.className = "empty-offers";
      p.textContent = "尚無可選項目";
      el.appendChild(p);
      return;
    }
    arts.forEach((art) => {
      const btn = document.createElement("button");
      btn.type = "button";
      btn.className = "skill-btn";
      btn.textContent = skillLabel(art);
      btn.addEventListener("click", async () => {
        if (setupBusy) return;
        setSetupBusy(true);
        window.NovelApp.hideError();
        try {
          await window.NovelApp.api("/api/setup/pick", {
            method: "POST",
            body: JSON.stringify({ slot, art_id: art.id }),
          });
          await window.NovelApp.refreshSetup();
        } catch (err) {
          const msg =
            err.body?.errors?.join(" ") ||
            err.body?.detail?.errors?.join(" ") ||
            err.message ||
            "選擇失敗";
          window.NovelApp.showError(msg);
        } finally {
          setSetupBusy(false);
        }
      });
      el.appendChild(btn);
    });
  }

  async function rerollSetupOffers(slot) {
    setSetupBusy(true);
    window.NovelApp.hideError();
    try {
      const result = await window.NovelApp.api("/api/setup/reroll", {
        method: "POST",
        body: JSON.stringify({ slot }),
      });
      const slotData = (result.slots || {})[slot] || {};
      renderSetupOffers(slot, slotData.arts || []);
      return result;
    } catch (err) {
      const msg =
        err.body?.errors?.join(" ") ||
        err.body?.detail?.errors?.join(" ") ||
        err.message ||
        "重新骰選失敗";
      window.NovelApp.showError(msg);
      throw err;
    } finally {
      setSetupBusy(false);
    }
  }

  async function loadSetupOffers(slot) {
    setSetupBusy(true);
    try {
      const cat = await window.NovelApp.api("/api/catalog");
      const el = panel();
      el.innerHTML = "";
      const slotData = (cat.slots || {})[slot] || {};
      const arts = slotData.arts || [];
      const rerollBtn = document.createElement("button");
      rerollBtn.type = "button";
      rerollBtn.className = "reroll-btn";
      rerollBtn.textContent = "重新骰選";
      rerollBtn.addEventListener("click", () => rerollSetupOffers(slot));
      el.appendChild(rerollBtn);
      renderSetupOffers(slot, arts);
    } catch (err) {
      const msg =
        err.body?.errors?.join(" ") ||
        err.body?.detail?.errors?.join(" ") ||
        err.message ||
        "載入選項失敗";
      window.NovelApp.showError(msg);
    } finally {
      setSetupBusy(false);
    }
  }

  function showSetupTab() {
    document.getElementById("tab-bar").classList.remove("hidden");
    document.querySelectorAll("#tab-bar button").forEach((b) => {
      const on = b.dataset.tab === TAB;
      b.classList.toggle("hidden", !on);
    });
    bind();
    openPanel("選擇技能");
  }

  const api = {
    TAB,
    bind,
    open: openPanel,
    close,
    isOpen,
    render,
    loadSetupOffers,
    showSetupTab,
  };
  C.register(api);
  return api;
})();
