const state = { token: null, user: null };

const $ = (id) => document.getElementById(id);

function setBusy(button, busy) {
  button.disabled = busy;
  button.setAttribute("aria-busy", String(busy));
}

function setStatus(element, message, kind = "") {
  element.textContent = message;
  if (kind) element.dataset.state = kind;
  else delete element.dataset.state;
}

async function request(path, options = {}) {
  const headers = options.headers || {};
  if (state.token) headers.Authorization = `Bearer ${state.token}`;
  if (options.body && !(options.body instanceof FormData)) {
    headers["Content-Type"] = "application/json";
    options.body = JSON.stringify(options.body);
  }
  const response = await fetch(path, { ...options, headers });
  const payload = await response.json().catch(() => ({
    code: 1500,
    message: "服务返回了无法解析的响应",
    data: null,
  }));
  if (!response.ok || payload.code !== 0) {
    throw new Error(payload.message || "请求失败");
  }
  return payload.data;
}

function showLogin() {
  $("auth-card").classList.remove("hidden");
  $("workspace").classList.add("hidden");
}

function showWorkspace() {
  $("auth-card").classList.add("hidden");
  $("workspace").classList.remove("hidden");
  $("who").textContent = `${state.user.username} · ${state.user.class_id} · ${state.user.role}`;
  $("upload-form").classList.toggle("hidden", state.user.role !== "teacher");
}

async function loadMaterials() {
  const list = $("materials");
  list.replaceChildren();
  setStatus($("materials-status"), "正在加载资料…");
  try {
    const data = await request("/api/v1/materials");
    for (const item of data.items) {
      const li = document.createElement("li");
      li.textContent = `${item.title}（${item.created_at}）`;
      list.append(li);
    }
    if (!data.items.length) setStatus($("materials-status"), "本班暂无资料", "empty");
    else setStatus($("materials-status"), "");
  } catch (error) {
    setStatus($("materials-status"), error.message, "error");
  }
}

$("auth-card").addEventListener("submit", async (event) => {
  event.preventDefault();
  const button = $("login");
  setBusy(button, true);
  setStatus($("auth-status"), "正在登录…");
  try {
    const data = await request("/api/v1/auth/login", {
      method: "POST",
      body: { username: $("username").value, password: $("password").value },
    });
    state.token = data.token;
    state.user = data.user;
    setStatus($("auth-status"), "");
    showWorkspace();
    await loadMaterials();
  } catch (error) {
    setStatus($("auth-status"), error.message, "error");
  } finally {
    setBusy(button, false);
  }
});

$("logout").addEventListener("click", async () => {
  const button = $("logout");
  setBusy(button, true);
  try {
    await request("/api/v1/auth/logout", { method: "POST" });
  } finally {
    setBusy(button, false);
    state.token = null;
    state.user = null;
    showLogin();
  }
});

$("refresh").addEventListener("click", async () => {
  const button = $("refresh");
  setBusy(button, true);
  try {
    await loadMaterials();
  } finally {
    setBusy(button, false);
  }
});

$("upload-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const button = $("upload");
  const status = $("upload-status");
  const file = $("file").files[0];
  if (!file) {
    setStatus(status, "请选择 Markdown 或 TXT 文件", "error");
    return;
  }
  const form = new FormData();
  form.append("title", $("title").value);
  form.append("file", file);
  setBusy(button, true);
  setStatus(status, "正在上传并建立索引…");
  try {
    await request("/api/v1/materials", { method: "POST", body: form });
    $("upload-form").reset();
    setStatus(status, "上传成功");
    await loadMaterials();
  } catch (error) {
    setStatus(status, error.message, "error");
  } finally {
    setBusy(button, false);
  }
});

$("search-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const button = $("search");
  const target = $("search-results");
  const status = $("search-status");
  target.replaceChildren();
  setBusy(button, true);
  setStatus(status, "正在检索本班资料…");
  try {
    const data = await request(`/api/v1/search?q=${encodeURIComponent($("query").value)}`);
    for (const item of data.items) {
      const article = document.createElement("article");
      article.className = "citation";
      const heading = document.createElement("strong");
      heading.textContent = `${item.title} · 第 ${item.start_line}-${item.end_line} 行`;
      const text = document.createElement("p");
      text.textContent = item.snippet;
      article.append(heading, text);
      target.append(article);
    }
    if (!data.items.length) setStatus(status, "资料中未找到相关内容", "empty");
    else setStatus(status, "");
  } catch (error) {
    setStatus(status, error.message, "error");
  } finally {
    setBusy(button, false);
  }
});

$("ask-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const button = $("ask");
  const target = $("answer");
  setBusy(button, true);
  target.textContent = "正在检索本班资料…";
  try {
    const data = await request("/api/v1/ask", {
      method: "POST",
      body: { question: $("question").value },
    });
    target.replaceChildren();
    const answer = document.createElement("p");
    answer.textContent = data.answer;
    target.append(answer);
    if (data.degraded) {
      const notice = document.createElement("p");
      notice.className = "muted";
      notice.textContent = "当前未配置模型，以下内容由本班资料摘录生成。";
      target.append(notice);
    }
    for (const [index, item] of data.citations.entries()) {
      const citation = document.createElement("div");
      citation.className = "citation";
      citation.textContent = `[${index + 1}] ${item.title}，第 ${item.start_line}-${item.end_line} 行：${item.snippet}`;
      target.append(citation);
    }
  } catch (error) {
    target.textContent = error.message;
  } finally {
    setBusy(button, false);
  }
});

showLogin();
