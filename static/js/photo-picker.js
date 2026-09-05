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

  function showSelected(file) {
    if (!file) return;
    if (previewUrl) URL.revokeObjectURL(previewUrl);
    previewUrl = URL.createObjectURL(file);
    preview.src = previewUrl;
    preview.hidden = false;
    icon.hidden = true;
    title.textContent = file.name || "Photo selected";
    message.textContent = "Photo ready - save the plant when you are finished.";
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

  input.addEventListener("change", () => showSelected(input.files[0]));
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
    const file = Array.from(event.dataTransfer.files).find(item =>
      item.type.startsWith("image/") || /\.(heic|heif)$/i.test(item.name)
    );
    if (!file) {
      message.textContent = "That item is not a photo. Choose an image from Photos or files.";
      return;
    }
    try {
      const transfer = new DataTransfer();
      transfer.items.add(file);
      input.files = transfer.files;
      showSelected(file);
    } catch (error) {
      message.textContent =
        "This browser cannot receive that dragged photo. Tap the chooser instead.";
    }
  });

  window.addEventListener("beforeunload", () => {
    if (previewUrl) URL.revokeObjectURL(previewUrl);
  });
});
