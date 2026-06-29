/** Production foreground panel — industries and tech nodes. */
window.NovelProductionPanel = (function () {
  const C = window.NovelSheetCommon;
  const TAB = "production";
  const IDS = {
    overlay: "production-overlay",
    title: "production-sheet-title",
    body: "production-sheet-body",
    panel: "production-panel",
    actions: "production-actions",
    close: "production-sheet-close",
    backdrop: "production-sheet-backdrop",
  };
  const DEFAULT_TITLE = "產業";

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
    panel()?.querySelectorAll(".industry-card").forEach((b) => b.classList.remove("selected"));
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

  function industrySubtitle(ind) {
    const parts = [];
    if (ind.manager) parts.push("負責人：" + ind.manager);
    if (ind.assistants && ind.assistants.length) {
      parts.push("協助：" + ind.assistants.join("、"));
    }
    parts.push("月收：" + (ind.income ?? 0) + "　月支：" + (ind.expense ?? 0));
    parts.push("現金：" + (ind.cash ?? 0) + "　負債：" + (ind.debt ?? 0));
    if (ind.plr_role === "owns") parts.push("持有");
    else if (ind.plr_role === "manages") parts.push("經營");
    return parts.join("｜");
  }

  function productLine(prod) {
    const st = (prod.status || "").trim();
    return prod.name + (st ? "（" + st + "）" : "");
  }

  function nodeSubtitle(node) {
    const parts = [];
    if (node.status) parts.push(node.status);
    if (node.domain) parts.push(node.domain);
    if (node.lines != null) parts.push("產線：" + node.lines);
    if (node.asset_label && node.asset_label !== node.name) {
      parts.push("資產：" + node.asset_label);
    }
    return parts.join("｜");
  }

  function appendIndustryCard(el, cardData, onSelect) {
    const card = document.createElement("button");
    card.type = "button";
    card.className = "industry-card prod-btn" + (cardData.extraClass ? " " + cardData.extraClass : "");
    const title = document.createElement("span");
    title.className = "industry-title";
    title.textContent = cardData.title;
    const sub = document.createElement("span");
    sub.className = "prod-sub";
    sub.textContent = cardData.subtitle;
    card.appendChild(title);
    card.appendChild(sub);
    (cardData.lines || []).forEach((line) => {
      const span = document.createElement("span");
      span.className = "prod-sub";
      span.textContent = line;
      card.appendChild(span);
    });
    card.addEventListener("click", () => onSelect(card, cardData.id, cardData.actions));
    el.appendChild(card);
  }

  function selectCard(card, id, actions) {
    const el = panel();
    if (selected === id) {
      clearSelection();
      return;
    }
    el.querySelectorAll(".industry-card").forEach((b) => b.classList.remove("selected"));
    card.classList.add("selected");
    selected = id;
    C.renderSubActions(IDS.actions, actions || []);
  }

  function render(production) {
    clearSelection();
    const data = production || {};
    const industries = data.industries || [];
    const nodes = data.nodes || [];
    const el = panel();
    el.innerHTML = "";

    if (!industries.length && !nodes.length) {
      el.appendChild(C.emptyHint("尚未取得產業"));
      return;
    }

    industries.forEach((ind) => {
      const kind = ind.kind ? "·" + ind.kind : "";
      const loc = ind.location ? "｜" + ind.location : "";
      const lines = [];
      if (ind.products && ind.products.length) {
        lines.push("產品：" + ind.products.map(productLine).join("、"));
      }
      appendIndustryCard(
        el,
        {
          id: ind.id,
          title: ind.name + kind + loc,
          subtitle: industrySubtitle(ind),
          lines,
          actions: ind.actions,
        },
        selectCard
      );
    });

    if (nodes.length) {
      el.appendChild(C.sectionTitle("技術"));
      nodes.forEach((node) => {
        const lines = [];
        if (node.outputs && node.outputs.length) {
          lines.push(
            "產出：" +
              node.outputs.map((o) => o.name + (o.status ? "（" + o.status + "）" : "")).join("、")
          );
        }
        appendIndustryCard(
          el,
          {
            id: node.id,
            title: node.name,
            subtitle: nodeSubtitle(node),
            lines,
            actions: node.actions,
            extraClass: "tec-node",
          },
          selectCard
        );
      });
    }
  }

  const api = { TAB, bind, open: openPanel, close, isOpen, render };
  C.register(api);
  return api;
})();
