/* YardWise property map. Hand-written on purpose (no build step).
   Coordinate space: CRS.Simple map units; y grows downward like image pixels,
   so every Leaflet latlng is [-y, x] and we convert at the edges. */
/* global L */

function yardwiseMap(opts) {
  const el = document.getElementById("map");
  if (!el) return;
  const map = L.map(el, {
    crs: L.CRS.Simple, minZoom: -3, maxZoom: 5, zoomSnap: 0.5,
    scrollWheelZoom: true, attributionControl: false,
  });
  const state = { data: null, mode: "view", traceBedId: null, tracePts: [],
                  placePlantId: null, markers: {}, bedShapes: {}, traceLayer: null,
                  traceHandles: [], selectionLayer: null, selectionStart: null,
                  selectionMoved: false,
                  suggestedName: "", plantLayer: L.layerGroup() };
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

  function setStatus(msg) {
    const status = document.getElementById("map-status");
    if (status) status.textContent = msg;
  }

  function plantTooltip(name) {
    const content = document.createElement("span");
    content.textContent = name;
    return content;
  }

  function sidebarItem(locationId) {
    return document.querySelector(`[data-plant-location="${locationId}"]`);
  }

  function highlightLocation(locationId, highlighted) {
    const marker = state.markers[locationId];
    const item = sidebarItem(locationId);
    if (item) item.classList.toggle("is-map-highlighted", highlighted);
    if (!marker) return;
    marker.setStyle(highlighted
      ? { radius: 11, weight: 4, fillColor: "#e47a4e" }
      : { radius: 7, weight: 2, fillColor: "#bc5f38" });
    if (highlighted) marker.openTooltip();
    else marker.closeTooltip();
  }

  function showSelectedPhoto(file) {
    if (!file) return;
    if (previewUrl) URL.revokeObjectURL(previewUrl);
    previewUrl = URL.createObjectURL(file);
    photoPreview.src = previewUrl;
    photoPreview.hidden = false;
    photoIcon.hidden = true;
    photoTitle.textContent = file.name || "Photo selected";
  }

  if (photoInput && photoDrop) {
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
  }

  function drawTrace() {
    if (state.traceLayer) state.traceLayer.remove();
    state.traceHandles.forEach(handle => handle.remove());
    state.traceHandles = [];
    state.traceLayer = null;
    if (!state.tracePts.length) return;
    const points = state.tracePts.map(p => toLL(p[0], p[1]));
    state.traceLayer = (state.tracePts.length >= 3
      ? L.polygon(points, { color: "#bc5f38", dashArray: "6 4", fillOpacity: 0.1 })
      : L.polyline(points, { color: "#bc5f38", dashArray: "6 4", weight: 3 })
    ).addTo(map);
    if (state.mode === "trace") {
      const icon = L.divIcon({ className: "bed-vertex-handle", iconSize: [18, 18] });
      state.tracePts.forEach((point, index) => {
        const handle = L.marker(toLL(point[0], point[1]), {
          draggable: true, icon, keyboard: true,
          title: `Move outline point ${index + 1}`,
        }).addTo(map);
        handle.on("drag", event => {
          const [x, y] = fromLL(event.target.getLatLng());
          state.tracePts[index] = [Math.round(x), Math.round(y)];
          state.traceLayer.setLatLngs(state.tracePts.map(p => toLL(p[0], p[1])));
        });
        state.traceHandles.push(handle);
      });
    }
  }

  function startTrace(bedId, initialPoints = [], suggestedName = "") {
    state.mode = "trace";
    state.traceBedId = bedId;
    state.tracePts = initialPoints;
    state.suggestedName = suggestedName;
    drawTrace();
    nameForm.hidden = true;
    nameError.hidden = true;
    traceActions.hidden = false;
    setStatus(bedId
      ? "Tap around the bed's edge to draw its new outline"
      : "Tap around the new bed's edge, then finish the outline");
  }

  function selectionBounds(start, end) {
    return [
      [Math.min(start[0], end[0]), Math.min(start[1], end[1])],
      [Math.max(start[0], end[0]), Math.max(start[1], end[1])],
    ];
  }

  function rectanglePoints(bounds) {
    const [[left, top], [right, bottom]] = bounds;
    return [[left, top], [right, top], [right, bottom], [left, bottom]];
  }

  async function requestBedSuggestion(bounds) {
    state.mode = "suggesting";
    map.dragging.enable();
    el.classList.remove("selecting-bed-region");
    setStatus("Studying the selected region for bed edges...");
    let result;
    try {
      result = await post("/map/beds/suggest/", { bounds });
    } catch (error) {
      result = { error: "The outline service did not answer." };
    }
    if (state.selectionLayer) state.selectionLayer.remove();
    state.selectionLayer = null;
    if (result.ok) {
      startTrace(null, result.boundary, result.suggested_name || "");
      setStatus(
        `Suggested ${result.suggested_name || "bed outline"} (${result.confidence} confidence). ` +
        "Drag the round points to adjust the edges, then finish the outline."
      );
      return;
    }
    startTrace(null, rectanglePoints(bounds));
    setStatus(`${result.error} Drag the round points to adjust the outline, then finish it.`);
  }

  function startRegionSelection() {
    cancelTrace();
    state.mode = "select-region";
    state.selectionStart = null;
    map.dragging.disable();
    el.classList.add("selecting-bed-region");
    setStatus("Drag over one garden-bed area, or tap two opposite corners, to select it.");
  }

  function cancelTrace() {
    state.mode = "view";
    state.traceBedId = null;
    state.tracePts = [];
    state.suggestedName = "";
    drawTrace();
    if (state.selectionLayer) state.selectionLayer.remove();
    state.selectionLayer = null;
    state.selectionStart = null;
    map.dragging.enable();
    el.classList.remove("selecting-bed-region");
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
      if (layer.render_w && layer.render_h) {
        lb = [toLL(layer.x, layer.y + layer.render_h),
              toLL(layer.x + layer.render_w, layer.y)];
      } else if (layer.w && layer.h) {
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
      const selected = String(opts.focusBed || "") === String(bed.id);
      const poly = L.polygon(bed.boundary.map(p => toLL(p[0], p[1])), {
        color: selected ? "#bc5f38" : "#3d5c40",
        weight: selected ? 4 : 2,
        fillColor: selected ? "#bc5f38" : "#7d9770",
        fillOpacity: selected ? 0.22 : (opts.focusBed ? 0.05 : 0.18),
        opacity: opts.focusBed && !selected ? 0.35 : 1,
      }).addTo(map).bindTooltip(plantTooltip(bed.name), { sticky: true });
      poly.on("click", () => {
        if (state.mode !== "view") return;
        window.location.href = bed.url;
      });
      state.bedShapes[bed.id] = poly;
    });
    // plant points
    data.points.forEach(pt => {
      if (opts.focusBed && String(pt.bed_id || "") !== String(opts.focusBed)) return;
      const m = L.circleMarker(toLL(pt.x, pt.y), {
        radius: 7, color: "#fffdf6", weight: 2, fillColor: "#bc5f38", fillOpacity: 0.95,
      }).addTo(state.plantLayer).bindTooltip(plantTooltip(pt.name), {
        direction: "top", offset: [0, -8], className: "plant-map-tooltip",
      });
      m.on("mouseover", () => highlightLocation(pt.loc_id, true));
      m.on("mouseout", () => highlightLocation(pt.loc_id, false));
      m.on("click", event => {
        if (event.originalEvent) L.DomEvent.stopPropagation(event.originalEvent);
        window.location.href = pt.url;
      });
      state.markers[pt.loc_id] = m;
    });
    map.fitBounds(bounds);

    // Keep the normal property view quiet. Fine-grained plant markers appear
    // only after zooming in or entering a selected-bed/plant context.
    function updateProgressiveLayers() {
      const revealPlants = map.getZoom() >= 0 || opts.focusPlant || opts.focusBed;
      if (revealPlants && !map.hasLayer(state.plantLayer)) state.plantLayer.addTo(map);
      if (!revealPlants && map.hasLayer(state.plantLayer)) state.plantLayer.removeFrom(map);
    }
    map.on("zoomend", updateProgressiveLayers);
    updateProgressiveLayers();

    // focus requested from a profile page ("Show on map")
    const focusedPlantPoint = data.points.find(
      point => String(point.plant_id) === String(opts.focusPlant || "")
    );
    if (focusedPlantPoint && state.markers[focusedPlantPoint.loc_id]) {
      state.plantLayer.addTo(map);
      const m = state.markers[focusedPlantPoint.loc_id];
      map.setView(m.getLatLng(), 1);
      m.openTooltip();
    } else if (opts.focusBed && state.bedShapes[opts.focusBed]) {
      const shape = state.bedShapes[opts.focusBed];
      map.fitBounds(shape.getBounds().pad(opts.bedPage ? 0.18 : 0.4));
    }

    document.querySelectorAll("[data-plant-location]").forEach(item => {
      const locationId = item.dataset.plantLocation;
      if (!state.markers[locationId]) return;
      item.addEventListener("mouseenter", () => highlightLocation(locationId, true));
      item.addEventListener("mouseleave", () => highlightLocation(locationId, false));
      item.addEventListener("focus", () => highlightLocation(locationId, true));
      item.addEventListener("blur", () => highlightLocation(locationId, false));
    });
  }

  map.on("click", async (e) => {
    const [x, y] = fromLL(e.latlng);
    if (state.mode === "select-region") {
      const point = [Math.round(x), Math.round(y)];
      if (!state.selectionStart) {
        state.selectionStart = point;
        setStatus("Now tap the opposite corner of the garden-bed region.");
        return;
      }
      const bounds = selectionBounds(state.selectionStart, point);
      if (bounds[1][0] - bounds[0][0] < 10 || bounds[1][1] - bounds[0][1] < 10) {
        setStatus("Choose an opposite corner to make the selected region larger.");
        return;
      }
      requestBedSuggestion(bounds);
    } else if (state.mode === "trace") {
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

  map.on("mousedown", e => {
    if (state.mode !== "select-region" || state.selectionStart) return;
    state.selectionStart = fromLL(e.latlng).map(Math.round);
    state.selectionMoved = false;
  });
  map.on("mousemove", e => {
    if (state.mode !== "select-region" || !state.selectionStart) return;
    const current = fromLL(e.latlng).map(Math.round);
    const bounds = selectionBounds(state.selectionStart, current);
    state.selectionMoved = (
      bounds[1][0] - bounds[0][0] >= 10 && bounds[1][1] - bounds[0][1] >= 10
    );
    if (state.selectionLayer) state.selectionLayer.remove();
    state.selectionLayer = L.rectangle(
      [toLL(bounds[0][0], bounds[1][1]), toLL(bounds[1][0], bounds[0][1])],
      { color: "#bc5f38", weight: 2, dashArray: "6 4", fillOpacity: 0.12 }
    ).addTo(map);
  });
  map.on("mouseup", e => {
    if (state.mode !== "select-region" || !state.selectionStart || !state.selectionMoved) return;
    const bounds = selectionBounds(state.selectionStart, fromLL(e.latlng).map(Math.round));
    requestBedSuggestion(bounds);
  });

  if (opts.editor) {
    document.getElementById("trace-new-start").addEventListener("click", startRegionSelection);
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
        nameInput.value = state.suggestedName;
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
      setTimeout(() => { window.location.href = res.bed.url; }, 600);
    });
    document.getElementById("place-start").addEventListener("click", () => {
      const sel = document.getElementById("place-plant");
      if (!sel.value) { setStatus("Pick the plant to place first"); return; }
      state.mode = "place"; state.placePlantId = sel.value;
      setStatus("Tap the plant's spot on the map");
    });
  }

  fetch(opts.dataUrl || "/map/data.json").then(r => r.json()).then(render);
}
