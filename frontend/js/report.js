(function () {
  const API_BASE = "";
  const $ = (id) => document.getElementById(id);

  const modeBadge = $("modeBadge");
  const reportForm = $("reportForm");
  const reportFile = $("reportFile");
  const reportFileName = $("reportFileName");
  const reportSubmit = $("reportSubmit");
  const reportResult = $("reportResult");
  const reportDropzone = $("reportDropzone");
  const reportLanguage = $("reportLanguage");

  function escapeHTML(s) {
    return (s || "").replace(/[&<>"']/g, (c) => ({
      "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;"
    }[c]));
  }

  function renderReply(data) {
    const md = (data && data.reply) || "";
    const html = window.DOMPurify.sanitize(window.marked.parse(md));
    return `<div class="msg assistant" style="max-width:100%;">${html}</div>`;
  }

  function thinkingMarkup() {
    return `<div class="thinking"><span class="dot"></span><span class="dot"></span><span class="dot"></span> Reading & analyzing your report…</div>`;
  }

  async function checkHealth() {
    try {
      const res = await fetch(`${API_BASE}/api/health`);
      const data = await res.json();
      if (data.mode === "live") {
        modeBadge.textContent = "Live AI";
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
    reportResult.innerHTML = thinkingMarkup();

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
