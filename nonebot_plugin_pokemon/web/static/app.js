(() => {
  const BASE = location.pathname.replace(/\/+$/, "");
  const $ = (sel) => document.querySelector(sel);

  async function csrfToken() {
    const response = await fetch("/qweb/api/v1/auth/session", { credentials: "same-origin", cache: "no-store" });
    if (!response.ok) throw new Error("无法读取登录会话");
    const session = await response.json();
    if (!session.csrf_token) throw new Error("请登录七七");
    return session.csrf_token;
  }

  let userName = "";
  let awaiting = false;
  let menuData = null;

  async function api(path, options) {
    const opts = Object.assign({}, options || {});
    opts.headers = { "Content-Type": "application/json", ...opts.headers };
    if (!["GET", "HEAD"].includes((opts.method || "GET").toUpperCase())) {
      opts.headers["X-CSRF-Token"] = await csrfToken();
    }
    const response = await fetch(BASE + path, opts);
    const text = await response.text();
    let data = null;
    try { data = text ? JSON.parse(text) : null; } catch (_) { data = { text }; }
    if (!response.ok) {
      throw new Error((data && (data.detail || data.error)) || ("HTTP " + response.status));
    }
    return data;
  }

  function esc(text) {
    return String(text == null ? "" : text).replace(/[&<>"']/g, (ch) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[ch]));
  }

  function addMessage(who, content, buttons, images) {
    const wrap = document.createElement("div");
    wrap.className = "msg " + (who === "me" ? "me" : "");
    const avatar = document.createElement("div");
    avatar.className = "avatar";
    avatar.textContent = who === "me" ? "我" : "宝";
    const bubble = document.createElement("div");
    bubble.className = "bubble";
    bubble.innerHTML = esc(content || "").replace(/\n/g, "<br>");
    (images || []).forEach((src) => {
      const img = document.createElement("img");
      img.src = src;
      img.alt = "游戏图片";
      bubble.appendChild(img);
    });
    (buttons || []).forEach((btn, index) => {
      const action = btn.data || btn.text;
      let tag;
      if (btn.action === 0 || /^https?:\/\//.test(action)) {
        tag = document.createElement("a");
        tag.href = action;
        tag.target = "_blank";
        tag.rel = "noopener noreferrer";
      } else {
        tag = document.createElement("button");
        tag.onclick = () => sendCommand(action);
      }
      tag.className = "tag";
      tag.textContent = btn.text || action;
      tag.title = action || "";
      tag.style.marginRight = "6px";
      bubble.appendChild(tag);
    });
    wrap.appendChild(avatar);
    wrap.appendChild(bubble);
    $("#console").appendChild(wrap);
    $("#console").scrollTop = $("#console").scrollHeight;
  }

  function renderResult(result) {
    const messages = result.messages || [];
    if (!messages.length) {
      if (result.error) addMessage("bot", "⚠ " + result.error);

      return;
    }
    messages.forEach((msg) => {
      const segments = msg.segments || [];
      const text = segments.filter((s) => s.type === "text" && s.data).map((s) => s.data).join("");
      const images = segments.filter((s) => s.type === "image" && s.data).map((s) => s.data);
      if (text || images.length) addMessage("bot", text, result.buttons || [], images);
    });
    if (result.error) addMessage("bot", "⚠ " + result.error);
  }

  async function followResult(result) {
    while (true) {
      if (result.superseded) return;
      renderResult(result);
      awaiting = !!result.awaiting;
      updateAwaiting();
      if (awaiting || result.done || result.error) return;
      await new Promise(resolve => setTimeout(resolve, 750));
      const params = new URLSearchParams({ operation: result.operation, offset: String(result.offset) });
      result = await api("/api/session?" + params);
    }
  }

  async function sendCommand(text) {
    text = String(text || "").trim();
    if (!text) return;
    addMessage("me", text);
    $("#command-input").value = "";
    $("#send-command").disabled = true;
    try {
      const result = await api("/api/command", {
        method: "POST",
        body: JSON.stringify({ text }),
      });
      await followResult(result);
      await refreshProfile();
    } catch (err) {
      addMessage("bot", "⚠ " + err.message);
    } finally {
      $("#send-command").disabled = false;
      $("#command-input").focus();
    }
  }

  function updateAwaiting() {
    $("#awaiting-hint").textContent = awaiting ? "等待你的选择… 可点击上方按钮或输入内容" : "";
    const cancel = $("#cancel-interaction");
    if (!cancel) {
      const btn = document.createElement("button");
      btn.id = "cancel-interaction";
      btn.className = "tag";
      btn.textContent = "取消连续交互";
      btn.onclick = async () => {
        await api("/api/cancel", { method: "POST", body: "{}" });
        awaiting = false;
        updateAwaiting();
        addMessage("bot", "已取消当前连续交互。");
      };
      $("#context-buttons").appendChild(btn);
    }
    cancel && (cancel.style.display = awaiting ? "inline-block" : "none");
  }

  async function refreshProfile() {
    try {
      const data = await api("/api/bootstrap");
      const p = data.profile;
      const identity = data.identity || {};
      userName = identity.user_name || p.nickname || "";
      $("#nickname").textContent = p.nickname || "未开局";
      $("#who").textContent = userName || "网页玩家";
      $("#admin-badge").textContent = identity.is_admin ? " · 管理员" : "";
      const adminTab = $("#tab-admin");
      if (adminTab) adminTab.style.display = identity.is_admin ? "" : "none";
      $("#title-chip").textContent = p.title || "";
      $("#place").textContent = p.score ? (p.region ? p.region + " · " : "") + (p.map || "未知地点") : "尚未领取初始精灵";
      $("#score").textContent = p.score;
      $("#rep").textContent = p.reputation;
      $("#poke-count").textContent = p.pokemon_count;
      $("#dungeon").textContent = p.dungeon_floor;
      const row = $("#team-row");
      row.innerHTML = "";
      (p.team || []).forEach((m) => {
        const pill = document.createElement("span");
        pill.className = "poke-pill";
        pill.textContent = m.name + " Lv." + m.level;
        pill.title = (m.types || []).join("/");
        row.appendChild(pill);
      });
    } catch (err) {
      $("#who").textContent = "身份未通过宿主校验";
    }
  }

  function renderMenu() {
    if (!menuData) return;
    const root = $("#menu-list");
    root.innerHTML = "";
    const categories = menuData.categories || {};
    Object.keys(categories).forEach((category) => {
      const detail = document.createElement("details");
      detail.className = "menu-cat";
      detail.open = category === "基础" || category === "养成";
      const summary = document.createElement("summary");
      summary.innerHTML = "<span>" + esc(category) + "</span><span>" + categories[category].length + "</span>";
      detail.appendChild(summary);
      categories[category].forEach((item) => {
        if (item.pmn_hidden) return;
        const btn = document.createElement("button");
        btn.className = "menu-item";
        btn.innerHTML = "<b>" + esc(item.func) + "</b><span>" + esc(item.trigger_method || "") + "</span>";
        btn.title = item.brief_des || "";
        btn.onclick = () => {
          const trigger = (item.trigger_method || "").replace(/[`]/g, "");
          const first = trigger.split(" / ")[0].trim();
          if (first.includes("...") || first.includes(" ")) {
            $("#command-input").value = first.replace(/\.\.\./g, " ");
            $("#command-input").focus();
          } else {
            sendCommand(first);
          }
        };
        detail.appendChild(btn);
      });
      root.appendChild(detail);
    });
  }

  async function loadMenu(query) {
    const data = await api("/api/menu" + (query ? "?q=" + encodeURIComponent(query) : ""));
    menuData = data;
    renderMenu();
  }

  async function loadDex(query) {
    const grid = $("#dex-grid");
    $("#dex-detail").innerHTML = "";
    if (!query) { grid.innerHTML = '<span class="muted">输入名称或编号开始搜索，例如 皮卡丘。</span>'; return; }
    try {
      const data = await api("/api/pokedex?q=" + encodeURIComponent(query));
      grid.innerHTML = "";
      (data.items || []).forEach((item) => {
        const card = document.createElement("div");
        card.className = "dex-card";
        card.innerHTML = "<b>#" + item.id + " " + esc(item.name) + "</b><span>" + esc((item.types || []).join(" / ")) + " · 种族值 " + item.base_total + "</span>";
        card.onclick = () => showDex(item.name);
        grid.appendChild(card);
      });
      if (!(data.items || []).length) grid.innerHTML = '<span class="muted">没有找到。</span>';
    } catch (err) { grid.innerHTML = '<span class="err">' + esc(err.message) + "</span>"; }
  }

  async function showDex(name) {
    try {
      const data = await api("/api/pokedex?name=" + encodeURIComponent(name));
      const e = data.entry;
      const stats = Object.entries(e.base_stats).map(([k, v]) => {
        const width = Math.min(100, v / 1.8);
        return '<div style="margin:6px 0"><span class="muted">' + esc(k) + " " + v + '</span><div style="height:6px;border-radius:6px;background:rgba(120,160,230,.14)"><div style="height:6px;width:' + width + '%;border-radius:6px;background:linear-gradient(90deg,#6fb1ff,#7de2c3)"></div></div></div>';
      }).join("");
      $("#dex-detail").innerHTML = '<div class="panel" style="margin-top:14px;padding:16px"><h2 style="margin:0 0 8px">' + esc(e.name) + " <span class='muted'>#" + e.id + "</span></h2><div class='muted'>" + esc((e.types || []).join(" / ")) + " · 种族值总和 " + e.base_total + "</div>" + stats + '<p style="line-height:1.7;color:#cfe0ff">' + esc(e.description) + "</p></div>";
    } catch (err) { $("#dex-detail").innerHTML = '<span class="err">' + esc(err.message) + "</span>"; }
  }

  async function loadAnalytics() {
    try {
      const overview = await api("/api/analytics/overview");
      const kpis = [
        ["训练家", overview.players],
        ["宝可梦记录", overview.pokemon_records],
        ["平均等级", overview.average_level],
        ["平均金币", overview.average_score],
      ];
      $("#kpis").innerHTML = kpis.map(([k, v]) => '<div class="kpi"><span>' + k + "</span><b>" + v + "</b></div>").join("");
      const stamp = "?t=" + Date.now();
      const charts = ["team_radar", "team_levels", "team_types"];
      $("#player-charts").innerHTML = charts.map((kind) => '<div class="chart-card"><h3>' + kind + '</h3><img src="' + BASE + "/api/charts/" + kind + stamp + '" alt="' + kind + '"></div>').join("");
      const globals = ["popular_species", "level_distribution"];
      $("#global-charts").innerHTML = globals.map((kind) => '<div class="chart-card"><h3>' + kind + '</h3><img src="' + BASE + "/api/charts/" + kind + stamp + '" alt="' + kind + '"></div>').join("");
      const rank = await api("/api/leaderboard/score");
      $("#rank-list").innerHTML = (rank.items || []).map((item, i) => '<div class="rank"><span><i>' + (i + 1) + "</i>" + esc(item.nickname) + "</span><b>" + item.score + "</b></div>").join("");
    } catch (err) { $("#rank-list").innerHTML = '<span class="err">' + esc(err.message) + "</span>"; }
  }

  async function loadAdmin() {
    try {
      const data = await api("/api/admin/state");
      const kpis = [
        ["数据目录", data.data_dir],
        ["图标", data.icons],
        ["闪光图标", data.star_icons],
        ["菜单条目", data.menu_entries],
        ["玩家", data.players],
        ["宝可梦记录", data.pokemon_records],
        ["工具注册", data.tools_registered ? "是" : "否"],
        ["网页会话", data.web_sessions],
      ];
      $("#admin-kpis").innerHTML = kpis.map(([k, v]) => '<div class="kpi"><span>' + k + "</span><b style='font-size:13px'>" + esc(v) + "</b></div>").join("");
      $("#admin-jobs").innerHTML = (data.scheduler_jobs || []).map((name) => '<div class="rank"><span>' + esc(name) + "</span><b>定时</b></div>").join("") || '<span class="muted">没有定时任务</span>';
    } catch (err) {
      $("#admin-kpis").innerHTML = '<span class="err">' + esc(err.message) + "</span>";
    }
  }

  // events
  document.querySelectorAll(".tab").forEach((tab) => {
    tab.onclick = () => {
      document.querySelectorAll(".tab").forEach((t) => t.classList.toggle("active", t === tab));
      document.querySelectorAll(".view").forEach((v) => v.classList.toggle("active", v.id === "view-" + tab.dataset.view));
      if (tab.dataset.view === "analytics") loadAnalytics();
      if (tab.dataset.view === "admin") loadAdmin();
      if (tab.dataset.view === "dex") loadDex($("#dex-search").value.trim());
    };
  });
  $("#send-command").onclick = () => sendCommand($("#command-input").value);
  $("#command-input").addEventListener("keydown", (e) => {
    if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); sendCommand($("#command-input").value); }
  });
  $("#menu-search").addEventListener("input", (e) => loadMenu(e.target.value.trim()));
  $("#dex-search").addEventListener("input", (e) => loadDex(e.target.value.trim()));
  $("#admin-refresh").onclick = loadAdmin;
  $("#admin-download").onclick = async () => {
    try {
      await api("/api/admin/resource/download", { method: "POST", body: "{}" });
      addMessage("bot", "已开始后台下载全部素材，完成后日志会显示结果。");
    } catch (err) { addMessage("bot", "⚠ " + err.message); }
  };
  $("#admin-reload").onclick = async () => {
    try {
      const r = await api("/api/admin/reload", { method: "POST", body: "{}" });
      addMessage("bot", "已重载菜单与工具：" + (r.tools_registered ? "工具已注册" : "MoEllmChats 未安装或名称冲突"));
    } catch (err) { addMessage("bot", "⚠ " + err.message); }
  };

  (async () => {
    addMessage("bot", "欢迎来到宝可梦网页版。先发送 `领取初始精灵 小火龙` 开局，或点击左侧功能目录。");
    await refreshProfile();
    await loadMenu("");
    const current = await api("/api/session");
    if (current.operation) await followResult(current);
    const quick = ["宝可梦帮助", "领取初始精灵 小火龙", "我的精灵列表", "野外探索", "精灵状态 小火龙", "查看地图"];
    $("#quick-commands").innerHTML = "";
    quick.forEach((text) => {
      const btn = document.createElement("button");
      btn.textContent = text;
      btn.onclick = () => sendCommand(text);
      $("#quick-commands").appendChild(btn);
    });
    setInterval(refreshProfile, 60000);
  })();
})();
