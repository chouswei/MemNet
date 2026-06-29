window.NovelSheet = (function () {
  let selected = { items: null, arts: null, production: null };
  let sheetData = null;

  const emptyHint = (msg) => {
    const p = document.createElement("p");
    p.className = "empty-hint";
    p.textContent = msg;
    return p;
  };

  function sectionTitle(text) {
    const h = document.createElement("h3");
    h.className = "sheet-section-title";
    h.textContent = text;
    return h;
  }

  function initTabs() {
    document.querySelectorAll("#tab-bar button").forEach((btn) => {
      btn.addEventListener("click", () => {
        const tab = btn.dataset.tab;
        document.querySelectorAll("#tab-bar button").forEach((b) => {
          b.setAttribute("aria-selected", b.dataset.tab === tab ? "true" : "false");
        });
        ["items", "arts", "production"].forEach((t) => {
          document.getElementById("panel-" + t).classList.toggle("hidden", t !== tab);
        });
        clearSubActions(tab);
      });
    });
    activateTab("items");
  }

  function activateTab(tab) {
    document.querySelectorAll("#tab-bar button").forEach((b) => {
      b.setAttribute("aria-selected", b.dataset.tab === tab ? "true" : "false");
    });
    ["items", "arts", "production"].forEach((t) => {
      document.getElementById("panel-" + t).classList.toggle("hidden", t !== tab);
    });
  }

  function clearSubActions(kind) {
    const el = document.getElementById("panel-" + kind + "-actions");
    if (el) {
      el.innerHTML = "";
      el.classList.add("hidden");
    }
    selected[kind] = null;
    const panel = document.getElementById("panel-" + kind);
    if (panel) {
      panel.querySelectorAll(".item-btn, .art-btn, .prod-btn, .industry-card").forEach((b) => {
        b.classList.remove("selected");
      });
    }
  }

  function prefill(template) {
    const ta = document.getElementById("input-text");
    ta.value = template;
    ta.focus();
  }

  function renderSubActions(kind, actions, name) {
    const el = document.getElementById("panel-" + kind + "-actions");
    el.innerHTML = "";
    (actions || []).forEach((act) => {
      const btn = document.createElement("button");
      btn.type = "button";
      btn.textContent = act.label;
      btn.addEventListener("click", () => prefill(act.template || act.label));
      el.appendChild(btn);
    });
    el.classList.toggle("hidden", !actions || !actions.length);
  }

  function render(data) {
    sheetData = data;
    selected = { items: null, arts: null, production: null };
    ["items", "arts", "production"].forEach((k) => {
      const el = document.getElementById("panel-" + k + "-actions");
      if (el) {
        el.innerHTML = "";
        el.classList.add("hidden");
      }
    });
    renderItems(data.items || []);
    renderArtsPanel(data.arts || [], data.body_stats || []);
    const prod = data.production || {};
    renderIndustries(prod.industries || []);
    renderProductionNodes(prod.nodes || []);
  }

  function renderItems(items) {
    const panel = document.getElementById("panel-items");
    panel.innerHTML = "";
    if (!items.length) {
      panel.appendChild(emptyHint("尚無物品"));
      return;
    }
    items.forEach((item) => {
      const btn = document.createElement("button");
      btn.type = "button";
      btn.className = "item-btn";
      btn.textContent = item.name + "×" + item.qty;
      btn.addEventListener("click", () => {
        if (selected.items === item.id) {
          clearSubActions("items");
          btn.classList.remove("selected");
          return;
        }
        panel.querySelectorAll(".item-btn").forEach((b) => b.classList.remove("selected"));
        btn.classList.add("selected");
        selected.items = item.id;
        renderSubActions("items", item.actions, item.name);
      });
      panel.appendChild(btn);
    });
  }

  function renderArtsPanel(arts, bodyStats) {
    const panel = document.getElementById("panel-arts");
    panel.innerHTML = "";
    if (!arts.length && !bodyStats.length) {
      panel.appendChild(emptyHint("尚無武學"));
      return;
    }
    if (arts.length) {
      panel.appendChild(sectionTitle("武功"));
      arts.forEach((art) => appendArtBtn(panel, art, art.name));
    }
    if (bodyStats.length) {
      panel.appendChild(sectionTitle("根基"));
      bodyStats.forEach((stat) => {
        const label = stat.kind + (stat.rank ? "·" + stat.rank : "");
        appendArtBtn(panel, stat, label, stat.kind);
      });
    }
  }

  function appendArtBtn(panel, entry, label, actionName) {
    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = "art-btn";
    btn.textContent = label;
    btn.addEventListener("click", () => {
      const key = entry.id;
      if (selected.arts === key) {
        clearSubActions("arts");
        btn.classList.remove("selected");
        return;
      }
      panel.querySelectorAll(".art-btn").forEach((b) => b.classList.remove("selected"));
      btn.classList.add("selected");
      selected.arts = key;
      renderSubActions("arts", entry.actions || [], actionName || entry.name);
    });
    panel.appendChild(btn);
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

  function renderIndustries(industries) {
    const panel = document.getElementById("panel-production");
    panel.innerHTML = "";
    if (!industries.length) {
      panel.appendChild(emptyHint("尚未取得產業"));
      return;
    }
    industries.forEach((ind) => {
      const card = document.createElement("button");
      card.type = "button";
      card.className = "industry-card prod-btn";
      const title = document.createElement("span");
      title.className = "industry-title";
      const kind = ind.kind ? "·" + ind.kind : "";
      const loc = ind.location ? "｜" + ind.location : "";
      title.textContent = ind.name + kind + loc;
      const sub = document.createElement("span");
      sub.className = "prod-sub";
      sub.textContent = industrySubtitle(ind);
      card.appendChild(title);
      card.appendChild(sub);
      if (ind.products && ind.products.length) {
        const prods = document.createElement("span");
        prods.className = "prod-sub";
        prods.textContent = "產品：" + ind.products.map(productLine).join("、");
        card.appendChild(prods);
      }
      card.addEventListener("click", () => {
        if (selected.production === ind.id) {
          clearSubActions("production");
          card.classList.remove("selected");
          return;
        }
        panel.querySelectorAll(".industry-card").forEach((b) => b.classList.remove("selected"));
        card.classList.add("selected");
        selected.production = ind.id;
        renderSubActions("production", ind.actions, ind.name);
      });
      panel.appendChild(card);
    });
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

  function renderProductionNodes(nodes) {
    const panel = document.getElementById("panel-production");
    if (!nodes.length) return;
    if (panel.querySelector(".empty-hint") && !panel.querySelector(".industry-card")) {
      panel.innerHTML = "";
    }
    if (nodes.length) {
      panel.appendChild(sectionTitle("技術"));
    }
    nodes.forEach((node) => {
      const card = document.createElement("button");
      card.type = "button";
      card.className = "industry-card prod-btn tec-node";
      const title = document.createElement("span");
      title.className = "industry-title";
      title.textContent = node.name;
      const sub = document.createElement("span");
      sub.className = "prod-sub";
      sub.textContent = nodeSubtitle(node);
      card.appendChild(title);
      card.appendChild(sub);
      if (node.outputs && node.outputs.length) {
        const outs = document.createElement("span");
        outs.className = "prod-sub";
        outs.textContent =
          "產出：" +
          node.outputs
            .map((o) => o.name + (o.status ? "（" + o.status + "）" : ""))
            .join("、");
        card.appendChild(outs);
      }
      card.addEventListener("click", () => {
        if (selected.production === node.id) {
          clearSubActions("production");
          card.classList.remove("selected");
          return;
        }
        panel.querySelectorAll(".industry-card, .tec-node").forEach((b) => b.classList.remove("selected"));
        card.classList.add("selected");
        selected.production = node.id;
        renderSubActions("production", node.actions, node.name);
      });
      panel.appendChild(card);
    });
  }

  return { render, initTabs };
})();
