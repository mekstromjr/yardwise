document.querySelectorAll("[data-map-remove-prompt]").forEach(dialog => {
  const openButton = document.querySelector("[data-map-remove-open]");
  const closeButton = dialog.querySelector("[data-map-remove-close]");
  if (!openButton || !closeButton) return;

  function closePrompt() {
    if (typeof dialog.close === "function") dialog.close();
    else dialog.removeAttribute("open");
  }

  openButton.addEventListener("click", () => {
    if (typeof dialog.showModal === "function") dialog.showModal();
    else dialog.setAttribute("open", "");
  });
  closeButton.addEventListener("click", closePrompt);
  dialog.addEventListener("click", event => {
    if (event.target === dialog) closePrompt();
  });
});
