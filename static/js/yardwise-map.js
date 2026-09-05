/* YardWise property map. Hand-written on purpose (no build step).
   Coordinate space: CRS.Simple map units; y grows downward like image pixels,
   so every Leaflet latlng is [-y, x] and we convert at the edges. */
/* global L */

function yardwiseMap(opts) {
  const el = document.getElementById("map");
  const map = L.map(el, { crs: L.CRS.Simple, minZoom: -3, attributionControl: false });
  const state = { data: null, mode: "view", traceBedId: null, tracePts: [],
                  placePlantId: null, markers: {}, bedShapes: {}, traceLayer: null };

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
      if (state.traceLayer) state.traceLayer.remove();
      state.traceLayer = L.polygon(state.tracePts.map(p => toLL(p[0], p[1])), {
        color: "#bc5f38", dashArray: "6 4", fillOpacity: 0.1,
      }).addTo(map);
      setStatus(`Tracing: ${state.tracePts.length} points - tap "Finish bed" when done`);
    } else if (state.mode === "place") {
      const res = await post(`/map/plant/${state.placePlantId}/point/`, {
        x: Math.round(x), y: Math.round(y),
      });
      setStatus(res.ok ? `Placed in ${res.bed || "open ground"} (${res.cell}). Reloading...`
                       : "Could not place");
      if (res.ok) setTimeout(() => window.location.reload(), 600);
    }
  });

  document.getElementById("trace-start").addEventListener("click", () => {
    const sel = document.getElementById("trace-bed");
    if (!sel.value) { setStatus("Pick which bed you're tracing first"); return; }
    state.mode = "trace"; state.traceBedId = sel.value; state.tracePts = [];
    setStatus("Tap around the bed's edge on the map");
  });
  document.getElementById("trace-finish").addEventListener("click", async () => {
    if (state.mode !== "trace" || state.tracePts.length < 3) {
      setStatus("Need at least 3 points"); return;
    }
    const res = await post(`/map/bed/${state.traceBedId}/boundary/`,
                           { boundary: state.tracePts });
    setStatus(res.ok ? `Saved (cells ${res.cells.join(", ")}). Reloading...` : res.error);
    if (res.ok) setTimeout(() => window.location.reload(), 600);
  });
  document.getElementById("place-start").addEventListener("click", () => {
    const sel = document.getElementById("place-plant");
    if (!sel.value) { setStatus("Pick the plant to place first"); return; }
    state.mode = "place"; state.placePlantId = sel.value;
    setStatus("Tap the plant's spot on the map");
  });

  fetch("/map/data.json").then(r => r.json()).then(render);
}
