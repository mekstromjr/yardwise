/* YardWise property map. Hand-written on purpose (no build step).
   Coordinate space: CRS.Simple map units; y grows downward like image pixels,
   so every Leaflet latlng is [-y, x] and we convert at the edges. */
/* global L */

function yardwiseMap(opts) {
  const el = document.getElementById("map");
  const map = L.map(el, { crs: L.CRS.Simple, minZoom: -3, attributionControl: false });
  const state = { data: null, mode: "view", traceBedId: null, tracePts: [],
                  placePlantId: null, markers: {}, bedShapes: {}, traceLayer: null };
  const traceActions = document.getElementById("trace-actions");
  const nameForm = document.getElementById("new-bed-name-form");
  const nameInput = document.getElementById("new-bed-name");
  const nameError = document.getElementById("new-bed-error");
  const photoDrop = document.getElementById("map-photo-drop");
  const photoInput = document.getElementById("map-photo-input");
  const photoPreview = document.getElementById("map-photo-preview");
  const photoIcon = document.getElementById("map-photo-icon");
  const photoTitle = document.getElementById("map-photo-title");
  let previewUrl = null;

  const toLL = (x, y) => [-y, x];
  const fromLL = (ll) => [ll.lng, -ll.lat];

  function csrf() {
    return document.cookie.split("; ").find(r => r.startsWith("csrftoken="))?.split("=")[1] || "";
  }
  async function post(url, body) {
    const r = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json", "X-CSRFToken": csrf() },
      body: JSON.stringify(body),
    });
    return r.json();
  }

  function setStatus(msg) { document.getElementById("map-status").textContent = msg; }

  function showSelectedPhoto(file) {
    if (!file) return;
    if (previewUrl) URL.revokeObjectURL(previewUrl);
    previewUrl = URL.createObjectURL(file);
    photoPreview.src = previewUrl;
    photoPreview.hidden = false;
    photoIcon.hidden = true;
    photoTitle.textContent = file.name || "Photo selected";
  }

  photoInput.addEventListener("change", () => showSelectedPhoto(photoInput.files[0]));
  ["dragenter", "dragover"].forEach(eventName => {
    photoDrop.addEventListener(eventName, event => {
      event.preventDefault();
      photoDrop.classList.add("dragging");
    });
  });
  ["dragleave", "drop"].forEach(eventName => {
    photoDrop.addEventListener(eventName, event => {
      event.preventDefault();
      photoDrop.classList.remove("dragging");
    });
  });
  photoDrop.addEventListener("drop", event => {
    const file = Array.from(event.dataTransfer.files).find(item =>
      item.type.startsWith("image/") || /\.(heic|heif)$/i.test(item.name)
    );
    if (!file) {
      setStatus("That item is not a photo. Choose an image from Photos or files.");
      return;
    }
    try {
      const transfer = new DataTransfer();
      transfer.items.add(file);
      photoInput.files = transfer.files;
      showSelectedPhoto(file);
      setStatus("Photo ready - add a name if you like, then use this photo.");
    } catch (error) {
      setStatus("This browser cannot receive that dragged photo. Tap the chooser instead.");
    }
  });

  function drawTrace() {
    if (state.traceLayer) state.traceLayer.remove();
    state.traceLayer = null;
    if (!state.tracePts.length) return;
    const points = state.tracePts.map(p => toLL(p[0], p[1]));
    state.traceLayer = (state.tracePts.length >= 3
      ? L.polygon(points, { color: "#bc5f38", dashArray: "6 4", fillOpacity: 0.1 })
      : L.polyline(points, { color: "#bc5f38", dashArray: "6 4", weight: 3 })
    ).addTo(map);
  }

  function startTrace(bedId) {
    state.mode = "trace";
    state.traceBedId = bedId;
    state.tracePts = [];
    drawTrace();
    nameForm.hidden = true;
    nameError.hidden = true;
    traceActions.hidden = false;
    setStatus(bedId
      ? "Tap around the bed's edge to draw its new outline"
      : "Tap around the new bed's edge, then finish the outline");
  }

  function cancelTrace() {
    state.mode = "view";
    state.traceBedId = null;
    state.tracePts = [];
    drawTrace();
    traceActions.hidden = true;
    nameForm.hidden = true;
    nameError.hidden = true;
    nameInput.value = "";
    setStatus("Tap a bed or marker to identify it.");
  }

  function render(data) {
    state.data = data;
    const bounds = [toLL(0, data.height), toLL(data.width, 0)];
    map.setMaxBounds(L.latLngBounds(bounds).pad(0.2));

    // reference imagery - fit into the space preserving each image's natural
    // aspect ratio (centered letterbox), never stretch
    data.layers.forEach(layer => {
      if (!layer.visible) return;
      let lb = bounds;
      if (layer.w && layer.h) {
        const scale = Math.min(data.width / layer.w, data.height / layer.h);
        const w = layer.w * scale, h = layer.h * scale;
        const x0 = (data.width - w) / 2, y0 = (data.height - h) / 2;
        lb = [toLL(x0, y0 + h), toLL(x0 + w, y0)];
      }
      L.imageOverlay(layer.url, lb, { opacity: layer.opacity }).addTo(map);
    });
    // grid overlay
    if (data.grid.visible) {
      const g = L.layerGroup().addTo(map);
      for (let c = 1; c < data.grid.cols; c++) {
        const x = (data.width / data.grid.cols) * c;
        L.polyline([toLL(x, 0), toLL(x, data.height)],
                   { color: "#2b3a2c", weight: 1, opacity: 0.15 }).addTo(g);
      }
      for (let r = 1; r < data.grid.rows; r++) {
        const y = (data.height / data.grid.rows) * r;
        L.polyline([toLL(0, y), toLL(data.width, y)],
                   { color: "#2b3a2c", weight: 1, opacity: 0.15 }).addTo(g);
      }
    }
    // beds
    data.beds.forEach(bed => {
      if (!bed.boundary) return;
      const poly = L.polygon(bed.boundary.map(p => toLL(p[0], p[1])), {
        color: "#3d5c40", weight: 2, fillColor: "#7d9770", fillOpacity: 0.18,
      }).addTo(map).bindTooltip(bed.name, { sticky: true });
      poly.on("click", () => {
        if (state.mode !== "view") return;
        window.location.search = "?bed=" + bed.id;
      });
      state.bedShapes[bed.id] = poly;
    });
    // plant points
    data.points.forEach(pt => {
      const m = L.circleMarker(toLL(pt.x, pt.y), {
        radius: 7, color: "#fffdf6", weight: 2, fillColor: "#bc5f38", fillOpacity: 0.95,
      }).addTo(map).bindPopup(
        `<strong>${pt.name}</strong><br>${pt.bed || "no bed"} · ${pt.cell}` +
        `<br><a href="${pt.url}">Open plant</a>`);
      state.markers[pt.plant_id] = m;
    });
    map.fitBounds(bounds);

    // focus requested from a profile page ("Show on map")
    if (opts.focusPlant && state.markers[opts.focusPlant]) {
      const m = state.markers[opts.focusPlant];
      map.setView(m.getLatLng(), 1);
      m.openPopup();
    } else if (opts.focusBed && state.bedShapes[opts.focusBed]) {
      const shape = state.bedShapes[opts.focusBed];
      map.fitBounds(shape.getBounds().pad(0.4));
      shape.setStyle({ color: "#bc5f38", weight: 3 });
    }
  }

  map.on("click", async (e) => {
    const [x, y] = fromLL(e.latlng);
    if (state.mode === "trace") {
      state.tracePts.push([Math.round(x), Math.round(y)]);
      drawTrace();
      setStatus(`Outlining: ${state.tracePts.length} point${state.tracePts.length === 1 ? "" : "s"} - tap "Finish outline" when done`);
    } else if (state.mode === "place") {
      const res = await post(`/map/plant/${state.placePlantId}/point/`, {
        x: Math.round(x), y: Math.round(y),
      });
      setStatus(res.ok ? `Placed in ${res.bed || "open ground"} (${res.cell}). Reloading...`
                       : "Could not place");
      if (res.ok) setTimeout(() => window.location.reload(), 600);
    }
  });

  document.getElementById("trace-new-start").addEventListener("click", () => startTrace(null));
  document.getElementById("trace-existing-start").addEventListener("click", () => {
    const sel = document.getElementById("trace-bed");
    if (!sel.value) { setStatus("Pick the existing bed you want to adjust"); return; }
    startTrace(sel.value);
  });
  document.getElementById("trace-finish").addEventListener("click", async () => {
    if (state.mode !== "trace" || state.tracePts.length < 3) {
      setStatus("Need at least 3 points"); return;
    }
    if (!state.traceBedId) {
      state.mode = "name-bed";
      traceActions.hidden = true;
      nameForm.hidden = false;
      setStatus("Outline ready - give this garden bed a name");
      nameInput.focus();
      return;
    }
    const res = await post(`/map/bed/${state.traceBedId}/boundary/`,
                           { boundary: state.tracePts });
    setStatus(res.ok ? `Saved (cells ${res.cells.join(", ")}). Reloading...` : res.error);
    if (res.ok) setTimeout(() => window.location.reload(), 600);
  });
  document.getElementById("trace-undo").addEventListener("click", () => {
    if (state.mode !== "trace" || !state.tracePts.length) return;
    state.tracePts.pop();
    drawTrace();
    setStatus(state.tracePts.length
      ? `Outlining: ${state.tracePts.length} point${state.tracePts.length === 1 ? "" : "s"}`
      : "Tap the first point on the bed's edge");
  });
  document.getElementById("trace-cancel").addEventListener("click", cancelTrace);
  document.getElementById("new-bed-cancel").addEventListener("click", cancelTrace);
  document.getElementById("new-bed-back").addEventListener("click", () => {
    state.mode = "trace";
    nameForm.hidden = true;
    traceActions.hidden = false;
    setStatus("Adjust the outline, then finish it again");
  });
  nameForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    const name = nameInput.value.trim();
    if (!name) {
      nameError.textContent = "Give the garden bed a name.";
      nameError.hidden = false;
      nameInput.focus();
      return;
    }
    const res = await post("/map/beds/create/", { name, boundary: state.tracePts });
    if (!res.ok) {
      nameError.textContent = res.error || "The bed could not be created.";
      nameError.hidden = false;
      return;
    }
    nameError.hidden = true;
    setStatus(`Created ${res.bed.name} (${res.bed.code}). Reloading...`);
    setTimeout(() => { window.location.search = `?bed=${res.bed.id}`; }, 600);
  });
  document.getElementById("place-start").addEventListener("click", () => {
    const sel = document.getElementById("place-plant");
    if (!sel.value) { setStatus("Pick the plant to place first"); return; }
    state.mode = "place"; state.placePlantId = sel.value;
    setStatus("Tap the plant's spot on the map");
  });

  fetch("/map/data.json").then(r => r.json()).then(render);
}
