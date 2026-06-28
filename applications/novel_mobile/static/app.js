/* Shared API client and app bootstrap */
window.NovelApp = (function () {
  const POLL_MS = 2000;
  const TIMEOUT_MS = 600000;
  const JOB_KEY = "novel_mobile_job_id";
  const TOKEN_KEY = "novel_mobile_token";

  let mode = "setup";
  let health = null;
  let setupData = null;
  let lastBeat = null;
  let sheet = null;
  let activeJobId = null;
  let pollTimer = null;
  let pollStarted = 0;

  const phaseLabels = {
    prepare_script: "準備劇本…",
    oln: "寫大綱…",
    sbd: "寫分鏡…",
    scr: "寫腳本…",
    prepare_prose: "準備正文…",
    prose: "撰寫劇情…",
  };

  function authHeaders() {
    const token = localStorage.getItem(TOKEN_KEY);
    if (!token) return {};
    return { Authorization: "Bearer " + token };
  }

  async function api(path, opts = {}) {
    const res = await fetch(path, {
      ...opts,
      headers: {
        "Content-Type": "application/json",
        ...authHeaders(),
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
    const sel = "#panel-choices button, #tab-bar button, #btn-submit, .sub-actions button, .panel button";
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
    const res = await api("/api/beat", { method: "POST", body: JSON.stringify(body) });
    await pollJob(res.job_id);
  }

  async function refreshSheet() {
    if (mode !== "play") return;
    try {
      sheet = await api("/api/player/sheet");
      if (window.NovelSheet) window.NovelSheet.render(sheet);
    } catch {
      /* sheet optional during M1 */
    }
  }

  async function loadHealth() {
    health = await api("/api/health");
    setTitle(health.title || "Novel");
    if (!health.ok && health.issues) {
      showError("啟動檢查：" + health.issues.join(", "));
    }
    return health;
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

  async function init() {
    document.getElementById("btn-retry").addEventListener("click", () => {
      hideError();
      if (mode === "setup") refreshSetup();
    });
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

    await loadHealth();
    await refreshSetup();
    const jid = localStorage.getItem(JOB_KEY);
    if (jid) pollJob(jid);
  }

  document.addEventListener("DOMContentLoaded", init);

  return {
    api,
    postBeat,
    refreshSetup,
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
  };
})();
