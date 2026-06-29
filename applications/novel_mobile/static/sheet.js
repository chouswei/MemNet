/** Facade: wire tab bar to separate items / skills / production panels. */
window.NovelSheet = (function () {
  const PANELS = {
    items: () => window.NovelItemsPanel,
    skills: () => window.NovelSkillsPanel,
    production: () => window.NovelProductionPanel,
    party: () => window.NovelPartyPanel,
  };

  let tabsBound = false;

  function panelFor(tab) {
    const factory = PANELS[tab];
    return factory ? factory() : null;
  }

  function initTabs() {
    window.NovelItemsPanel.bind();
    window.NovelSkillsPanel.bind();
    window.NovelProductionPanel.bind();
    window.NovelPartyPanel.bind();
    window.NovelSheetCommon.bindEscape();

    if (tabsBound) return;
    tabsBound = true;

    document.querySelectorAll("#tab-bar button").forEach((btn) => {
      btn.addEventListener("click", () => {
        const tab = btn.dataset.tab;
        const p = panelFor(tab);
        if (!p) return;
        if (tab === "party") {
          if (p.isOpen()) p.close();
          else p.open();
          return;
        }
        if (window.NovelPartyPanel && window.NovelPartyPanel.isOpen()) {
          window.NovelPartyPanel.close();
        }
        if (p.isOpen()) p.close();
        else p.open();
      });
    });
  }

  function render(data) {
    window.NovelItemsPanel.render(data.items || []);
    window.NovelSkillsPanel.render(data.arts || [], data.body_stats || []);
    window.NovelProductionPanel.render(data.production || {});
  }

  async function renderParty() {
    if (window.NovelPartyPanel && window.NovelPartyPanel.isOpen()) {
      await window.NovelPartyPanel.open();
    } else if (window.NovelPartyPanel) {
      try {
        const data = await window.NovelApp.api("/api/party/panel");
        window.NovelPartyPanel.render(data);
      } catch {
        window.NovelPartyPanel.render({ members: [], ui_note: "" });
      }
    }
  }

  function openSheet(tab, titleOverride) {
    const p = panelFor(tab);
    if (p) p.open(titleOverride);
  }

  function closeSheet() {
    window.NovelSheetCommon.closeAll();
  }

  function isOpen() {
    return (
      window.NovelSheetCommon.isAnyOpen() ||
      (window.NovelPartyPanel && window.NovelPartyPanel.isOpen())
    );
  }

  return { render, renderParty, initTabs, openSheet, closeSheet, isOpen };
})();
