document.querySelectorAll("[data-location-prompt]").forEach(dialog => {
  const openButton = document.querySelector("[data-location-prompt-open]");
  const closeButton = dialog.querySelector("[data-location-prompt-close]");
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
