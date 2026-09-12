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
                  traceHandles: [], suggestedName: "", traceHistory: [], traceInitialPts: [],
                  mapLocked: false, suggestionRequest: 0, plantLayer: L.layerGroup() };
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
  async function post(url, body, timeoutMs = 0) {
    const controller = timeoutMs ? new AbortController() : null;
    const timer = controller ? setTimeout(() => controller.abort(), timeoutMs) : null;
    try {
      const r = await fetch(url, {
        method: "POST",
        headers: { "Content-Type": "application/json", "X-CSRFToken": csrf() },
        body: JSON.stringify(body),
        signal: controller?.signal,
      });
      return r.json();
    } finally {
      if (timer) clearTimeout(timer);
    }
  }

  function setStatus(msg) {
    const status = document.getElementById("map-status");
    if (status) status.textContent = msg;
  }

  function setMapLocked(locked) {
    const interactions = [
      "dragging", "touchZoom", "doubleClickZoom", "scrollWheelZoom", "boxZoom", "keyboard",
    ];
    interactions.forEach(name => {
      const handler = map[name];
      if (handler && typeof handler[locked ? "disable" : "enable"] === "function") {
        handler[locked ? "disable" : "enable"]();
      }
    });
    state.mapLocked = locked;
    el.classList.toggle("map-editing-locked", locked);
  }

  function copyPoints(points) {
    return points.map(point => [point[0], point[1]]);
  }

  function rememberTrace() {
    state.traceHistory.push(copyPoints(state.tracePts));
    updateOutlineActions();
  }

  function nearestTraceEdge(point) {
    let nearest = 0;
    let nearestPoint = point;
    let nearestDistance = Infinity;
    state.tracePts.forEach((start, index) => {
      const end = state.tracePts[(index + 1) % state.tracePts.length];
      const dx = end[0] - start[0];
      const dy = end[1] - start[1];
      const lengthSquared = dx * dx + dy * dy;
      const amount = lengthSquared
        ? Math.max(0, Math.min(1, ((point[0] - start[0]) * dx + (point[1] - start[1]) * dy) / lengthSquared))
        : 0;
      const x = start[0] + amount * dx;
      const y = start[1] + amount * dy;
      const distance = (point[0] - x) ** 2 + (point[1] - y) ** 2;
      if (distance < nearestDistance) {
        nearest = index;
        nearestPoint = [Math.round(x), Math.round(y)];
        nearestDistance = distance;
      }
    });
    return { index: nearest, point: nearestPoint };
  }

  function updateOutlineActions(busy = false) {
    const undo = document.getElementById("trace-undo");
    const restart = document.getElementById("trace-restart");
    const save = document.getElementById("trace-finish");
    const refine = document.getElementById("trace-refine-ai");
    const count = document.getElementById("trace-point-count");
    if (undo) undo.disabled = busy || !state.traceHistory.length;
    if (restart) restart.disabled = busy;
    if (save) save.disabled = busy || state.tracePts.length < 3;
    if (refine) refine.disabled = busy || state.tracePts.length < 3;
    if (count) {
      count.textContent = `${state.tracePts.length} point${state.tracePts.length === 1 ? "" : "s"}`;
    }
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
      ? L.polygon(points, { color: "#bc5f38", weight: 4, opacity: 1, fillOpacity: 0.18,
                            bubblingMouseEvents: false })
      : L.polyline(points, { color: "#bc5f38", weight: 4, opacity: 1,
                             bubblingMouseEvents: false })
    ).addTo(map);
    if (state.mode === "trace") {
      if (state.tracePts.length >= 2) {
        state.traceLayer.on("click", event => {
          if (event.originalEvent) L.DomEvent.stopPropagation(event.originalEvent);
          const point = fromLL(event.latlng).map(Math.round);
          const edge = nearestTraceEdge(point);
          rememberTrace();
          state.tracePts.splice(edge.index + 1, 0, edge.point);
          drawTrace();
          updateOutlineActions();
          setStatus("Added an outline point. Drag it to refine the bed edge, or undo.");
        });
      }
      state.tracePts.forEach((point, index) => {
        const icon = L.divIcon({
          className: "bed-vertex-marker",
          html: `<span class="bed-vertex-dot${index === 0 ? " is-first" : ""}">${index + 1}</span>`,
          iconSize: [28, 28],
          iconAnchor: [14, 14],
        });
        const handle = L.marker(toLL(point[0], point[1]), {
          draggable: true, icon, keyboard: true, zIndexOffset: 1000,
          title: `Move outline point ${index + 1}`,
        }).addTo(map);
        handle.on("dragstart", rememberTrace);
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
    state.tracePts = copyPoints(initialPoints);
    state.traceInitialPts = copyPoints(initialPoints);
    state.traceHistory = [];
    state.suggestedName = suggestedName;
    setMapLocked(true);
    drawTrace();
    nameForm.hidden = true;
    nameError.hidden = true;
    traceActions.hidden = false;
    updateOutlineActions();
    setStatus(bedId
      ? "Adjust the bed's outline, then save it"
      : "Adjust the new bed's outline, then save it");
  }

  function outlineBounds(points) {
    const xs = points.map(point => point[0]);
    const ys = points.map(point => point[1]);
    const left = Math.min(...xs);
    const right = Math.max(...xs);
    const top = Math.min(...ys);
    const bottom = Math.max(...ys);
    const padX = Math.max(20, (right - left) * 0.2);
    const padY = Math.max(20, (bottom - top) * 0.2);
    return [
      [Math.max(0, Math.round(left - padX)), Math.max(0, Math.round(top - padY))],
      [Math.min(state.data.width, Math.round(right + padX)),
       Math.min(state.data.height, Math.round(bottom + padY))],
    ];
  }

  async function requestBedRefinement() {
    if (state.mode !== "trace" || state.tracePts.length < 3) {
      setStatus("Tap at least 3 points around the bed before asking AI to refine it.");
      return;
    }
    const requestId = ++state.suggestionRequest;
    const originalPoints = copyPoints(state.tracePts);
    const initialPoints = copyPoints(state.traceInitialPts);
    const bedId = state.traceBedId;
    const suggestedName = state.suggestedName;
    const bounds = outlineBounds(originalPoints);
    state.mode = "suggesting";
    setMapLocked(true);
    updateOutlineActions(true);
    setStatus("Refining your outline against the visible bed edges...");
    let result;
    try {
      result = await post("/map/beds/suggest/", { bounds, boundary: originalPoints }, 30000);
    } catch (error) {
      result = { error: error.name === "AbortError"
        ? "AI refinement took too long."
        : "The outline service did not answer." };
    }
    if (requestId !== state.suggestionRequest || state.mode !== "suggesting") return;
    if (result.ok) {
      startTrace(bedId, result.boundary, result.suggested_name || suggestedName);
      state.traceInitialPts = initialPoints;
      state.traceHistory = [originalPoints];
      updateOutlineActions();
      setStatus(
        `AI refinement ready (${result.confidence} confidence). ` +
        "Review the round points, undo or adjust them if needed, then save."
      );
      return;
    }
    startTrace(bedId, originalPoints, suggestedName);
    state.traceInitialPts = initialPoints;
    setStatus(`${result.error} Your manual outline is unchanged and ready to save.`);
  }

  function startManualTrace() {
    cancelTrace();
    startTrace(null);
    setStatus("Tap multiple points around the bed edge. Use Undo as needed, then save or refine with AI.");
  }

  function cancelTrace() {
    state.suggestionRequest += 1;
    state.mode = "view";
    state.traceBedId = null;
    state.tracePts = [];
    state.traceInitialPts = [];
    state.traceHistory = [];
    state.suggestedName = "";
    drawTrace();
    setMapLocked(false);
    traceActions.hidden = true;
    nameForm.hidden = true;
    nameError.hidden = true;
    nameInput.value = "";
    setStatus("Tap a bed or marker to identify it.");
  }

  function render(data) {
    state.data = data;
    const bounds = [toLL(0, data.height), toLL(data.width, 0)];
    let primaryMapBounds = null;
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
      if (layer.primary && layer.kind === "master") primaryMapBounds = lb;
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
    // The main property view follows the portrait master map itself. Older
    // gardens may still use a wider permanent coordinate space to preserve
    // saved plant and bed positions; focusing the master bounds avoids gray
    // letterboxing without changing any of that stored geometry.
    map.fitBounds(opts.editor && primaryMapBounds ? primaryMapBounds : bounds);

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
    if (state.mode === "trace") {
      rememberTrace();
      state.tracePts.push([Math.round(x), Math.round(y)]);
      drawTrace();
      updateOutlineActions();
      setStatus(`Outlining: ${state.tracePts.length} point${state.tracePts.length === 1 ? "" : "s"} - keep tapping around the edge, then save or refine with AI.`);
    } else if (state.mode === "place") {
      const res = await post(`/map/plant/${state.placePlantId}/point/`, {
        x: Math.round(x), y: Math.round(y),
      });
      setStatus(res.ok ? `Placed in ${res.bed || "open ground"} (${res.cell}). Reloading...`
                       : "Could not place");
      if (res.ok) setTimeout(() => window.location.reload(), 600);
    }
  });

  if (opts.editor) {
    document.getElementById("trace-new-start").addEventListener("click", startManualTrace);
    document.getElementById("trace-refine-ai").addEventListener("click", requestBedRefinement);
    document.getElementById("trace-existing-start").addEventListener("click", () => {
      const sel = document.getElementById("trace-bed");
      if (!sel.value) { setStatus("Pick the existing bed you want to adjust"); return; }
      const bed = state.data?.beds.find(item => String(item.id) === String(sel.value));
      startTrace(sel.value, bed?.boundary || []);
      setStatus(bed?.boundary?.length
        ? `Adjusting ${bed.name}. Drag a point, add a point, or save the outline.`
        : `Tap around ${bed?.name || "the bed"} to draw its outline, then save.`);
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
        setStatus("Outline ready - confirm or change the garden bed name, then save it");
        nameInput.focus();
        return;
      }
      const res = await post(`/map/bed/${state.traceBedId}/boundary/`,
                             { boundary: state.tracePts });
      setStatus(res.ok ? `Saved (cells ${res.cells.join(", ")}). Reloading...` : res.error);
      if (res.ok) setTimeout(() => window.location.reload(), 600);
    });
    document.getElementById("trace-undo").addEventListener("click", () => {
      if (state.mode !== "trace" || !state.traceHistory.length) {
        setStatus("There is nothing to undo yet.");
        return;
      }
      state.tracePts = state.traceHistory.pop();
      drawTrace();
      updateOutlineActions();
      setStatus(state.tracePts.length
        ? `Undid the last change. The outline has ${state.tracePts.length} point${state.tracePts.length === 1 ? "" : "s"}.`
        : "Tap the first point on the bed's edge");
    });
    document.getElementById("trace-restart").addEventListener("click", () => {
      if (state.traceBedId) {
        state.tracePts = copyPoints(state.traceInitialPts);
        state.traceHistory = [];
        drawTrace();
        updateOutlineActions();
        setStatus(state.tracePts.length
          ? "Restored the bed's saved outline. Adjust it or save when ready."
          : "Starting over. Tap around the bed's edge, then save.");
        return;
      }
      startManualTrace();
    });
    document.getElementById("trace-cancel").addEventListener("click", cancelTrace);
    document.getElementById("new-bed-cancel").addEventListener("click", cancelTrace);
    document.getElementById("new-bed-back").addEventListener("click", () => {
      state.mode = "trace";
      nameForm.hidden = true;
      traceActions.hidden = false;
      updateOutlineActions();
      setStatus("Adjust the outline, then save it again");
    });
    document.getElementById("new-bed-restart").addEventListener("click", startManualTrace);
    nameForm.addEventListener("submit", async (event) => {
      event.preventDefault();
      const outlineAnother = event.submitter?.value === "another";
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
      setStatus(outlineAnother
        ? `Created ${res.bed.name} (${res.bed.code}). Ready for another bed...`
        : `Created ${res.bed.name} (${res.bed.code}). Opening the bed...`);
      setTimeout(() => {
        window.location.href = outlineAnother
          ? `${window.location.pathname}?new_bed=1`
          : res.bed.url;
      }, 600);
    });
    document.getElementById("place-start").addEventListener("click", () => {
      const sel = document.getElementById("place-plant");
      if (!sel.value) { setStatus("Pick the plant to place first"); return; }
      state.mode = "place"; state.placePlantId = sel.value;
      setStatus("Tap the plant's spot on the map");
    });
  }

  fetch(opts.dataUrl || "/map/data.json").then(r => r.json()).then(data => {
    render(data);
    if (opts.editor && opts.newBed) startManualTrace();
  });
}
