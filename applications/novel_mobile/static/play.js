window.NovelPlay = (function () {
  const narrativeEl = () => document.getElementById("narrative");
  const hudEl = () => document.getElementById("narrative-hud");
  const choicesEl = () => document.getElementById("panel-choices");

  function showPlayChrome() {
    document.getElementById("panel-choices").classList.remove("hidden");
    document.getElementById("panel-text").classList.remove("hidden");
    document.getElementById("tab-bar").classList.remove("hidden");
    document.querySelectorAll("#tab-bar button").forEach((b) => b.classList.remove("hidden"));
    ["items", "arts", "production"].forEach((t, i) => {
      const panel = document.getElementById("panel-" + t);
      panel.classList.remove("hidden");
      if (i === 0) panel.classList.remove("hidden");
    });
    if (window.NovelSheet) window.NovelSheet.initTabs();
  }

  function renderBeat(beat) {
    if (!beat) {
      narrativeEl().textContent = "尚無劇情，請選擇下方選項或輸入指令。";
      hudEl().style.display = "none";
      choicesEl().innerHTML = "";
      return;
    }
    const fmt = "【劇情】";
    narrativeEl().textContent = fmt + "\n" + (beat.prose || "");
    const hud = (beat.hud || "").trim();
    if (hud) {
      hudEl().style.display = "";
      hudEl().textContent = hud;
    } else {
      hudEl().style.display = "none";
    }
    renderChoices(beat.options || []);
  }

  function renderChoices(options) {
    const el = choicesEl();
    el.innerHTML = "";
    options.forEach((opt, i) => {
      const text = (opt || "").trim();
      if (!text) return;
      const n = i + 1;
      const btn = document.createElement("button");
      btn.type = "button";
      btn.className = "choice-btn";
      const label = text.length > 16 ? text.slice(0, 16) + "…" : text;
      btn.textContent = n + ". " + label;
      btn.addEventListener("click", () => {
        if (window.NovelApp.activeJobId) return;
        window.NovelApp.postBeat({ choice: n });
      });
      el.appendChild(btn);
    });
  }

  return { renderBeat, showPlayChrome, renderChoices };
})();
