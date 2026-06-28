window.NovelSheet = (function () {
  let selected = { items: null, arts: null, production: null };
  let sheetData = null;

  const emptyHint = (msg) => {
    const p = document.createElement("p");
    p.className = "empty-hint";
    p.textContent = msg;
    return p;
  };

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

  function prodSubtitle(node) {
    const st = node.status || "";
    if (node.asset_mode === "installable") {
      const req = (node.requires || [])[0];
      const owned = req ? req.owned : 0;
      return node.name + "·" + st + "·" + (node.asset_label || "") +
        " 裝×" + node.lines + "/有×" + owned;
    }
    return node.name + "·" + st + "·" + (node.asset_label || "") + "×" + (node.lines || 0);
  }

  function render(data) {
    sheetData = data;
    renderItems(data.items || []);
    renderArts(data.arts || [], data.body_stats || []);
    renderProduction((data.production || {}).nodes || []);
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

  function renderArts(arts, bodyStats) {
    const panel = document.getElementById("panel-arts");
    panel.innerHTML = "";
    const all = [
      ...arts.map((a) => ({ ...a, _type: "art" })),
      ...bodyStats.map((b) => ({ ...b, name: b.kind, _type: "stat" })),
    ];
    if (!all.length) {
      panel.appendChild(emptyHint("尚無武學"));
      return;
    }
    all.forEach((entry) => {
      const btn = document.createElement("button");
      btn.type = "button";
      btn.className = "art-btn";
      const label = entry.name + (entry.rank ? "·" + entry.rank : "");
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
        const actions = entry.actions || defaultMartialActions(entry.name);
        renderSubActions("arts", actions, entry.name);
      });
      panel.appendChild(btn);
    });
  }

  function defaultMartialActions(name) {
    return [
      { label: "修練", template: "修練" + name },
      { label: "於當前場景使用", template: "在當前場景使用" + name },
    ];
  }

  function renderProduction(nodes) {
    const panel = document.getElementById("panel-production");
    panel.innerHTML = "";
    if (!nodes.length) {
      panel.appendChild(emptyHint("尚未開放"));
      return;
    }
    nodes.forEach((node) => {
      const btn = document.createElement("button");
      btn.type = "button";
      btn.className = "prod-btn";
      const title = document.createElement("span");
      title.textContent = node.name;
      const sub = document.createElement("span");
      sub.className = "prod-sub";
      sub.textContent = prodSubtitle(node);
      btn.appendChild(title);
      btn.appendChild(sub);
      btn.addEventListener("click", () => {
        if (selected.production === node.id) {
          clearSubActions("production");
          btn.classList.remove("selected");
          return;
        }
        panel.querySelectorAll(".prod-btn").forEach((b) => b.classList.remove("selected"));
        btn.classList.add("selected");
        selected.production = node.id;
        renderSubActions("production", node.actions, node.name);
      });
      panel.appendChild(btn);
    });
  }

  return { render, initTabs };
})();
