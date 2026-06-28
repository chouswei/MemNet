window.NovelSetup = (function () {
  const actionsEl = () => document.getElementById("setup-actions");
  const narrativeEl = () => document.getElementById("narrative");
  const hudEl = () => document.getElementById("narrative-hud");

  function formatBlock(guidance, lines) {
    const fmt = guidance.format_god || "【神域】";
    const body = (lines || []).join("\n\n");
    return fmt + "\n" + body;
  }

  function hidePlayChrome() {
    document.getElementById("panel-choices").classList.add("hidden");
    document.getElementById("tab-bar").classList.add("hidden");
    ["items", "arts", "production"].forEach((t) => {
      document.getElementById("panel-" + t).classList.add("hidden");
    });
    hudEl().style.display = "none";
    hudEl().textContent = "";
  }

  function showPickTab(guidance) {
    const na = guidance.next_action || "";
    if (!na.startsWith("pick_")) {
      document.getElementById("tab-bar").classList.add("hidden");
      return;
    }
    document.getElementById("tab-bar").classList.remove("hidden");
    document.querySelectorAll("#tab-bar button").forEach((b) => {
      const on = b.dataset.tab === "arts";
      b.classList.toggle("hidden", !on);
      b.setAttribute("aria-selected", on ? "true" : "false");
    });
    document.getElementById("panel-arts").classList.remove("hidden");
    document.getElementById("panel-items").classList.add("hidden");
    document.getElementById("panel-production").classList.add("hidden");
  }

  async function loadCatalogAndRenderOffers(slot) {
    const cat = await window.NovelApp.api("/api/catalog");
    const panel = document.getElementById("panel-arts");
    panel.innerHTML = "";
    const slotData = (cat.slots || {})[slot] || {};
    const arts = slotData.offers || slotData.arts || [];
    arts.forEach((art) => {
      const btn = document.createElement("button");
      btn.type = "button";
      btn.className = "art-btn";
      btn.textContent = art.name || art.id;
      btn.addEventListener("click", async () => {
        await window.NovelApp.api("/api/setup/pick", {
          method: "POST",
          body: JSON.stringify({ slot, art_id: art.id }),
        });
        await window.NovelApp.refreshSetup();
      });
      panel.appendChild(btn);
    });
  }

  function renderSetupActions(guidance) {
    const el = actionsEl();
    el.innerHTML = "";
    const na = guidance.next_action;
    const map = {
      narrate_open: [{ label: "繼續", fn: () => window.NovelApp.refreshSetup() }],
      narrate_pre_pick: [{ label: "繼續", fn: async () => {
        await window.NovelApp.api("/api/catalog");
        await window.NovelApp.refreshSetup();
      }}],
      narrate_ask_gender: [
        { label: "男", fn: () => postProfile({ gender: "男" }) },
        { label: "女", fn: () => postProfile({ gender: "女" }) },
      ],
      narrate_transmigration: [{ label: "進入劇情", fn: () => window.NovelApp.refreshSetup() }],
    };
    const buttons = map[na];
    if (!buttons) {
      el.classList.add("hidden");
      return;
    }
    el.classList.remove("hidden");
    buttons.forEach((b) => {
      const btn = document.createElement("button");
      btn.type = "button";
      btn.textContent = b.label;
      btn.addEventListener("click", b.fn);
      el.appendChild(btn);
    });
  }

  async function postProfile(body) {
    await window.NovelApp.api("/api/setup/profile", {
      method: "POST",
      body: JSON.stringify(body),
    });
    document.getElementById("input-text").value = "";
    await window.NovelApp.refreshSetup();
  }

  function render(data) {
    hidePlayChrome();
    const guidance = data.setup_guidance || {};
    const na = guidance.next_action;

    if (na === "start_play") {
      window.NovelApp.enterPlay();
      return;
    }

    let lines = guidance.suggested_lines || [];
    if (na === "commit_player_profile") {
      const errs = (data.profile || {}).errors || [];
      lines = errs.length ? errs : lines;
    }
    if (guidance.scene) {
      lines = [guidance.scene, ...lines];
    }
    narrativeEl().textContent = formatBlock(guidance, lines);
    hudEl().style.display = "none";

    renderSetupActions(guidance);

    if (na.startsWith("pick_")) {
      const slot = na.replace("pick_", "");
      showPickTab(guidance);
      loadCatalogAndRenderOffers(slot);
    } else {
      document.getElementById("tab-bar").classList.add("hidden");
    }

    const textPanel = document.getElementById("panel-text");
    if (na === "narrate_ask_name") {
      textPanel.classList.remove("hidden");
    } else if (!na.startsWith("pick_")) {
      textPanel.classList.toggle("hidden", na !== "narrate_ask_name");
    }
  }

  function onSubmit(text) {
    const guidance = (window.NovelApp.setupData || {}).setup_guidance || {};
    if (guidance.next_action === "narrate_ask_name") {
      postProfile({ name: text });
    }
  }

  return { render, onSubmit, hidePlayChrome };
})();
