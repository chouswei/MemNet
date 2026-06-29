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

  function hidePlayChrome() {
    document.getElementById("panel-choices").classList.add("hidden");
    document.getElementById("tab-bar").classList.add("hidden");
    if (window.NovelSheet) window.NovelSheet.closeSheet();
    if (window.NovelPartyPanel) window.NovelPartyPanel.close();
    const opts = document.getElementById("narrative-options");
    if (opts) {
      opts.innerHTML = "";
      opts.classList.add("hidden");
    }
    const hud = hudEl();
    hud.textContent = "";
    hud.classList.add("hidden");
    hud.style.display = "none";
  }

  function setBusy(on) {
    busy = on;
    document.querySelectorAll("#setup-actions button, #btn-submit").forEach((b) => {
      b.disabled = on;
    });
    document.getElementById("input-text").disabled = on;
  }

  function showPickTab() {
    if (window.NovelSkillsPanel) {
      window.NovelSheet.initTabs();
      window.NovelSkillsPanel.showSetupTab();
    }
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
    const hud = hudEl();
    hud.classList.add("hidden");
    hud.style.display = "none";
    const pane = document.getElementById("narrative-pane");
    if (pane) pane.scrollTop = 0;

    renderSetupActions(guidance);

    const textPanel = document.getElementById("panel-text");
    const needsInput = na === "narrate_ask_name" || na === "commit_player_profile";
    textPanel.classList.toggle("hidden", !needsInput && !na.startsWith("pick_"));

    if (na.startsWith("pick_")) {
      const slot = na.replace("pick_", "");
      showPickTab();
      if (window.NovelSkillsPanel) window.NovelSkillsPanel.loadSetupOffers(slot);
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
