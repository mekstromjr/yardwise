(() => {
  const dialog = document.querySelector("[data-photo-lightbox]");
  if (!dialog) return;

  const image = dialog.querySelector("[data-photo-lightbox-image]");
  const info = dialog.querySelector("[data-photo-lightbox-info]");
  const resetButton = dialog.querySelector("[data-photo-zoom-reset]");
  const stage = dialog.querySelector("[data-photo-stage]");
  let scale = 1;
  let offsetX = 0;
  let offsetY = 0;
  let dragStart = null;
  let openMenu = null;

  const renderTransform = () => {
    image.style.transform = `translate(${offsetX}px, ${offsetY}px) scale(${scale})`;
  };

  const setScale = (next) => {
    scale = Math.min(5, Math.max(1, next));
    if (scale === 1) {
      offsetX = 0;
      offsetY = 0;
    }
    renderTransform();
    resetButton.textContent = `${Math.round(scale * 100)}%`;
    stage.classList.toggle("is-zoomed", scale > 1);
  };

  const closeMenu = () => {
    if (openMenu) openMenu.hidden = true;
    openMenu = null;
  };

  const openPhoto = (button) => {
    const details = button.querySelector(".photo-hover-info");
    image.src = button.dataset.photoSrc;
    image.alt = button.dataset.photoAlt || "Plant photo";
    info.textContent = details ? details.innerText.trim() : image.alt;
    setScale(1);
    if (typeof dialog.showModal === "function") dialog.showModal();
    else dialog.setAttribute("open", "");
  };

  document.querySelectorAll("[data-photo-open]").forEach((button) => {
    button.addEventListener("click", () => openPhoto(button));
    button.addEventListener("contextmenu", (event) => {
      const menu = button.closest(".plant-photo-surface")?.querySelector("[data-photo-menu]");
      if (!menu) return;
      event.preventDefault();
      closeMenu();
      menu.hidden = false;
      menu.style.left = `${Math.min(event.clientX, window.innerWidth - 230)}px`;
      menu.style.top = `${Math.min(event.clientY, window.innerHeight - 100)}px`;
      openMenu = menu;
    });
  });

  dialog.querySelector("[data-photo-zoom-in]").addEventListener("click", () => setScale(scale + 0.5));
  dialog.querySelector("[data-photo-zoom-out]").addEventListener("click", () => setScale(scale - 0.5));
  resetButton.addEventListener("click", () => setScale(1));
  dialog.querySelector("[data-photo-close]").addEventListener("click", () => dialog.close());
  stage.addEventListener("dblclick", () => setScale(scale > 1 ? 1 : 2));
  stage.addEventListener("wheel", (event) => {
    event.preventDefault();
    setScale(scale + (event.deltaY < 0 ? 0.25 : -0.25));
  }, { passive: false });
  stage.addEventListener("pointerdown", (event) => {
    if (scale === 1) return;
    dragStart = { x: event.clientX - offsetX, y: event.clientY - offsetY };
    stage.setPointerCapture(event.pointerId);
    stage.classList.add("is-dragging");
  });
  stage.addEventListener("pointermove", (event) => {
    if (!dragStart) return;
    offsetX = event.clientX - dragStart.x;
    offsetY = event.clientY - dragStart.y;
    renderTransform();
  });
  const stopDragging = () => {
    dragStart = null;
    stage.classList.remove("is-dragging");
  };
  stage.addEventListener("pointerup", stopDragging);
  stage.addEventListener("pointercancel", stopDragging);
  dialog.addEventListener("click", (event) => {
    if (event.target === dialog) dialog.close();
  });
  dialog.addEventListener("close", () => {
    image.removeAttribute("src");
    setScale(1);
  });
  document.addEventListener("click", (event) => {
    if (openMenu && !openMenu.contains(event.target)) closeMenu();
  });
  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape") closeMenu();
  });
  window.addEventListener("scroll", closeMenu, true);
})();
