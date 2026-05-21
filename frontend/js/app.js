(function () {
  const API_BASE = "";
  const $ = (id) => document.getElementById(id);

  const messagesEl = $("messages");
  const intakeForm = $("intakeForm");
  const chatForm = $("chatForm");
  const chatInput = $("chatInput");
  const modeBadge = $("modeBadge");

  let conversation = [];

  function escapeHTML(s) {
    return (s || "").replace(/[&<>"']/g, (c) => ({
      "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;"
    }[c]));
  }

  function renderReply(data) {
    const md = (data && data.reply) || "";
    const html = window.DOMPurify.sanitize(window.marked.parse(md));
    return `<div class="doc">${html}</div>`;
  }

  function addMessage(role, html, opts = {}) {
    const div = document.createElement("div");
    div.className = `msg ${role}`;
    if (opts.raw) div.innerHTML = html;
    else div.textContent = html;
    messagesEl.appendChild(div);
    messagesEl.scrollTop = messagesEl.scrollHeight;
    return div;
  }

  function clearMessages() {
    messagesEl.innerHTML = "";
  }

  function readIntake() {
    return {
      symptoms: $("symptoms").value.trim(),
      age: $("age").value.trim(),
      gender: $("gender").value,
      history: $("history").value.trim(),
      language: $("language").value,
      reportText: $("reportText").value.trim()
    };
  }

  async function postJSON(path, body) {
    const res = await fetch(`${API_BASE}${path}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body)
    });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) throw new Error(data.error || `Request failed (${res.status})`);
    return data;
  }

  async function checkHealth() {
    try {
      const res = await fetch(`${API_BASE}/api/health`);
      const data = await res.json();
      if (data.mode === "live") {
        modeBadge.textContent = `Live AI`;
        modeBadge.className = "mode-badge live";
      } else {
        modeBadge.textContent = "Demo mode";
        modeBadge.className = "mode-badge";
      }
    } catch {
      modeBadge.textContent = "Offline";
      modeBadge.className = "mode-badge error";
    }
  }

  function thinkingMarkup() {
    return `<div class="thinking"><span class="dot"></span><span class="dot"></span><span class="dot"></span> Analyzing…</div>`;
  }

  async function runAnalyze(displayText) {
    addMessage("user", displayText);
    const thinking = addMessage("assistant", thinkingMarkup(), { raw: true });
    try {
      const data = await postJSON("/api/analyze", readIntake());
      thinking.innerHTML = renderReply(data);
      conversation.push({ role: "user", content: displayText });
      conversation.push({ role: "assistant", content: data.reply });
    } catch (err) {
      thinking.innerHTML = `<div class="error-note">⚠️ ${escapeHTML(err.message)}</div>`;
    }
  }

  async function runChat(question) {
    addMessage("user", question);
    const thinking = addMessage("assistant", thinkingMarkup(), { raw: true });
    try {
      const data = await postJSON("/api/chat", {
        intake: readIntake(),
        question,
        history: conversation
      });
      thinking.innerHTML = renderReply(data);
      conversation.push({ role: "user", content: question });
      conversation.push({ role: "assistant", content: data.reply });
    } catch (err) {
      thinking.innerHTML = `<div class="error-note">⚠️ ${escapeHTML(err.message)}</div>`;
    }
  }

  intakeForm.addEventListener("submit", (e) => {
    e.preventDefault();
    const intake = readIntake();
    if (!intake.symptoms && !intake.reportText) {
      alert("Please describe your symptoms or paste a medical report.");
      return;
    }
    const display = intake.symptoms
      ? `Please analyze:\n${intake.symptoms}`
      : `Please explain this report:\n${intake.reportText}`;
    runAnalyze(display);
  });

  $("clearBtn").addEventListener("click", () => {
    intakeForm.reset();
    conversation = [];
    clearMessages();
  });

  chatForm.addEventListener("submit", (e) => {
    e.preventDefault();
    const q = chatInput.value.trim();
    if (!q) return;
    chatInput.value = "";
    runChat(q);
  });

  checkHealth();
})();
