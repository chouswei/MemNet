/* Shared API client and app bootstrap */
window.NovelApp = (function () {
  const POLL_MS = 2000;
  const TIMEOUT_MS = 600000;
  const JOB_KEY = "novel_mobile_job_id";
  const TOKEN_KEY = "novel_mobile_token";
  const ACCESS_TOKEN_KEY = "novel_mobile_access_token";
  const USER_KEY = "novel_user_id";
  const WORLD_KEY = "novel_world_id";

  let authConfig = null;
  let appStarted = false;

  let mode = "setup";
  let health = null;
  let setupData = null;
  let lastBeat = null;
  let sheet = null;
  let activeJobId = null;
  let pollTimer = null;
  let pollStarted = 0;

  let formatPlay = "【劇情】";
  let storySeeds = [];
  let worldList = [];

  const phaseLabels = {
    prepare_script: "準備劇本…",
    script_draft: "編劇初稿…",
    script_review: "編劇審稿…",
    oln: "寫大綱…",
    sbd: "寫分鏡…",
    scr: "寫腳本…",
    prepare_prose: "準備正文…",
    prose: "撰寫劇情…",
  };

  function authHeaders() {
    const access = localStorage.getItem(ACCESS_TOKEN_KEY);
    if (access) return { Authorization: "Bearer " + access };
    const token = localStorage.getItem(TOKEN_KEY);
    if (!token) return {};
    return { Authorization: "Bearer " + token };
  }

  function newUserId() {
    if (typeof crypto !== "undefined" && typeof crypto.randomUUID === "function") {
      return crypto.randomUUID();
    }
    if (typeof crypto !== "undefined" && typeof crypto.getRandomValues === "function") {
      const bytes = new Uint8Array(16);
      crypto.getRandomValues(bytes);
      bytes[6] = (bytes[6] & 0x0f) | 0x40;
      bytes[8] = (bytes[8] & 0x3f) | 0x80;
      const hex = Array.from(bytes, (b) => b.toString(16).padStart(2, "0")).join("");
      return (
        hex.slice(0, 8) +
        "-" +
        hex.slice(8, 12) +
        "-" +
        hex.slice(12, 16) +
        "-" +
        hex.slice(16, 20) +
        "-" +
        hex.slice(20)
      );
    }
    return "u-" + Date.now().toString(36) + "-" + Math.random().toString(36).slice(2, 10);
  }

  function ensureAnonUserId() {
    let id = localStorage.getItem(USER_KEY);
    if (!id) {
      id = newUserId();
      localStorage.setItem(USER_KEY, id);
    }
    return id;
  }

  function userHeaders() {
    if (
      authConfig &&
      (authConfig.auth_mode === "google" || authConfig.auth_mode === "guest")
    ) {
      return {};
    }
    return { "X-Novel-User-Id": ensureAnonUserId() };
  }

  function worldHeaders() {
    const wid = localStorage.getItem(WORLD_KEY);
    if (!wid) return {};
    return { "X-Novel-World-Id": wid };
  }

  function scopeHeaders() {
    return { ...userHeaders(), ...worldHeaders() };
  }

  function worldLabel(w) {
    const story = w.story_title || "";
    const title = w.title || w.world_id;
    return story && story !== title ? `${story} · ${title}` : title;
  }

  function renderWorldSelect(worlds) {
    const sel = document.getElementById("world-select");
    if (!sel) return;
    const wid = localStorage.getItem(WORLD_KEY);
    sel.innerHTML = "";
    (worlds || []).forEach((w) => {
      const opt = document.createElement("option");
      opt.value = w.world_id;
      opt.textContent = worldLabel(w);
      if (w.world_id === wid) opt.selected = true;
      sel.appendChild(opt);
    });
    sel.classList.toggle("hidden", !(worlds && worlds.length));
    const btnDelete = document.getElementById("btn-delete-world");
    if (btnDelete) btnDelete.classList.toggle("hidden", !(worlds && worlds.length));
    setHeaderWorldControls();
  }

  function closeWorldDirectory() {
    if (mode === "world_pick") return;
    const overlay = document.getElementById("world-dir-overlay");
    if (!overlay) return;
    overlay.classList.add("hidden");
    overlay.setAttribute("aria-hidden", "true");
  }

  function setHeaderWorldControls() {
    const pick = mode === "world_pick";
    const hasWorld = Boolean(localStorage.getItem(WORLD_KEY));
    const restart = document.getElementById("btn-restart-session");
    const del = document.getElementById("btn-delete-world");
    const sel = document.getElementById("world-select");
    const dir = document.getElementById("btn-world-dir");
    if (restart) restart.disabled = pick || !hasWorld;
    if (del) del.classList.toggle("hidden", pick || !hasWorld || !worldList.length);
    if (sel) sel.classList.toggle("hidden", pick || !worldList.length);
    if (dir) dir.textContent = pick ? "世界" : "世界目錄";
  }

  function setWorldPickChrome(active) {
    document.getElementById("app-main").classList.toggle("world-pick-dimmed", active);
    document.body.classList.toggle("world-pick-active", active);
    const closeBtn = document.getElementById("world-dir-close");
    if (closeBtn) closeBtn.classList.toggle("hidden", active);
    const input = document.getElementById("input-text");
    const submit = document.getElementById("btn-submit");
    if (input) input.disabled = active;
    if (submit) submit.disabled = active;
    setHeaderWorldControls();
  }

  async function loadWorldList() {
    const data = await api("/api/worlds");
    worldList = data.worlds || [];
    await loadStorySeeds();
    renderWorldSelect(worldList);
    return worldList;
  }

  function hasValidWorldSelection() {
    const wid = localStorage.getItem(WORLD_KEY);
    return Boolean(wid && worldList.some((w) => w.world_id === wid));
  }

  async function showWorldPickGate() {
    mode = "world_pick";
    setWorldPickChrome(true);
    hideError();
    if (window.NovelSetup) window.NovelSetup.hidePlayChrome();
    const narrative = document.getElementById("narrative");
    if (narrative) narrative.textContent = "";
    const title = document.getElementById("world-dir-title");
    if (title) title.textContent = "選擇世界";
    renderWorldDirectory(storySeeds, worldList);
    const overlay = document.getElementById("world-dir-overlay");
    overlay.classList.remove("hidden");
    overlay.setAttribute("aria-hidden", "false");
  }

  async function enterSelectedWorld(worldId) {
    if (!worldId) return;
    localStorage.setItem(WORLD_KEY, worldId);
    mode = "setup";
    setWorldPickChrome(false);
    closeWorldDirectory();
    const title = document.getElementById("world-dir-title");
    if (title) title.textContent = "世界目錄";
    hideError();
    setupData = null;
    lastBeat = null;
    sheet = null;
    if (window.NovelSetup) window.NovelSetup.hidePlayChrome();
    await loadHealth();
    await refreshSetup();
    if (mode === "play") {
      const jid = localStorage.getItem(JOB_KEY);
      if (jid) pollJob(jid);
    }
  }

  function renderWorldDirectory(seeds, worlds) {
    const body = document.getElementById("world-dir-body");
    if (!body) return;
    body.innerHTML = "";
    const current = localStorage.getItem(WORLD_KEY);

    const seedSec = document.createElement("section");
    seedSec.className = "world-dir-section";
    const seedH = document.createElement("h3");
    seedH.textContent = "劇本（SEED）";
    seedSec.appendChild(seedH);
    (seeds || []).forEach((s) => {
      const row = document.createElement("div");
      row.className = "world-dir-seed";
      const title = document.createElement("div");
      title.className = "world-dir-seed-title";
      title.textContent = s.title || s.app_id;
      const btn = document.createElement("button");
      btn.type = "button";
      btn.className = "header-btn";
      btn.textContent = "新開";
      btn.addEventListener("click", () => {
        closeWorldDirectory();
        createNewWorld(s.app_id);
      });
      row.appendChild(title);
      row.appendChild(btn);
      seedSec.appendChild(row);
    });
    body.appendChild(seedSec);

    const worldsSec = document.createElement("section");
    worldsSec.className = "world-dir-section";
    const worldsH = document.createElement("h3");
    worldsH.textContent = mode === "world_pick" ? "選擇存檔或從上方新開" : "我的存檔";
    worldsSec.appendChild(worldsH);
    if (!worlds || !worlds.length) {
      const empty = document.createElement("p");
      empty.className = "world-dir-row-meta";
      empty.textContent = "尚無存檔，請從上方劇本新開世界。";
      worldsSec.appendChild(empty);
    } else {
      (worlds || []).forEach((w) => {
        const row = document.createElement("div");
        row.className = "world-dir-row" + (w.world_id === current ? " active" : "");
        const main = document.createElement("button");
        main.type = "button";
        main.className = "world-dir-row-main";
        const t = document.createElement("div");
        t.className = "world-dir-row-title";
        t.textContent = w.title || w.world_id;
        const meta = document.createElement("div");
        meta.className = "world-dir-row-meta";
        meta.textContent = (w.story_title || w.app_id || "") + (w.has_session ? " · 已開局" : "");
        main.appendChild(t);
        main.appendChild(meta);
        main.addEventListener("click", async () => {
          closeWorldDirectory();
          await enterSelectedWorld(w.world_id);
        });
        const actions = document.createElement("div");
        actions.className = "world-dir-row-actions";
        const del = document.createElement("button");
        del.type = "button";
        del.className = "header-btn header-btn-danger";
        del.textContent = "刪";
        del.addEventListener("click", async (ev) => {
          ev.stopPropagation();
          closeWorldDirectory();
          localStorage.setItem(WORLD_KEY, w.world_id);
          await deleteCurrentWorld();
        });
        actions.appendChild(del);
        row.appendChild(main);
        row.appendChild(actions);
        worldsSec.appendChild(row);
      });
    }
    body.appendChild(worldsSec);
  }

  async function openWorldDirectory() {
    if (activeJobId) {
      showError("劇情處理中，請稍候再開世界目錄");
      return;
    }
    setLoading(true, "載入世界目錄…");
    try {
      const [seedData, worldData] = await Promise.all([
        api("/api/seeds"),
        api("/api/worlds"),
      ]);
      storySeeds = seedData.seeds || [];
      worldList = worldData.worlds || [];
      renderWorldDirectory(storySeeds, worldList);
      renderWorldSelect(worldList);
      const overlay = document.getElementById("world-dir-overlay");
      overlay.classList.remove("hidden");
      overlay.setAttribute("aria-hidden", "false");
    } catch (e) {
      showError(e.message || "無法載入世界目錄");
    } finally {
      setLoading(false);
    }
  }

  async function loadStorySeeds() {
    try {
      const data = await api("/api/seeds");
      storySeeds = data.seeds || [];
    } catch {
      storySeeds = [];
    }
  }

  async function ensureWorld() {
    await loadWorldList();
    return localStorage.getItem(WORLD_KEY);
  }

  async function switchWorld(worldId) {
    if (!worldId) return;
    if (worldId === localStorage.getItem(WORLD_KEY) && mode !== "world_pick") return;
    clearPoll();
    localStorage.removeItem(JOB_KEY);
    activeJobId = null;
    await enterSelectedWorld(worldId);
  }

  async function deleteCurrentWorld() {
    if (activeJobId) {
      showError("劇情處理中，請稍候再刪除");
      return;
    }
    const wid = localStorage.getItem(WORLD_KEY);
    if (!wid) return;
    const sel = document.getElementById("world-select");
    const title =
      (sel && sel.selectedOptions && sel.selectedOptions[0] && sel.selectedOptions[0].textContent) ||
      wid;
    const msg =
      `確定刪除「${title}」？\n\n` +
      "此操作無法復原：章節正文、圖狀態、編劇／作者對話與進度檔案都會永久刪除。";
    if (!window.confirm(msg)) return;
    clearPoll();
    localStorage.removeItem(JOB_KEY);
    activeJobId = null;
    hideError();
    setLoading(true, "刪除世界…");
    setBeatBusy(true);
    try {
      await api("/api/worlds/" + encodeURIComponent(wid), { method: "DELETE" });
      localStorage.removeItem(WORLD_KEY);
      mode = "world_pick";
      setupData = null;
      lastBeat = null;
      sheet = null;
      if (window.NovelSetup) window.NovelSetup.hidePlayChrome();
      await loadWorldList();
      await showWorldPickGate();
    } catch (e) {
      const errMsg =
        e.body?.errors?.join(" ") ||
        e.body?.detail?.errors?.join(" ") ||
        e.message ||
        "刪除世界失敗";
      showError(errMsg);
    } finally {
      setLoading(false);
      setBeatBusy(false);
    }
  }

  async function createNewWorld(appId) {
    if (activeJobId) {
      showError("劇情處理中，請稍候再開新世界");
      return;
    }
    if (!appId && storySeeds.length === 1) {
      appId = storySeeds[0].app_id;
    }
    if (!appId && storySeeds.length > 1) {
      await openWorldDirectory();
      return;
    }
    const seed = storySeeds.find((s) => s.app_id === appId);
    const seedTitle = seed ? seed.title : "";
    const title = window.prompt(
      seedTitle ? `「${seedTitle}」存檔名稱（可留空）` : "新世界名稱（可留空）",
      ""
    );
    if (title === null) return;
    setLoading(true, "建立世界…");
    try {
      const body = { title: title.trim(), expand_catalog: false };
      if (appId) body.app_id = appId;
      const created = await api("/api/worlds", {
        method: "POST",
        body: JSON.stringify(body),
      });
      localStorage.setItem(WORLD_KEY, created.world_id);
      worldList.unshift({
        world_id: created.world_id,
        title: created.title || created.world_id,
        app_id: created.app_id,
        story_title: created.story_title,
      });
      renderWorldSelect(worldList);
      await enterSelectedWorld(created.world_id);
    } catch (e) {
      showError(e.message || "建立世界失敗");
    } finally {
      setLoading(false);
    }
  }

  async function fetchAuthConfig() {
    const res = await fetch("/api/auth/config");
    if (!res.ok) throw new Error("auth config failed");
    return res.json();
  }

  function showAuthError(msg) {
    const el = document.getElementById("auth-error");
    el.textContent = msg || "登入失敗";
    el.classList.remove("hidden");
  }

  function hideAuthError() {
    document.getElementById("auth-error").classList.add("hidden");
  }

  function showAuthOverlay() {
    const el = document.getElementById("auth-overlay");
    el.classList.remove("hidden");
    el.setAttribute("aria-hidden", "false");
    document.getElementById("app-main").classList.add("hidden");
    document.querySelector("header").classList.add("hidden");
  }

  function hideAuthOverlay() {
    const el = document.getElementById("auth-overlay");
    el.classList.add("hidden");
    el.setAttribute("aria-hidden", "true");
    document.getElementById("app-main").classList.remove("hidden");
    document.querySelector("header").classList.remove("hidden");
  }

  async function completeGoogleLogin(credential) {
    hideAuthError();
    const res = await fetch("/api/auth/google", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ credential }),
    });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) {
      const err =
        data?.error === "email_not_allowed"
          ? "此 Google 帳號未獲授權"
          : data?.error || "登入失敗";
      showAuthError(err);
      return;
    }
    localStorage.setItem(ACCESS_TOKEN_KEY, data.access_token);
    localStorage.removeItem(WORLD_KEY);
    hideAuthOverlay();
    if (!appStarted) {
      appStarted = true;
      await startApp();
    }
  }

  function loadGoogleSignIn(clientId) {
    return new Promise((resolve, reject) => {
      if (window.google && window.google.accounts) {
        resolve();
        return;
      }
      const existing = document.getElementById("gsi-script");
      if (existing) {
        existing.addEventListener("load", () => resolve(), { once: true });
        existing.addEventListener("error", () => reject(new Error("gsi load failed")), {
          once: true,
        });
        return;
      }
      const script = document.createElement("script");
      script.id = "gsi-script";
      script.src = "https://accounts.google.com/gsi/client";
      script.async = true;
      script.defer = true;
      script.onload = () => resolve();
      script.onerror = () => reject(new Error("gsi load failed"));
      document.head.appendChild(script);
    }).then(() => {
      window.google.accounts.id.initialize({
        client_id: clientId,
        callback: (response) => {
          completeGoogleLogin(response.credential);
        },
      });
      const host = document.getElementById("google-signin-btn");
      host.innerHTML = "";
      window.google.accounts.id.renderButton(host, {
        type: "standard",
        theme: "filled_black",
        size: "large",
        text: "signin_with",
        shape: "rectangular",
        width: 280,
      });
    });
  }

  async function ensureGuestToken() {
    if (localStorage.getItem(ACCESS_TOKEN_KEY)) return true;
    const res = await fetch("/api/auth/guest", { method: "POST" });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) {
      showAuthError(data?.error || "無法建立玩家身份");
      return false;
    }
    localStorage.setItem(ACCESS_TOKEN_KEY, data.access_token);
    localStorage.removeItem(USER_KEY);
    return true;
  }

  async function ensureAuthenticated() {
    authConfig = await fetchAuthConfig();
    if (authConfig.auth_mode === "guest") {
      return ensureGuestToken();
    }
    if (authConfig.auth_mode !== "google") return true;
    if (localStorage.getItem(ACCESS_TOKEN_KEY)) return true;
    showAuthOverlay();
    await loadGoogleSignIn(authConfig.google_client_id);
    return false;
  }

  function formatApiError(err) {
    const body = err.body;
    if (body) {
      if (Array.isArray(body.errors) && body.errors.length) {
        return body.errors.join(" ");
      }
      const detail = body.detail ?? body;
      if (typeof detail === "string" && detail.trim()) {
        return detail;
      }
      if (detail && Array.isArray(detail.errors) && detail.errors.length) {
        return detail.errors.join(" ");
      }
      if (detail && typeof detail.error === "string" && detail.error.trim()) {
        return detail.error;
      }
    }
    if (err.message && err.message !== "Bad Gateway") {
      return err.message;
    }
    if (err.status === 502) {
      return "後端讀取遊戲圖失敗（session 可能未 bootstrap）。請重開 session 或新開世界。";
    }
    if (err.status === 503) {
      return "MemNet 或 session 不可用。請確認 memnet serve 已啟動，並重開 session。";
    }
    return err.message || "請求失敗";
  }

  async function api(path, opts = {}) {
    const res = await fetch(path, {
      ...opts,
      headers: {
        "Content-Type": "application/json",
        ...authHeaders(),
        ...scopeHeaders(),
        ...(opts.headers || {}),
      },
    });
    const text = await res.text();
    let data = null;
    try {
      data = text ? JSON.parse(text) : null;
    } catch {
      data = { raw: text };
    }
    if (!res.ok) {
      if (
        res.status === 401 &&
        authConfig &&
        authConfig.auth_mode === "google" &&
        localStorage.getItem(ACCESS_TOKEN_KEY)
      ) {
        localStorage.removeItem(ACCESS_TOKEN_KEY);
        appStarted = false;
        showAuthOverlay();
        if (authConfig.google_client_id) {
          loadGoogleSignIn(authConfig.google_client_id).catch(() => {
            showAuthError("無法載入 Google 登入");
          });
        }
      }
      const err = new Error(formatApiError({ body: data?.detail || data, status: res.status, message: res.statusText }));
      err.status = res.status;
      err.body = data?.detail || data;
      throw err;
    }
    return data;
  }

  function setTitle(title) {
    document.title = title;
    document.getElementById("app-title").textContent = title;
  }

  function showError(msg) {
    const el = document.getElementById("error-banner");
    document.getElementById("error-text").textContent = msg || "發生錯誤";
    el.classList.remove("hidden");
  }

  function hideError() {
    document.getElementById("error-banner").classList.add("hidden");
  }

  function setLoading(visible, phase) {
    const el = document.getElementById("loading-banner");
    if (!visible) {
      el.classList.add("hidden");
      return;
    }
    el.classList.remove("hidden");
    document.getElementById("loading-text").textContent =
      phaseLabels[phase] || phase || "處理中…";
  }

  function setBeatBusy(busy) {
    const sel =
      "#panel-choices button, #tab-bar button, #btn-submit, .sheet-close-btn, .sheet-backdrop, " +
      ".sub-actions button, .panel button";
    document.querySelectorAll(sel).forEach((b) => {
      b.disabled = busy;
    });
    document.getElementById("input-text").disabled = busy;
  }

  function clearPoll() {
    if (pollTimer) {
      clearTimeout(pollTimer);
      pollTimer = null;
    }
  }

  async function pollJob(jobId) {
    activeJobId = jobId;
    localStorage.setItem(JOB_KEY, jobId);
    pollStarted = Date.now();
    setBeatBusy(true);
    hideError();

    async function tick() {
      if (Date.now() - pollStarted > TIMEOUT_MS) {
        clearPoll();
        localStorage.removeItem(JOB_KEY);
        activeJobId = null;
        setBeatBusy(false);
        setLoading(false);
        showError("逾時");
        return;
      }
      try {
        const job = await api("/api/beat/jobs/" + jobId);
        setLoading(job.status === "running" || job.status === "queued", job.phase);
        if (job.status === "done") {
          clearPoll();
          localStorage.removeItem(JOB_KEY);
          activeJobId = null;
          setBeatBusy(false);
          setLoading(false);
          lastBeat = job.result;
          if (window.NovelPlay) window.NovelPlay.renderBeat(job.result);
          await refreshSheet();
          return;
        }
        if (job.status === "error") {
          clearPoll();
          localStorage.removeItem(JOB_KEY);
          activeJobId = null;
          setBeatBusy(false);
          setLoading(false);
          showError(job.error || job.result?.error || "beat 失敗");
          return;
        }
      } catch (e) {
        if (e.status === 404) {
          clearPoll();
          localStorage.removeItem(JOB_KEY);
          activeJobId = null;
          setBeatBusy(false);
          setLoading(false);
          try {
            lastBeat = await api("/api/beat/last");
            if (window.NovelPlay) window.NovelPlay.renderBeat(lastBeat);
          } catch {
            /* no last beat */
          }
          return;
        }
      }
      pollTimer = setTimeout(tick, POLL_MS);
    }
    tick();
  }

  async function postBeat(body) {
    hideError();
    setBeatBusy(true);
    try {
      const res = await api("/api/beat", { method: "POST", body: JSON.stringify(body) });
      await pollJob(res.job_id);
    } catch (e) {
      setBeatBusy(false);
      showError(formatApiError(e) || "beat 請求失敗");
    }
  }

  async function refreshSheet() {
    if (mode !== "play") return;
    try {
      sheet = await api("/api/player/sheet");
      if (window.NovelSheet) window.NovelSheet.render(sheet);
    } catch {
      /* sheet optional during M1 */
    }
    try {
      if (window.NovelSheet) await window.NovelSheet.renderParty();
    } catch {
      /* party optional */
    }
  }

  async function ensureSession() {
    health = await api("/api/health");
    setTitle(health.title || "Novel");
    const wid = localStorage.getItem(WORLD_KEY);
    if (
      wid &&
      health.issues &&
      health.issues.includes("no_session")
    ) {
      await api("/api/session/rebootstrap", { method: "POST", body: "{}" });
      health = await api("/api/health");
    }
    if (!health.ok && health.issues && wid) {
      showError("啟動檢查：" + health.issues.join(", "));
    }
    return health;
  }

  async function loadHealth() {
    return ensureSession();
  }

  async function restartSession() {
    if (mode === "world_pick" || !localStorage.getItem(WORLD_KEY)) {
      showError("請先選擇或新開世界");
      return;
    }
    const msg =
      "確定重開 session？\n\n將建立新局：圖狀態、開局進度、編劇／作者對話與上一拍快取都會清除。";
    if (!window.confirm(msg)) return;
    clearPoll();
    localStorage.removeItem(JOB_KEY);
    activeJobId = null;
    hideError();
    setLoading(true, "重開 session…");
    setBeatBusy(true);
    try {
      const res = await api("/api/session/rebootstrap", {
        method: "POST",
        body: "{}",
      });
      mode = "setup";
      setupData = res.player_setup || null;
      lastBeat = null;
      sheet = null;
      if (window.NovelSetup) window.NovelSetup.hidePlayChrome();
      await loadHealth();
      if (setupData && setupData.setup_complete) {
        await enterPlay();
      } else if (setupData && window.NovelSetup) {
        window.NovelSetup.render(setupData);
      } else {
        await refreshSetup();
      }
    } catch (e) {
      const errMsg =
        e.body?.errors?.join(" ") ||
        e.body?.detail?.errors?.join(" ") ||
        e.message ||
        "重開 session 失敗";
      showError(errMsg);
    } finally {
      setLoading(false);
      setBeatBusy(false);
    }
  }

  async function refreshSetup() {
    try {
      setupData = await api("/api/setup");
    } catch (e) {
      showError(formatApiError(e));
      throw e;
    }
    if (setupData.setup_complete) {
      await enterPlay();
      return;
    }
    if (window.NovelSetup) window.NovelSetup.render(setupData);
  }

  async function enterPlay() {
    mode = "play";
    await loadHealth();
    formatPlay =
      (setupData && setupData.setup_guidance && setupData.setup_guidance.format_play) ||
      formatPlay;
    document.getElementById("setup-actions").classList.add("hidden");
    document.getElementById("panel-text").classList.remove("hidden");
    document.getElementById("tab-bar").classList.remove("hidden");
    if (window.NovelPlay) window.NovelPlay.showPlayChrome();
    try {
      lastBeat = await api("/api/beat/last");
    } catch {
      lastBeat = null;
    }
    if (window.NovelPlay) window.NovelPlay.renderBeat(lastBeat);
    await refreshSheet();
  }

  async function startApp() {
    document.getElementById("btn-retry").addEventListener("click", () => {
      hideError();
      if (mode === "world_pick") {
        loadWorldList().then(() => showWorldPickGate());
      } else if (mode === "setup") {
        refreshSetup();
      }
    });
    document.getElementById("btn-restart-session").addEventListener("click", () => {
      if (activeJobId) {
        showError("劇情處理中，請稍候再重開");
        return;
      }
      restartSession();
    });
    const worldSel = document.getElementById("world-select");
    if (worldSel) {
      worldSel.addEventListener("change", () => switchWorld(worldSel.value));
    }
    const btnWorldDir = document.getElementById("btn-world-dir");
    if (btnWorldDir) {
      btnWorldDir.addEventListener("click", () => openWorldDirectory());
    }
    const worldDirClose = document.getElementById("world-dir-close");
    const worldDirBackdrop = document.getElementById("world-dir-backdrop");
    if (worldDirClose) worldDirClose.addEventListener("click", closeWorldDirectory);
    if (worldDirBackdrop) worldDirBackdrop.addEventListener("click", closeWorldDirectory);
    const btnDeleteWorld = document.getElementById("btn-delete-world");
    if (btnDeleteWorld) {
      btnDeleteWorld.addEventListener("click", () => deleteCurrentWorld());
    }
    document.getElementById("btn-submit").addEventListener("click", () => {
      const text = document.getElementById("input-text").value.trim();
      if (!text || activeJobId || mode === "world_pick") return;
      if (mode === "setup" && window.NovelSetup) {
        window.NovelSetup.onSubmit(text);
      } else if (mode === "play") {
        postBeat({ steering: text });
        document.getElementById("input-text").value = "";
      }
    });

    document.addEventListener("visibilitychange", () => {
      if (document.visibilityState !== "visible") return;
      const jid = localStorage.getItem(JOB_KEY);
      if (jid && !activeJobId) pollJob(jid);
    });

    await loadWorldList();
    if (!hasValidWorldSelection()) {
      setLoading(true, "載入世界…");
      try {
        await showWorldPickGate();
      } finally {
        setLoading(false);
      }
      return;
    }
    setLoading(true, "載入世界…");
    try {
      await enterSelectedWorld(localStorage.getItem(WORLD_KEY));
    } finally {
      setLoading(false);
    }
  }

  async function init() {
    try {
      const ready = await ensureAuthenticated();
      if (!ready) return;
      appStarted = true;
      try {
        const h = await api("/api/health");
        if (h.title) setTitle(h.title);
      } catch {
        /* title updated again after world load */
      }
      await startApp();
    } catch (e) {
      setTitle("連線失敗");
      showError(
        e.message ||
          "無法連線伺服器。請確認手機與電腦在同一 Wi‑Fi，且防火牆允許連入埠 8765。"
      );
    }
  }

  document.addEventListener("DOMContentLoaded", init);

  return {
    api,
    postBeat,
    refreshSetup,
    restartSession,
    refreshSheet,
    enterPlay,
    get mode() { return mode; },
    get setupData() { return setupData; },
    get sheet() { return sheet; },
    get health() { return health; },
    setLoading,
    showError,
    hideError,
    setBeatBusy,
    pollJob,
    get activeJobId() { return activeJobId; },
    get formatPlay() { return formatPlay; },
  };
})();
