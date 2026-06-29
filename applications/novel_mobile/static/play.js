window.NovelPlay = (function () {
  const narrativeEl = () => document.getElementById("narrative");
  const hudEl = () => document.getElementById("narrative-hud");
  const optionsTextEl = () => document.getElementById("narrative-options");
  const choicesEl = () => document.getElementById("panel-choices");

  function showPlayChrome() {
    document.getElementById("panel-choices").classList.remove("hidden");
    document.getElementById("panel-text").classList.remove("hidden");
    document.getElementById("tab-bar").classList.remove("hidden");
    document.querySelectorAll("#tab-bar button").forEach((b) => b.classList.remove("hidden"));
    if (window.NovelSheet) window.NovelSheet.initTabs();
  }

  function scrollNarrativeTop() {
    const pane = document.getElementById("narrative-pane");
    if (pane) pane.scrollTop = 0;
  }

  function clearOptions() {
    const textEl = optionsTextEl();
    if (textEl) {
      textEl.innerHTML = "";
      textEl.classList.add("hidden");
    }
    choicesEl().innerHTML = "";
  }

  function renderEmptyPlay() {
    narrativeEl().textContent =
      "歡迎進入。點「開始劇情」生成第一回，或在下方輸入指令。";
    hudEl().style.display = "none";
    clearOptions();
    const btnEl = choicesEl();
    btnEl.classList.remove("hidden");
    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = "choice-start-btn";
    btn.textContent = "開始劇情";
    btn.addEventListener("click", () => {
      if (window.NovelApp.activeJobId) return;
      window.NovelApp.postBeat({ choice: 1 });
    });
    btnEl.appendChild(btn);
    scrollNarrativeTop();
  }

  function renderBeat(beat) {
    if (window.NovelPartyPanel && window.NovelPartyPanel.isOpen()) {
      window.NovelPartyPanel.close();
    }
    if (!beat) {
      renderEmptyPlay();
      return;
    }
    const fmt = beat.format_play || window.NovelApp.formatPlay || "【劇情】";
    const beatTag =
      beat.beat_index && beat.beat_index >= 1
        ? `（第${beat.beat_index}拍）`
        : "";
    narrativeEl().textContent = fmt + beatTag + "\n" + (beat.prose || "");
    const hud = (beat.hud || "").trim();
    if (hud) {
      hudEl().style.display = "";
      hudEl().textContent = hud;
    } else {
      hudEl().style.display = "none";
    }
    renderChoices(beat.options || []);
    scrollNarrativeTop();
  }

  function renderChoices(options) {
    const textEl = optionsTextEl();
    const btnEl = choicesEl();
    btnEl.innerHTML = "";
    textEl.innerHTML = "";

    const items = options
      .map((opt) => (opt || "").trim())
      .filter(Boolean);

    if (!items.length) {
      textEl.classList.add("hidden");
      btnEl.classList.add("hidden");
      return;
    }

    btnEl.classList.remove("hidden");

    items.forEach((text, i) => {
      const n = i + 1;
      const row = document.createElement("div");
      row.className = "choice-read-item";
      const num = document.createElement("span");
      num.className = "choice-num";
      num.textContent = n + ".";
      row.appendChild(num);
      row.appendChild(document.createTextNode(text));
      textEl.appendChild(row);

      const btn = document.createElement("button");
      btn.type = "button";
      btn.className = "choice-num-btn";
      btn.textContent = String(n);
      btn.setAttribute("aria-label", "選項 " + n);
      btn.addEventListener("click", () => {
        if (window.NovelApp.activeJobId) return;
        window.NovelApp.postBeat({ choice: n });
      });
      btnEl.appendChild(btn);
    });

    textEl.classList.remove("hidden");
  }

  return { renderBeat, showPlayChrome, renderChoices };
})();
