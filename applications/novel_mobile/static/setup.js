window.NovelSetup = (function () {
  const actionsEl = () => document.getElementById("setup-actions");
  const narrativeEl = () => document.getElementById("narrative");
  const hudEl = () => document.getElementById("narrative-hud");

  let busy = false;

  function formatBlock(guidance, lines) {
    const fmt = guidance.format_god || "【神域】";
    const body = (lines || []).join("\n\n");
    return fmt + "\n" + body;
  }

  function artDisplayName(art) {
    return art["名稱"] || art.name || art.id || "";
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

  function setBusy(on) {
    busy = on;
    document.querySelectorAll("#setup-actions button, #btn-submit").forEach((b) => {
      b.disabled = on;
    });
    document.getElementById("input-text").disabled = on;
  }

  function showPickTab() {
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

  async function postAck(step) {
    setBusy(true);
    window.NovelApp.hideError();
    try {
      await window.NovelApp.api("/api/setup/ack", {
        method: "POST",
        body: JSON.stringify({ step }),
      });
      await window.NovelApp.refreshSetup();
    } catch (err) {
      const msg =
        err.body?.errors?.join(" ") ||
        err.body?.detail?.errors?.join(" ") ||
        err.message ||
        "操作失敗";
      window.NovelApp.showError(msg);
    } finally {
      setBusy(false);
    }
  }

  function renderOfferButtons(panel, slot, arts) {
    panel.querySelectorAll(".art-btn").forEach((el) => el.remove());
    panel.querySelectorAll("p.empty-offers").forEach((el) => el.remove());
    if (!arts.length) {
      const p = document.createElement("p");
      p.className = "empty-offers";
      p.textContent = "尚無可選項目";
      panel.appendChild(p);
      return;
    }
    arts.forEach((art) => {
      const btn = document.createElement("button");
      btn.type = "button";
      btn.className = "art-btn";
      btn.textContent = artDisplayName(art);
      btn.addEventListener("click", async () => {
        if (busy) return;
        setBusy(true);
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
          setBusy(false);
        }
      });
      panel.appendChild(btn);
    });
  }

  async function rerollOffers(slot) {
    setBusy(true);
    window.NovelApp.hideError();
    try {
      const result = await window.NovelApp.api("/api/setup/reroll", {
        method: "POST",
        body: JSON.stringify({ slot }),
      });
      const panel = document.getElementById("panel-arts");
      const slotData = (result.slots || {})[slot] || {};
      const arts = slotData.arts || [];
      renderOfferButtons(panel, slot, arts);
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
      setBusy(false);
    }
  }

  async function loadCatalogAndRenderOffers(slot) {
    setBusy(true);
    try {
      const cat = await window.NovelApp.api("/api/catalog");
      const panel = document.getElementById("panel-arts");
      panel.innerHTML = "";
      const slotData = (cat.slots || {})[slot] || {};
      const arts = slotData.arts || [];
      const rerollBtn = document.createElement("button");
      rerollBtn.type = "button";
      rerollBtn.className = "reroll-btn";
      rerollBtn.textContent = "重新骰選";
      rerollBtn.addEventListener("click", () => {
        rerollOffers(slot);
      });
      panel.appendChild(rerollBtn);
      renderOfferButtons(panel, slot, arts);
    } catch (err) {
      const msg =
        err.body?.errors?.join(" ") ||
        err.body?.detail?.errors?.join(" ") ||
        err.message ||
        "載入選項失敗";
      window.NovelApp.showError(msg);
    } finally {
      setBusy(false);
    }
  }

  function renderSetupActions(guidance) {
    const el = actionsEl();
    el.innerHTML = "";
    const na = guidance.next_action;
    let buttons = null;
    if (na === "narrate_ask_gender") {
      buttons = (guidance.genders || ["男", "女"]).map((g) => ({
        label: g,
        fn: () => postProfile({ gender: g }),
      }));
    } else {
      const map = {
        narrate_open: [{ label: "繼續", fn: () => postAck("narrate_open") }],
        narrate_pre_pick: [{ label: "繼續", fn: () => postAck("narrate_pre_pick") }],
        narrate_transmigration: [
          { label: "進入劇情", fn: () => postAck("narrate_transmigration") },
        ],
      };
      buttons = map[na];
    }
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
    setBusy(true);
    window.NovelApp.hideError();
    try {
      await window.NovelApp.api("/api/setup/profile", {
        method: "POST",
        body: JSON.stringify(body),
      });
      document.getElementById("input-text").value = "";
      await window.NovelApp.refreshSetup();
    } catch (err) {
      const msg =
        err.body?.errors?.join(" ") ||
        err.body?.detail?.errors?.join(" ") ||
        err.message ||
        "送出失敗";
      window.NovelApp.showError(msg);
    } finally {
      setBusy(false);
    }
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
      const scene = guidance.scene;
      const sceneLine =
        typeof scene === "string"
          ? scene
          : [scene.title, scene.hint].filter(Boolean).join("\n");
      if (sceneLine) lines = [sceneLine, ...lines];
    }
    narrativeEl().textContent = formatBlock(guidance, lines);
    hudEl().style.display = "none";

    renderSetupActions(guidance);

    const textPanel = document.getElementById("panel-text");
    const needsInput = na === "narrate_ask_name" || na === "commit_player_profile";
    textPanel.classList.toggle("hidden", !needsInput && !na.startsWith("pick_"));

    if (na.startsWith("pick_")) {
      const slot = na.replace("pick_", "");
      showPickTab();
      loadCatalogAndRenderOffers(slot);
    } else {
      document.getElementById("tab-bar").classList.add("hidden");
    }
  }

  function onSubmit(text) {
    const guidance = (window.NovelApp.setupData || {}).setup_guidance || {};
    const na = guidance.next_action;
    if (na === "narrate_ask_name" || na === "commit_player_profile") {
      postProfile({ name: text });
      return;
    }
    if (na === "narrate_open" || na === "narrate_pre_pick") {
      window.NovelApp.showError("請先按「繼續」");
      return;
    }
    if (!na.startsWith("pick_")) {
      window.NovelApp.showError("目前無法以文字輸入");
    }
  }

  return { render, onSubmit, hidePlayChrome };
})();
