/** Shared helpers and overlay lifecycle for items / skills / production panels. */
window.NovelSheetCommon = (function () {
  const registry = [];

  function emptyHint(msg) {
    const p = document.createElement("p");
    p.className = "empty-hint";
    p.textContent = msg;
    return p;
  }

  function sectionTitle(text) {
    const h = document.createElement("h3");
    h.className = "sheet-section-title";
    h.textContent = text;
    return h;
  }

  function prefillAndClose(template) {
    const ta = document.getElementById("input-text");
    ta.value = template;
    closeAll();
    ta.focus();
  }

  function register(panel) {
    registry.push(panel);
  }

  function closeAll() {
    registry.forEach((p) => p.close());
    if (window.NovelPartyPanel && window.NovelPartyPanel.isOpen()) {
      window.NovelPartyPanel.close();
    }
  }

  function isAnyOpen() {
    const partyOpen = window.NovelPartyPanel && window.NovelPartyPanel.isOpen();
    return registry.some((p) => p.isOpen()) || partyOpen;
  }

  function updateTabBar(activeTab) {
    document.querySelectorAll("#tab-bar button").forEach((b) => {
      const on = activeTab === b.dataset.tab;
      b.setAttribute("aria-selected", on ? "true" : "false");
      b.setAttribute("aria-pressed", on ? "true" : "false");
    });
  }

  function bindEscape() {
    if (bindEscape.done) return;
    bindEscape.done = true;
    document.addEventListener("keydown", (e) => {
      if (e.key === "Escape" && isAnyOpen()) closeAll();
    });
  }

  function bindOverlay(ids, onClose) {
    document.getElementById(ids.close).addEventListener("click", onClose);
    document.getElementById(ids.backdrop).addEventListener("click", onClose);
  }

  function openOverlay(ids, title, titleText) {
    closeAll();
    const overlay = document.getElementById(ids.overlay);
    overlay.classList.remove("hidden");
    overlay.setAttribute("aria-hidden", "false");
    document.getElementById(ids.title).textContent = titleText;
    const body = document.getElementById(ids.body);
    if (body) body.scrollTop = 0;
    return overlay;
  }

  function closeOverlay(ids) {
    const overlay = document.getElementById(ids.overlay);
    if (!overlay) return;
    overlay.classList.add("hidden");
    overlay.setAttribute("aria-hidden", "true");
  }

  function renderSubActions(actionsId, actions) {
    const el = document.getElementById(actionsId);
    el.innerHTML = "";
    (actions || []).forEach((act) => {
      const btn = document.createElement("button");
      btn.type = "button";
      btn.textContent = act.label;
      btn.addEventListener("click", () => prefillAndClose(act.template || act.label));
      el.appendChild(btn);
    });
    el.classList.toggle("hidden", !actions || !actions.length);
  }

  return {
    emptyHint,
    sectionTitle,
    prefillAndClose,
    register,
    closeAll,
    isAnyOpen,
    updateTabBar,
    bindEscape,
    bindOverlay,
    openOverlay,
    closeOverlay,
    renderSubActions,
  };
})();
