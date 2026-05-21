(function () {
  const modeBadge = document.getElementById("modeBadge");
  if (!modeBadge) return;
  fetch("/api/health")
    .then((r) => r.json())
    .then((data) => {
      if (data.mode === "live") {
        modeBadge.textContent = "Live AI";
        modeBadge.className = "mode-badge live";
      } else {
        modeBadge.textContent = "Demo mode";
        modeBadge.className = "mode-badge";
      }
    })
    .catch(() => {
      modeBadge.textContent = "Offline";
      modeBadge.className = "mode-badge error";
    });
})();
