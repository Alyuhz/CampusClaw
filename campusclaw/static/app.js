const state = { token: null, user: null };

const $ = (id) => document.getElementById(id);

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
  const data = await request("/api/v1/materials");
  const list = $("materials");
  list.replaceChildren();
  for (const item of data.items) {
    const li = document.createElement("li");
    li.textContent = `${item.title}（${item.created_at}）`;
    list.append(li);
  }
  if (!data.items.length) list.textContent = "本班暂无资料";
}

$("login").addEventListener("click", async () => {
  $("auth-status").textContent = "正在登录…";
  try {
    const data = await request("/api/v1/auth/login", {
      method: "POST",
      body: { username: $("username").value, password: $("password").value },
    });
    state.token = data.token;
    state.user = data.user;
    $("auth-status").textContent = "";
    showWorkspace();
    await loadMaterials();
  } catch (error) {
    $("auth-status").textContent = error.message;
  }
});

$("logout").addEventListener("click", async () => {
  try {
    await request("/api/v1/auth/logout", { method: "POST" });
  } finally {
    state.token = null;
    state.user = null;
    showLogin();
  }
});

$("refresh").addEventListener("click", () => loadMaterials().catch((error) => alert(error.message)));

$("upload-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const form = new FormData();
  form.append("title", $("title").value);
  form.append("file", $("file").files[0]);
  try {
    await request("/api/v1/materials", { method: "POST", body: form });
    $("upload-form").reset();
    await loadMaterials();
  } catch (error) {
    alert(error.message);
  }
});

$("search").addEventListener("click", async () => {
  const target = $("search-results");
  target.replaceChildren();
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
    if (!data.items.length) target.textContent = "资料中未找到相关内容";
  } catch (error) {
    target.textContent = error.message;
  }
});

$("ask").addEventListener("click", async () => {
  const target = $("answer");
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
  }
});

showLogin();
