// Frontend controller — communicates only with the backend API.
(function () {
  const $ = (id) => document.getElementById(id);
  const messagesEl = $("messages");
  const modeBadge = $("modeBadge");
  const intakeForm = $("intakeForm");
  const chatForm = $("chatForm");
  const chatInput = $("chatInput");

  // Configure the backend URL. When the frontend is served BY the backend
  // (same origin), this stays empty. Otherwise set it to e.g. "http://127.0.0.1:5000".
  const API_BASE = window.API_BASE || "";

  let conversation = []; // {role: 'user'|'assistant', content: string}

  function escapeHTML(s) {
    return String(s).replace(/[&<>"']/g, (c) => ({
      "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;"
    }[c]));
  }

  // Render server reply, respecting the format flag ("markdown" or "html").
  function renderReply(data) {
    const raw = data.reply || "";
    let body = "";
    if (data.format === "markdown" && window.marked) {
      window.marked.setOptions({ gfm: true, breaks: true });
      body = window.marked.parse(raw);
    } else {
      body = raw; // already HTML (fallback responses)
    }
    if (window.DOMPurify) body = window.DOMPurify.sanitize(body);
    let prefix = "";
    if (data.error_note) {
      prefix = `<div class="error-note">⚠️ AI service issue: ${escapeHTML(data.error_note)}<br><span>Showing safe fallback response below.</span></div>`;
    }
    return `<div class="doc">${prefix}${body}</div>`;
  }

  function addMessage(role, html, { raw = false } = {}) {
    const wrap = document.createElement("div");
    wrap.className = `message ${role}`;
    const bubble = document.createElement("div");
    bubble.className = "bubble";
    bubble.innerHTML = raw ? html : `<p>${escapeHTML(html).replace(/\n/g, "<br>")}</p>`;
    wrap.appendChild(bubble);
    messagesEl.appendChild(wrap);
    messagesEl.scrollTop = messagesEl.scrollHeight;
    return bubble;
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
        modeBadge.textContent = `Live AI (${data.model || ""})`;
        modeBadge.className = "mode-badge live";
      } else {
        modeBadge.textContent = "Demo mode";
        modeBadge.className = "mode-badge";
      }
    } catch {
      modeBadge.textContent = "Backend offline";
      modeBadge.className = "mode-badge error";
    }
  }

  function thinkingMarkup() {
    return `<div class="thinking"><span class="dot"></span><span class="dot"></span><span class="dot"></span> Analyzing…</div>`;
  }

  async function runAnalyze(displayText) {
    clearMessages();
    addMessage("user", displayText);
    const thinking = addMessage("assistant", thinkingMarkup(), { raw: true });
    try {
      const data = await postJSON("/api/analyze", readIntake());
      thinking.innerHTML = renderReply(data);
      conversation = [
        { role: "user", content: displayText },
        { role: "assistant", content: data.reply }
      ];
    } catch (err) {
      thinking.innerHTML = `<div class="error-note">⚠️ ${escapeHTML(err.message)}</div>`;
    }
  }

  async function runChat(question) {
    clearMessages();
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

  // --- Report PDF upload modal ---
  const reportModal = $("reportModal");
  const reportForm = $("reportForm");
  const reportFile = $("reportFile");
  const reportFileName = $("reportFileName");
  const reportSubmit = $("reportSubmit");
  const reportResult = $("reportResult");
  const reportDropzone = $("reportDropzone");
  const reportLanguage = $("reportLanguage");

  function openReportModal() {
    reportLanguage.value = $("language").value || "English";
    reportModal.hidden = false;
    reportModal.setAttribute("aria-hidden", "false");
    document.body.style.overflow = "hidden";
  }

  function closeReportModal() {
    reportModal.hidden = true;
    reportModal.setAttribute("aria-hidden", "true");
    document.body.style.overflow = "";
    reportForm.reset();
    reportFileName.hidden = true;
    reportFileName.textContent = "";
    reportSubmit.disabled = true;
    reportResult.hidden = true;
    reportResult.innerHTML = "";
  }

  $("openReportModal").addEventListener("click", openReportModal);
  reportModal.querySelectorAll("[data-close-modal]").forEach((el) => {
    el.addEventListener("click", closeReportModal);
  });
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape" && !reportModal.hidden) closeReportModal();
  });

  function setReportFile(file) {
    if (!file) {
      reportFileName.hidden = true;
      reportFileName.textContent = "";
      reportSubmit.disabled = true;
      return;
    }
    if (!/\.pdf$/i.test(file.name)) {
      reportFileName.hidden = false;
      reportFileName.textContent = "⚠️ Please choose a PDF file.";
      reportSubmit.disabled = true;
      return;
    }
    const kb = (file.size / 1024).toFixed(0);
    reportFileName.hidden = false;
    reportFileName.textContent = `📄 ${file.name} (${kb} KB)`;
    reportSubmit.disabled = false;
  }

  reportFile.addEventListener("change", () => setReportFile(reportFile.files[0]));

  ["dragenter", "dragover"].forEach((evt) =>
    reportDropzone.addEventListener(evt, (e) => {
      e.preventDefault();
      reportDropzone.classList.add("is-drag");
    })
  );
  ["dragleave", "drop"].forEach((evt) =>
    reportDropzone.addEventListener(evt, (e) => {
      e.preventDefault();
      reportDropzone.classList.remove("is-drag");
    })
  );
  reportDropzone.addEventListener("drop", (e) => {
    const file = e.dataTransfer && e.dataTransfer.files && e.dataTransfer.files[0];
    if (file) {
      const dt = new DataTransfer();
      dt.items.add(file);
      reportFile.files = dt.files;
      setReportFile(file);
    }
  });

  reportForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    const file = reportFile.files[0];
    if (!file) return;
    reportSubmit.disabled = true;
    reportResult.hidden = false;
    reportResult.innerHTML = `<div class="doc">${thinkingMarkup().replace("Analyzing", "Reading & analyzing your report")}</div>`;

    const fd = new FormData();
    fd.append("report", file);
    fd.append("language", reportLanguage.value || "English");
    try {
      const res = await fetch(`${API_BASE}/api/analyze-report`, { method: "POST", body: fd });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error(data.error || `Request failed (${res.status})`);
      let banner = "";
      if (data.source === "vision") {
        banner = `<div class="info-note">🔍 No text layer detected — read directly from the page images using AI vision.</div>`;
      }
      reportResult.innerHTML = banner + renderReply(data);
    } catch (err) {
      reportResult.innerHTML = `<div class="error-note">⚠️ ${escapeHTML(err.message)}</div>`;
    } finally {
      reportSubmit.disabled = false;
    }
  });

  checkHealth();
})();
