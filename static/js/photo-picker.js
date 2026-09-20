/* Drag-and-drop enhancement for optional photo inputs. The input remains a
   normal file picker, so iPhone and iPad can use their native Photos sheet. */

document.querySelectorAll("[data-photo-picker]").forEach(picker => {
  const input = picker.querySelector("input[type='file']");
  const dropZone = picker.querySelector("[data-photo-drop]");
  const preview = picker.querySelector("[data-photo-preview]");
  const icon = picker.querySelector("[data-photo-icon]");
  const title = picker.querySelector("[data-photo-title]");
  const message = picker.querySelector("[data-photo-message]");
  const removeButton = picker.querySelector("[data-photo-remove]");
  let previewUrl = null;

  const emptyTitle = title.textContent;
  const emptyMessage = message.textContent;
  const readyMessage = picker.dataset.photoReadyMessage ||
    "Photo ready - save when you are finished.";

  function showSelected(files) {
    const selected = Array.from(files || []);
    const file = selected[0];
    if (!file) return;
    if (previewUrl) URL.revokeObjectURL(previewUrl);
    previewUrl = URL.createObjectURL(file);
    preview.src = previewUrl;
    preview.hidden = false;
    icon.hidden = true;
    title.textContent = selected.length > 1
      ? `${selected.length} photos selected`
      : (file.name || "Photo selected");
    message.textContent = selected.length > 1
      ? `${selected.length} photos ready - save when you are finished.`
      : readyMessage;
    removeButton.hidden = false;
  }

  function clearSelected() {
    input.value = "";
    if (previewUrl) URL.revokeObjectURL(previewUrl);
    previewUrl = null;
    preview.removeAttribute("src");
    preview.hidden = true;
    icon.hidden = false;
    title.textContent = emptyTitle;
    message.textContent = emptyMessage;
    removeButton.hidden = true;
  }

  preview.addEventListener("error", () => {
    preview.hidden = true;
    icon.hidden = false;
    message.textContent = "Photo selected. A preview is not available for this format.";
  });

  input.addEventListener("change", () => showSelected(input.files));
  removeButton.addEventListener("click", clearSelected);

  const form = picker.closest("form");
  form.addEventListener("submit", () => {
    const submitButton = form.querySelector("button[type='submit']");
    submitButton.disabled = true;
    submitButton.textContent = submitButton.dataset.savingLabel || "Saving...";
    form.setAttribute("aria-busy", "true");
  });

  ["dragenter", "dragover"].forEach(eventName => {
    dropZone.addEventListener(eventName, event => {
      event.preventDefault();
      dropZone.classList.add("dragging");
    });
  });

  ["dragleave", "drop"].forEach(eventName => {
    dropZone.addEventListener(eventName, event => {
      event.preventDefault();
      dropZone.classList.remove("dragging");
    });
  });

  dropZone.addEventListener("drop", event => {
    const photos = Array.from(event.dataTransfer.files).filter(item =>
      item.type.startsWith("image/") || /\.(heic|heif)$/i.test(item.name)
    );
    if (!photos.length) {
      message.textContent = "That item is not a photo. Choose an image from Photos or files.";
      return;
    }
    try {
      const transfer = new DataTransfer();
      const accepted = input.multiple ? photos : photos.slice(0, 1);
      accepted.forEach(file => transfer.items.add(file));
      input.files = transfer.files;
      showSelected(input.files);
    } catch (error) {
      message.textContent =
        "This browser cannot receive that dragged photo. Tap the chooser instead.";
    }
  });

  window.addEventListener("beforeunload", () => {
    if (previewUrl) URL.revokeObjectURL(previewUrl);
  });
});
