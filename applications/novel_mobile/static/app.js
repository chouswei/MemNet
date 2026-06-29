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

  const phaseLabels = {
    prepare_script: "準備劇本…",
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
    if (authConfig && authConfig.auth_mode === "google") return {};
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

  function renderWorldSelect(worlds) {
    const sel = document.getElementById("world-select");
    if (!sel) return;
    const wid = localStorage.getItem(WORLD_KEY);
    sel.innerHTML = "";
    (worlds || []).forEach((w) => {
      const opt = document.createElement("option");
      opt.value = w.world_id;
      opt.textContent = w.title || w.world_id;
      if (w.world_id === wid) opt.selected = true;
      sel.appendChild(opt);
    });
    sel.classList.toggle("hidden", !(worlds && worlds.length));
    const btnNew = document.getElementById("btn-new-world");
    if (btnNew) btnNew.classList.remove("hidden");
  }

  async function ensureWorld() {
    setLoading(true, "載入世界…");
    try {
      const data = await api("/api/worlds");
      const worlds = data.worlds || [];
      let wid = localStorage.getItem(WORLD_KEY);
      const known = worlds.some((w) => w.world_id === wid);
      if (!wid || !known) {
        if (worlds.length > 0) {
          wid = worlds[0].world_id;
        } else {
          setLoading(true, "建立世界…");
          const created = await api("/api/worlds", {
            method: "POST",
            body: JSON.stringify({ title: "", expand_catalog: false }),
          });
          wid = created.world_id;
          worlds.unshift({
            world_id: wid,
            title: created.title || wid,
          });
        }
        localStorage.setItem(WORLD_KEY, wid);
      }
      renderWorldSelect(worlds);
      return wid;
    } finally {
      setLoading(false);
    }
  }

  async function switchWorld(worldId) {
    if (!worldId || worldId === localStorage.getItem(WORLD_KEY)) return;
    clearPoll();
    localStorage.removeItem(JOB_KEY);
    activeJobId = null;
    localStorage.setItem(WORLD_KEY, worldId);
    mode = "setup";
    setupData = null;
    lastBeat = null;
    sheet = null;
    hideError();
    if (window.NovelSetup) window.NovelSetup.hidePlayChrome();
    await loadHealth();
    await refreshSetup();
  }

  async function createNewWorld() {
    if (activeJobId) {
      showError("劇情處理中，請稍候再開新世界");
      return;
    }
    const title = window.prompt("新世界名稱（可留空）", "");
    if (title === null) return;
    setLoading(true, "建立世界…");
    try {
      const created = await api("/api/worlds", {
        method: "POST",
        body: JSON.stringify({ title: title.trim(), expand_catalog: false }),
      });
      localStorage.setItem(WORLD_KEY, created.world_id);
      await switchWorld(created.world_id);
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

  async function ensureAuthenticated() {
    authConfig = await fetchAuthConfig();
    if (authConfig.auth_mode !== "google") return true;
    if (localStorage.getItem(ACCESS_TOKEN_KEY)) return true;
    showAuthOverlay();
    await loadGoogleSignIn(authConfig.google_client_id);
    return false;
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
      const err = new Error(data?.detail?.error || data?.error || res.statusText);
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
      const msg =
        e.body?.errors?.join(" ") ||
        e.body?.detail?.errors?.join(" ") ||
        e.message ||
        "beat 請求失敗";
      showError(msg);
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
    if (health.issues && health.issues.includes("no_session")) {
      await api("/api/session/rebootstrap", { method: "POST", body: "{}" });
      health = await api("/api/health");
    }
    if (!health.ok && health.issues) {
      showError("啟動檢查：" + health.issues.join(", "));
    }
    return health;
  }

  async function loadHealth() {
    return ensureSession();
  }

  async function restartSession() {
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
    setupData = await api("/api/setup");
    if (setupData.setup_complete) {
      await enterPlay();
      return;
    }
    if (window.NovelSetup) window.NovelSetup.render(setupData);
  }

  async function enterPlay() {
    mode = "play";
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
      if (mode === "setup") refreshSetup();
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
    const btnNewWorld = document.getElementById("btn-new-world");
    if (btnNewWorld) {
      btnNewWorld.addEventListener("click", () => createNewWorld());
    }
    document.getElementById("btn-submit").addEventListener("click", () => {
      const text = document.getElementById("input-text").value.trim();
      if (!text || activeJobId) return;
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

    await ensureWorld();
    await loadHealth();
    await refreshSetup();
    if (mode === "play") {
      const jid = localStorage.getItem(JOB_KEY);
      if (jid) pollJob(jid);
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
