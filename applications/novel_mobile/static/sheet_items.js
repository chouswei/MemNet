/** Items foreground panel — inventory from player sheet. */
window.NovelItemsPanel = (function () {
  const C = window.NovelSheetCommon;
  const TAB = "items";
  const IDS = {
    overlay: "items-overlay",
    title: "items-sheet-title",
    body: "items-sheet-body",
    panel: "items-panel",
    actions: "items-actions",
    close: "items-sheet-close",
    backdrop: "items-sheet-backdrop",
  };
  const DEFAULT_TITLE = "物品";

  let selected = null;
  let open = false;
  let bound = false;

  function panel() {
    return document.getElementById(IDS.panel);
  }

  function clearSelection() {
    selected = null;
    const el = document.getElementById(IDS.actions);
    if (el) {
      el.innerHTML = "";
      el.classList.add("hidden");
    }
    panel()?.querySelectorAll(".item-btn").forEach((b) => b.classList.remove("selected"));
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

  function render(items) {
    clearSelection();
    const el = panel();
    el.innerHTML = "";
    if (!items.length) {
      el.appendChild(C.emptyHint("尚無物品"));
      return;
    }
    items.forEach((item) => {
      const btn = document.createElement("button");
      btn.type = "button";
      btn.className = "item-btn";
      btn.textContent = item.name + "×" + item.qty;
      btn.addEventListener("click", () => {
        if (selected === item.id) {
          clearSelection();
          return;
        }
        el.querySelectorAll(".item-btn").forEach((b) => b.classList.remove("selected"));
        btn.classList.add("selected");
        selected = item.id;
        C.renderSubActions(IDS.actions, item.actions);
      });
      el.appendChild(btn);
    });
  }

  const api = { TAB, bind, open: openPanel, close, isOpen, render };
  C.register(api);
  return api;
})();
