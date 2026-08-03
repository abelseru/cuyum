(() => {
  const API = '/json';
  const NORMAL_MS = 5000;
  const ALERT_MS = 1500;

  let map = null;
  let sensorLayer = null;
  let zoneLayer = null;
  let connectionLayer = null;

  // Conserva los marcadores entre actualizaciones para que
  // un popup abierto no desaparezca cada 1,5 o 5 segundos.
  const sensorMarkers = new Map();
  let timer = null;
  let audioEnabled = false;
  let audioCtx = null;
  let lastAlertBeep = 0;
  const previousSensorSignals = new Map();
  let sensorSignalSnapshotReady = false;
  let lastBoundsKey = '';
  let currentCoverageBounds = null;
  let userMovedMap = false;

  const CELL_COLORS = ['#8b5cf6', '#0ea5e9', '#ec4899', '#2563eb', '#a855f7', '#e11d48'];
  const $ = (id) => document.getElementById(id);

  
function uiClassLabel(value) {
  const text = String(value || "").trim().toLowerCase();
  const map = {
    "high": "alta",
    "strong": "alta",
    "good": "buena",
    "minimal": "mínima",
    "listening": "escucha",
    "single station": "escucha",
    "waiting": "en espera",
    "no coverage": "sin cobertura",
    "no recent data": "en espera",
    "no_coverage": "sin cobertura",
    "strong_cell": "alta",
    "good_cell": "buena",
    "minimal_cell": "mínima",
    "single_station": "escucha",
    "blind_zone": "sin cobertura",
    "stale_cell": "en espera"
  };
  return map[text] || value || "en espera";
}

function uiNetworkLabel(value) {
  const text = String(value || "").trim().toLowerCase();
  const map = {
    "high multicell network": "red multicelda alta",
    "partial multicell network": "red multicelda parcial",
    "active local network": "red local activa",
    "degraded network": "red degradada",
    "partial network": "red parcial"
  };
  return map[text] || value || "red Cuyum";
}

function uiSensorState(value) {
  const text = String(value || "").trim().toLowerCase();

  const map = {
    "active": "activo",
    "inactive": "inactivo",
    "waiting": "en espera",
    "listening": "en escucha",
    "calibrating": "calibrando",
    "high_latency": "latencia alta",
    "high latency": "latencia alta",
    "disconnected": "desconectado",
    "candidate": "candidato",
    "observed": "observado",
    "reliable": "confiable"
  };

  return map[text] || value || "activo";
}

function uiDirectionLabel(value) {
  const text = String(value || "").trim().toLowerCase();
  const map = {
    "north": "NORTE",
    "northeast": "NORESTE",
    "east": "ESTE",
    "southeast": "SURESTE",
    "south": "SUR",
    "southwest": "SUROESTE",
    "west": "OESTE",
    "northwest": "NOROESTE",
    "local": "Local"
  };
  return map[text] || value || "Zona";
}

function escapeHtml(value) {
    return String(value ?? '').replace(/[&<>'"]/g, (ch) => ({'&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#39;','"':'&quot;'}[ch]));
  }

  function cleanText(value) {
    return String(value || '').toLowerCase().normalize('NFD').replace(/[\u0300-\u036f]/g, '');
  }

  function firstRelevantCell(data) {
    const cells = data.display_cells || data.cells || [];
    return cells.find(c => Number(c.confirming || 0) > 0)
      || cells.find(c => cleanText(c.state || c.state_label).includes('observ') || cleanText(c.state || c.state_label).includes('senal'))
      || cells.find(c => c.role === 'early_warning')
      || cells[0]
      || null;
  }

  function cellHumanLabel(cell) {
    if (!cell) return 'Red';
    const raw = cell.label || cell.short_label || cell.direction_label || 'Zona';
    return uiDirectionLabel(raw);
  }

  function warningSecondsFrom(data, cell) {
    const values = [
      cell && cell.warning_seconds,
      cell && cell.effective_warning_seconds,
      data.auto_cell_01_aviso_util,
      data.warning_seconds
    ];
    for (const value of values) {
      const n = Number(value);
      if (Number.isFinite(n) && n > 0) return Math.round(n);
    }
    return null;
  }

  function demoState(data) {
    return null;
  }

  function statusFromData(data) {
    const demo = demoState(data);
    if (demo) return demo;

    const display = data.display || {};
    const alert = data.alert || {};
    const cell = firstRelevantCell(data);
    const text = cleanText(`${display.status || ''} ${display.message || ''}`);
    const isSound = alert.sound || Number(alert.buzzer_seconds || 0) > 0;

    if (isSound || text.includes('anticip') || text.includes('signal')) {
      const seconds = warningSecondsFrom(data, cell);
      return { mode: 'alert', word: 'Atención', hint: `${cellHumanLabel(cell)}${seconds ? ` · ${seconds} s estimados` : ''}` };
    }
    if (text.includes('confirm') || text.includes('possible movement')) {
      return { mode: 'watch', word: 'Movimiento posible', hint: `${cellHumanLabel(cell)} · datos coincidentes` };
    }
    if (text.includes('observ') || text.includes('senal') || text.includes('signal')) {
      return { mode: 'watch', word: 'Señal detectada', hint: `${cellHumanLabel(cell)} · en observación` };
    }
    if (text.includes('sin datos') || text.includes('degradada') || text.includes('blind')) {
      return { mode: 'offline', word: 'Sin datos', hint: 'esperando lectura de Cuyum' };
    }
    return { mode: 'normal', word: 'Operativo', hint: 'sin señales relevantes' };
  }

  function normalizeClassLabel(value) {
    const v = String(value || '').toLowerCase().trim();
    if (v === 'fuerte' || v === 'alta' || v === 'strong_cell') return 'alta';
    if (v === 'buena' || v === 'media' || v === 'good_cell') return 'buena';
    if (v === 'mínima' || v === 'minima' || v === 'básica' || v === 'basica' || v === 'minimal_cell') return 'mínima';
    if (v === 'escucha' || v === 'regular' || v === 'single_station') return 'regular';
    if (!v || v.includes('espera') || v.includes('cobertura') || v.includes('datos') || v.includes('blind') || v.includes('stale')) return 'en espera';
    return v;
  }

  function qualityWidth(label) {
    const v = normalizeClassLabel(label);
    if (v === 'alta') return 100;
    if (v === 'buena') return 75;
    if (v === 'mínima') return 45;
    if (v === 'regular') return 28;
    return 10;
  }

  
  const CELL_COLOR_BY_ID = {
    cell_00: '#DB2777',
    auto_cell_01: '#06B6D4',
    auto_cell_02: '#2563EB',
    auto_cell_03: '#3730A3',
    auto_cell_04: '#7C3AED',
    regional_observers: '#CBD5E1'
  };

function displayCellId(cell, i) {
    return cell.cell_id || cell.id || `cell_${i}`;
  }

  function cellIndex(cells, cellId) {
    const idx = (cells || []).findIndex((c, i) => displayCellId(c, i) === cellId || c.cell_id === cellId || c.id === cellId);
    return idx >= 0 ? idx : 0;
  }

  function cellColorByIndex(index) {
    return CELL_COLORS[Math.max(0, index) % CELL_COLORS.length];
  }

  function cellColor(cells, cellId) {
    const id = String(cellId || '');
    if (CELL_COLOR_BY_ID[id]) return CELL_COLOR_BY_ID[id];

    const idx = cellIndex(cells, cellId);
    return cellColorByIndex(idx);
  }


    function installLanguageSwitcher(targetMap) {
    if (!targetMap || !window.L) return;

    const currentLanguage =
      String(document.documentElement.lang || 'es').toLowerCase();

    const targetLanguage =
      currentLanguage.startsWith('en') ? 'es' : 'en';

    const languageCode = targetLanguage.toUpperCase();

    const label =
      targetLanguage === 'en'
        ? 'Switch to English'
        : 'Cambiar a español';

    const url = new URL(window.location.href);
    url.searchParams.set('lang', targetLanguage);

    if (targetMap._cuyumLanguageControl) {
      try {
        targetMap.removeControl(targetMap._cuyumLanguageControl);
      } catch (e) {}
      targetMap._cuyumLanguageControl = null;
    }

    const LanguageControl = L.Control.extend({
      options: { position: 'topleft' },

      onAdd: function () {
        const wrap = L.DomUtil.create(
          'div',
          'leaflet-control cuyum-language-control'
        );

        const link = L.DomUtil.create(
          'a',
          'cuyum-language-switch is-' + targetLanguage,
          wrap
        );

        link.href = url.pathname + '?' + url.searchParams.toString();
        link.title = label;
        link.setAttribute('aria-label', label);

        link.innerHTML =
          '<span class="cuyum-language-bubble" aria-hidden="true">💬</span>' +
          '<span class="cuyum-language-code">' +
          languageCode +
          '</span>';

        L.DomEvent.disableClickPropagation(wrap);
        L.DomEvent.disableScrollPropagation(wrap);

        return wrap;
      }
    });

    targetMap._cuyumLanguageControl = new LanguageControl();
    targetMap._cuyumLanguageControl.addTo(targetMap);
  }

  function initMap() {
    if (map || !window.L) return;

    map = L.map('leafletMap', {
      zoomControl: true,
      attributionControl: true,
      dragging: true,
      scrollWheelZoom: false,
      doubleClickZoom: true,
      boxZoom: false,
      keyboard: false,
      tap: true,
      touchZoom: true,
      maxBoundsViscosity: 0.85
    }).setView([-32.8895, -68.8458], 6);

    installLanguageSwitcher(map);

    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
      maxZoom: 18,
      minZoom: 3,
      attribution: '&copy; OpenStreetMap'
    }).addTo(map);

    connectionLayer = L.layerGroup().addTo(map);
    zoneLayer = L.layerGroup().addTo(map);
    sensorLayer = L.layerGroup().addTo(map);

    map.on('dragstart zoomstart', () => { userMovedMap = true; });
    setTimeout(() => map.invalidateSize(), 200);
    window.addEventListener('resize', () => setTimeout(() => map.invalidateSize(), 100));
  }

  function setMeter(id, value, max) {
    const el = $(id);
    if (!el) return;
    const n = Number(value);
    const pct = Number.isFinite(n) ? Math.max(0, Math.min(100, (n / max) * 100)) : 0;
    el.style.width = `${pct}%`;
  }

  function setText(id, value) {
    const el = $(id);
    if (el) el.textContent = value;
  }

  function setStateCard(data) {
    const card = $('stateCard');
    const state = statusFromData(data);
    card.classList.remove('state-normal', 'state-watch', 'state-alert', 'state-offline');
    card.classList.add(state.mode === 'alert' ? 'state-alert' : (state.mode === 'watch' ? 'state-watch' : (state.mode === 'offline' ? 'state-offline' : 'state-normal')));

    setText('mainMessage', state.word);
    setText('statusHint', state.hint);
    setText('lastUpdate', data.updated_at ? new Date(data.updated_at).toLocaleTimeString([], {hour: '2-digit', minute: '2-digit', second: '2-digit'}) : '--:--:--');

    const network = data.network || {};
    const zones = network.cells_active ?? data.cells_active ?? '--';
    const sensors = network.sensors_active ?? '--';
    setText('zonesCount', zones);
    setText('sensorsCount', sensors);
  }

  function sensorCountLabel(cell) {
    const active = Number(cell.sensors_active || 0);
    const observers = Number(cell.observer_sensors || 0);

    if (observers > 0) {
      return `${active} + ${observers} obs.`;
    }

    return String(active);
  }

  function renderCompetentAuthority(data) {
    const authority = data.competent_authority || {};
    const name = String(authority.name || "INPRES").trim() || "INPRES";
    const recordsUrl = String(
      authority.records_url ||
      "https://contenidos.inpres.gob.ar/sismologia/xultimos"
    ).trim();

    const button = $("competentAuthorityButton");

    if (button) {
      button.textContent = `🏛️ Ver ${name}`;
      button.href = recordsUrl;
    }
  }

  function renderCells(cells) {
    const box = $('cellsList');
    box.innerHTML = '';
    if (!cells || cells.length === 0) {
      box.innerHTML = '<div class="zone-row"><div class="zone-name-wrap"><span></span><b class="zone-name">Inicializando</b></div><span class="zone-level">--</span><span class="zone-sensors">--</span></div>';
      return;
    }
    cells.slice(0, 6).forEach((cell, index) => {
      const id = displayCellId(cell, index);
      const color = cellColor(cells, cell.cell_id || cell.id || `cell_${index}`);
      const label = uiClassLabel(cell.class_label || cell.class || 'waiting');
      const row = document.createElement('div');
      row.className = 'zone-row';
      row.dataset.cellId = id;
      row.style.setProperty('--cell-color', color);
      row.innerHTML = `
        <div class="zone-name-wrap">
          <span class="zone-dot" aria-hidden="true"></span>
          <b class="zone-name">${escapeHtml(uiDirectionLabel(cell.label || cell.short_label || cell.direction_label || 'Zona'))}</b>
        </div>
        <span class="zone-level">${escapeHtml(label)}</span>
        <span class="zone-sensors">${escapeHtml(sensorCountLabel(cell))}</span>
      `;
      box.appendChild(row);
    });
  }

  function liveSensors(data) {
    return (data.sensors || [])
      .filter(s => s.has_location && Number.isFinite(Number(s.lat)) && Number.isFinite(Number(s.lon)))
      .map(s => ({ ...s, lat: Number(s.lat), lon: Number(s.lon) }));
  }


  function liveCells(data) {
    const displayCells = Array.isArray(data.display_cells) ? data.display_cells : [];
    const mapCells = Array.isArray(data.cells) ? data.cells : [];
    const sensors = Array.isArray(data.sensors) ? data.sensors : [];

    const byId = new Map();
    mapCells.forEach(c => {
      const id = c.cell_id || c.id;
      if (id) byId.set(id, c);
    });

    const source = displayCells.length ? displayCells : mapCells;

    return source.map((cell, index) => {
      const id = cell.cell_id || cell.id || `cell_${index}`;
      const base = byId.get(id) || {};
      const merged = { ...base, ...cell, cell_id: id };

      let lat = Number(merged.lat);
      let lon = Number(merged.lon);

      if (!Number.isFinite(lat) || !Number.isFinite(lon)) {
        const related = sensors.filter(s => sensorCellId(s) === id && Number.isFinite(Number(s.lat)) && Number.isFinite(Number(s.lon)));
        if (related.length) {
          lat = related.reduce((sum, s) => sum + Number(s.lat), 0) / related.length;
          lon = related.reduce((sum, s) => sum + Number(s.lon), 0) / related.length;
        }
      }

      if (!Number.isFinite(lat) || !Number.isFinite(lon)) {
        return null;
      }

      merged.lat = lat;
      merged.lon = lon;
      return merged;
    }).filter(Boolean);
  }


  function isRegionalObserver(sensor) {
    return String(sensor.role || sensor.rol || '').toLowerCase() === 'observador_regional'
      || sensor.cell_id === 'regional_observers'
      || sensor.role === 'regional_observer';
  }

  function sensorCellId(sensor) {
    const cid = sensor.cell_id || sensor.cell || sensor.cellId;

    // The auto_cell_* entries are real cells. They must not be converted into
    // regional_observers, aunque su role interno sea regional_observer.
    if (cid && String(cid).startsWith('auto_cell_')) return cid;

    if (cid) return cid;

    if (isRegionalObserver(sensor)) return 'regional_observers';

    return 'no_cell';
  }

  function sensorStyle(sensor, cells) {
    const cid = sensorCellId(sensor);
    const color = cellColor(cells, cid);

    if (sensor.flag) {
      return {
        radius: 9,
        color: '#2b0b0b',
        weight: 2,
        fillColor: '#e00000',
        fillOpacity: 1,
        opacity: 1
      };
    }

    const calibrated = sensor.calibrated !== false;

    return {
      radius: calibrated ? 7 : 6,
      color: calibrated ? '#ffffff' : color,
      weight: calibrated ? 2.5 : 2,
      fillColor: color,
      fillOpacity: calibrated ? 0.92 : 0.55,
      opacity: calibrated ? 0.98 : 0.85,
      dashArray: calibrated ? null : '4 4'
    };
  }

  function zoneStyle(cell, cells) {
    const color = cellColor(cells, cell.cell_id || cell.id);
    return { color, weight: 3, opacity: .75, fillColor: color, fillOpacity: .085, radius: 22000 };
  }


  function makeZoneMarker(color) {
    return L.divIcon({
      className: 'zone-center-dot',
      html: `<span style="background:${color}; border-color:${color};"></span>`,
      iconSize: [18, 18],
      iconAnchor: [9, 9]
    });
  }

  function makeHomeMarker(zoom = 6) {
    const size = zoom >= 10 ? 44 : (zoom >= 8 ? 50 : 56);
    const imgSize = Math.max(36, size - 8);

    return L.divIcon({
      className: 'cuyum-system-center-icon',
      html: `<span style="width:${size}px;height:${size}px;"><img src="/static/cuyum_favicon_64.png" alt="Cuyum" style="width:${imgSize}px;height:${imgSize}px;"></span>`,
      iconSize: [size, size],
      iconAnchor: [size / 2, size / 2]
    });
  }


  function sensorQualityLabel(sensor) {
    const q = Number(sensor.score_selection);
    if (Number.isFinite(q)) {
      if (q >= 0.86) return 'alta';
      if (q >= 0.72) return 'buena';
      if (q >= 0.50) return 'regular';
      return 'en revisión';
    }
    if (sensor.calibrated === false) return 'en revisión';
    return 'operativa';
  }

  function sensorLocationLabel(sensor) {
    const src = String(sensor.location_source || '').toLowerCase();
    if (sensor.approx_location || src.includes('aproximada') || src.includes('override')) return 'ubicación pública aproximada';
    return 'ubicación de inventario';
  }

  function sensorPopup(sensor) {
    const title =
      sensor.locality ||
      (sensor.name && sensor.name !== sensor.sensor_id ? sensor.name : null) ||
      sensor.sensor_id ||
      'Sensor';
    const code = sensor.sensor_id || '';
    const zona = isRegionalObserver(sensor) ? 'Observadores' : (sensor.cell_label || sensor.cell_id || 'Zona');
    const estado = uiSensorState(sensor.state);
    const calidad = sensorQualityLabel(sensor);
    const ubicacion = sensorLocationLabel(sensor);
    const latencia = Number(sensor.latency_seconds);
    const latText = Number.isFinite(latencia) ? `<br>Latencia: ${latencia.toFixed(1)} s` : '';
    return `<b>${escapeHtml(title)}</b><br>${escapeHtml(code)}<br>Zona: ${escapeHtml(zona)}<br>Estado: ${escapeHtml(estado)}<br>Calidad: ${escapeHtml(calidad)}<br>${escapeHtml(ubicacion)}${latText}`;
  }

  function buildBounds(points) {
    if (!points.length) return null;
    return L.latLngBounds(points.map(p => [p.lat, p.lon])).pad(0.20);
  }

  function boundsKey(bounds) {
    if (!bounds) return '';
    const sw = bounds.getSouthWest();
    const ne = bounds.getNorthEast();
    return [sw.lat.toFixed(2), sw.lng.toFixed(2), ne.lat.toFixed(2), ne.lng.toFixed(2)].join('|');
  }

  function fitCoverage(force = false) {
    if (!map || !currentCoverageBounds) return;
    const protectedBounds = currentCoverageBounds.pad(0.35);
    map.invalidateSize();
    if (force || !userMovedMap) {
      map.fitBounds(currentCoverageBounds, { padding: [36, 36], maxZoom: 8, animate: false });
      userMovedMap = false;
    }
    const baseZoom = map.getZoom();
    map.setMinZoom(Math.max(3, baseZoom - 1));
    map.setMaxZoom(Math.min(13, baseZoom + 5));
    map.setMaxBounds(protectedBounds);
  }

  function renderMap(data) {
    initMap();
    if (!map) {
      $('mapSummary').textContent = 'Mapa no disponible';
      return;
    }
    /*
      Los sensores no se borran aquí. Sus marcadores se actualizan
      individualmente para conservar cualquier popup abierto.
    */
    zoneLayer.clearLayers();
    connectionLayer.clearLayers();

    const cells = liveCells(data);
    const sensors = liveSensors(data);
    const systemCenter = data.system_center && Number.isFinite(Number(data.system_center.lat)) && Number.isFinite(Number(data.system_center.lon))
      ? {
          lat: Number(data.system_center.lat),
          lon: Number(data.system_center.lon),
          label: data.system_center.label || 'Mendoza'
        }
      : { lat: -32.8895, lon: -68.8458, label: 'Mendoza' };

    const home = systemCenter;
    const allPoints = sensors.concat(cells).concat([home]);
    $('mapEmpty').classList.toggle('hidden', allPoints.length > 1);
    const localCell = cells.find(c => c.cell_id === 'cell_00') || { lat: home.lat, lon: home.lon, label: 'Local' };

    cells.forEach((cell, index) => {
      const color = cellColor(cells, cell.cell_id || cell.id || `cell_${index}`);
      if (cell.cell_id !== 'cell_00') {
        L.polyline([[localCell.lat, localCell.lon], [cell.lat, cell.lon]], {
          color, opacity: .42, weight: 2, dashArray: '6 8', interactive: false
        }).addTo(connectionLayer);
      }
      if (cell.cell_id === 'cell_00') {
        const localSensors = sensors.filter(sensor =>
          sensorCellId(sensor) === 'cell_00' &&
          Number.isFinite(Number(sensor.lat)) &&
          Number.isFinite(Number(sensor.lon))
        );

        let localRadius = 22000;

        if (localSensors.length) {
          const centerPoint = L.latLng(cell.lat, cell.lon);

          const farthestMeters = Math.max(
            ...localSensors.map(sensor =>
              centerPoint.distanceTo(
                L.latLng(Number(sensor.lat), Number(sensor.lon))
              )
            )
          );

          localRadius = Math.max(
            10000,
            Math.min(55000, farthestMeters * 0.30)
          );
        }

        const style = zoneStyle(cell, cells);
        style.radius = localRadius;

        L.circle([cell.lat, cell.lon], style).addTo(zoneLayer);
      }
    });

    const currentSensorIds = new Set();

    sensors.forEach((sensor, index) => {
      const sensorId = String(
        sensor.sensor_id ||
        sensor.id ||
        sensor.code ||
        `${sensorCellId(sensor)}:${sensor.lat}:${sensor.lon}:${index}`
      );

      currentSensorIds.add(sensorId);

      let marker = sensorMarkers.get(sensorId);

      if (!marker) {
        marker = L.circleMarker(
          [sensor.lat, sensor.lon],
          sensorStyle(sensor, cells)
        )
          .bindPopup(sensorPopup(sensor))
          .addTo(sensorLayer);

        sensorMarkers.set(sensorId, marker);
      } else {
        marker.setLatLng([sensor.lat, sensor.lon]);
        marker.setStyle(sensorStyle(sensor, cells));
        marker.setPopupContent(sensorPopup(sensor));
      }
    });

    /*
      Retira únicamente sensores que ya no existen en la respuesta.
      Los marcadores restantes conservan su popup y estado de apertura.
    */
    sensorMarkers.forEach((marker, sensorId) => {
      if (currentSensorIds.has(sensorId)) return;

      sensorLayer.removeLayer(marker);
      sensorMarkers.delete(sensorId);
    });

    const bounds = buildBounds(allPoints);
    const key = boundsKey(bounds);
    if (bounds && key !== lastBoundsKey) {
      lastBoundsKey = key;
      currentCoverageBounds = bounds;
      userMovedMap = false;
      fitCoverage(true);
    } else if (bounds) {
      currentCoverageBounds = bounds;
    }

  }


  function playIndividualSensorChirp() {
    if (!audioEnabled || !audioCtx) return;

    const ctx = audioCtx;
    const osc = ctx.createOscillator();
    const gain = ctx.createGain();
    const start = ctx.currentTime;

    /*
      Un único pulso idéntico a uno de los cinco pulsos
      utilizados por playCuyumFiveBeepPattern().
    */
    osc.type = "square";
    osc.frequency.value = 880;

    gain.gain.setValueAtTime(
      0.0001,
      start
    );

    gain.gain.exponentialRampToValueAtTime(
      0.22,
      start + 0.02
    );

    gain.gain.exponentialRampToValueAtTime(
      0.0001,
      start + 0.16
    );

    osc.connect(gain);
    gain.connect(ctx.destination);

    osc.start(start);
    osc.stop(start + 0.18);
  }

  function maybeChirpForIndividualSensor(data) {
    const sensors = Array.isArray(data.sensors)
      ? data.sensors
      : [];

    const currentSignals = new Map();
    let newlyDetected = false;

    sensors.forEach((sensor, index) => {
      const sensorId = String(
        sensor.sensor_id ||
        sensor.id ||
        sensor.code ||
        `${sensor.cell_id || "no_cell"}:${index}`
      );

      const detecting = Boolean(sensor.flag);
      currentSignals.set(sensorId, detecting);

      if (
        sensorSignalSnapshotReady &&
        detecting &&
        previousSensorSignals.get(sensorId) !== true
      ) {
        newlyDetected = true;
      }
    });

    previousSensorSignals.clear();

    currentSignals.forEach((detecting, sensorId) => {
      previousSensorSignals.set(sensorId, detecting);
    });

    if (!sensorSignalSnapshotReady) {
      sensorSignalSnapshotReady = true;
      return;
    }

    const alertSoundActive = Boolean(
      data.alert && data.alert.sound
    );

    if (
      newlyDetected &&
      audioEnabled &&
      !alertSoundActive
    ) {
      try {
        playIndividualSensorChirp();
      } catch (error) {
        console.warn(
          "Cuyum individual sensor chirp unavailable",
          error
        );
      }
    }
  }

  function playCuyumFiveBeepPattern() {
    const AudioContext =
      window.AudioContext || window.webkitAudioContext;

    if (!AudioContext) return;

    const ctx = audioCtx || new AudioContext();
    audioCtx = ctx;

    for (let i = 0; i < 5; i++) {
      const osc = ctx.createOscillator();
      const gain = ctx.createGain();
      const start = ctx.currentTime + i * 0.28;

      osc.type = "square";
      osc.frequency.value = 880;

      gain.gain.setValueAtTime(
        0.0001,
        start
      );

      gain.gain.exponentialRampToValueAtTime(
        0.22,
        start + 0.02
      );

      gain.gain.exponentialRampToValueAtTime(
        0.0001,
        start + 0.16
      );

      osc.connect(gain);
      gain.connect(ctx.destination);

      osc.start(start);
      osc.stop(start + 0.18);
    }
  }

  function maybeBeep(data) {
    const alert = data.alert || {};
    const soundActive = Boolean(alert.sound);

    if (!soundActive) {
      lastAlertBeep = 0;
      return;
    }

    if (!audioEnabled) return;

    // El patrón ya fue reproducido durante este episodio.
    if (lastAlertBeep !== 0) return;

    lastAlertBeep = Date.now();

    try {
      playCuyumFiveBeepPattern();
    } catch (error) {
      console.warn(
        "Cuyum sound unavailable",
        error
      );
    }
  }

  async function tick() {
    try {
      const res = await fetch(API, { cache: 'no-store' });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      renderCompetentAuthority(data);
      setStateCard(data);
      renderCells(data.display_cells || []);
      renderMap(data);
      maybeChirpForIndividualSensor(data);
      maybeBeep(data);
      const next = (data.poll && data.poll.next_ms) || ((data.alert && data.alert.active) ? ALERT_MS : NORMAL_MS);
      timer = setTimeout(tick, next);
    } catch (err) {
      setText('mainMessage', 'Sin conexión');
      setText('statusHint', 'reintentando conexión con Cuyum');
      timer = setTimeout(tick, NORMAL_MS);
    }
  }

  const centerButton = $('centerMapButton');
  if (centerButton) {
    centerButton.addEventListener('click', () => {
      userMovedMap = false;
      fitCoverage(true);
    });
  }

  $('audioButton').addEventListener('click', async () => {
    try {
      audioCtx = audioCtx || new (window.AudioContext || window.webkitAudioContext)();
      await audioCtx.resume();

      audioEnabled = true;
      playIndividualSensorChirp();

      const audioButton = $('audioButton');
      audioButton.classList.remove('audio-attention');
      audioButton.classList.add('audio-test');
      $('audioButton').classList.add('active');
      $('audioButton').textContent = 'Audio activo';
    } catch (e) {
      $('audioButton').textContent = 'Audio no disponible';
    }
  });

  window.addEventListener('load', () => {
    initMap();
    tick();
  });
})();

/* Page-level simulation button.
   This does not modify Cuyum state files.
   It only changes the live page rendering for a few seconds. */
(function () {
  const SIM_KEY = "cuyum_page_simulation_until";
  const SIM_DURATION_MS = 10000;

  function simulationActive() {
    const until = Number(sessionStorage.getItem(SIM_KEY) || 0);
    return Date.now() < until;
  }

  function startSimulation() {
    sessionStorage.setItem(SIM_KEY, String(Date.now() + SIM_DURATION_MS));
    playSimulationSound();

    setTimeout(() => {
      sessionStorage.removeItem(SIM_KEY);
      window.location.reload();
    }, SIM_DURATION_MS);

    window.dispatchEvent(new Event("cuyum-simulation-start"));
  }

  function showSimulationBanner(text) {
    return;
  }

  function playSimulationSound() {
    try {
      playCuyumFiveBeepPattern();
    } catch (error) {
      console.warn(
        "simulation sound unavailable",
        error
      );
    }
  }

  function chooseFarthestCell(data) {
    const cells = Array.isArray(data.cells) ? data.cells : [];
    if (!cells.length) return null;

    const early = cells.filter(c => c.role === "early_warning");
    const pool = early.length ? early : cells;

    return pool
      .slice()
      .sort((a, b) => Number(b.warning_seconds || 0) - Number(a.warning_seconds || 0))[0];
  }

  function applySimulation(data) {
    if (!simulationActive()) return data;

    const copy = JSON.parse(JSON.stringify(data || {}));

    copy.display = copy.display || {};
    copy.alert = copy.alert || {};
    copy.network = copy.network || {};
    copy.cells = Array.isArray(copy.cells) ? copy.cells : [];
    copy.display_cells = Array.isArray(copy.display_cells) ? copy.display_cells : [];
    copy.sensors = Array.isArray(copy.sensors) ? copy.sensors : [];

    const targetCell = chooseFarthestCell(copy);
    const targetCellId = targetCell ? targetCell.cell_id : null;

    copy.display.status = "observacion";
    copy.display.message = "Simulación";
    copy.display.sound = true;

    copy.alert.active = true;
    copy.alert.level = "simulation";
    copy.alert.message = "Simulación";
    copy.alert.sound = true;
    copy.alert.buzzer_seconds = 9999;

    copy.simulation = {
      active: true,
      label: "Simulación",
      duration_seconds: 9999,
      target_cell_id: targetCellId
    };

    for (const cell of copy.cells) {
      if (!targetCellId || cell.cell_id === targetCellId) {
        cell.state_label = "Simulación";
        cell.warning_seconds = 9999;
      }
    }

    for (const cell of copy.display_cells) {
      if (!targetCellId || cell.cell_id === targetCellId) {
        cell.state_label = "Simulación";
        cell.warning_seconds = 9999;
      }
    }

    for (const sensor of copy.sensors) {
      if (!targetCellId || sensor.cell_id === targetCellId) {
        sensor.flag = true;
        sensor.state = "activo";
        sensor.calibrated = true;
        sensor.ratio = Math.max(Number(sensor.ratio || 0), 9.99);
        sensor.simulation = true;
      } else {
        sensor.flag = false;
      }
    }

    return copy;
  }

  function installSimulationButton() {
    if (document.getElementById("simulationButton")) return;

    const button = document.createElement("button");
    button.id = "simulationButton";
    button.className = "simulation-button simulation-bottom-button";
    button.type = "button";
    button.innerHTML = "<span aria-hidden=\"true\">🔊</span> Probar simulación";
    button.addEventListener("click", startSimulation);

    const bottomBar =
      document.querySelector(".map-footer") ||
      document.querySelector(".map-actions") ||
      document.querySelector(".bottom-actions") ||
      document.querySelector(".live-actions") ||
      Array.from(document.querySelectorAll("div, footer, nav"))
        .find(el => {
          const t = (el.textContent || "").toLowerCase();
          return t.includes("estado actual") && t.includes("registros recientes");
        });

    if (bottomBar) {
      bottomBar.appendChild(button);
      return;
    }

    const mapCard =
      document.querySelector(".map-card") ||
      document.querySelector(".map-panel") ||
      document.querySelector("main");

    if (mapCard) {
      const row = document.createElement("div");
      row.className = "simulation-bottom-row";
      row.appendChild(button);
      mapCard.appendChild(row);
      return;
    }

    document.body.appendChild(button);
  }

  function installFetchInterceptor() {
    if (window.__cuyumSimulationFetchInstalled) return;
    window.__cuyumSimulationFetchInstalled = true;

    const originalFetch = window.fetch.bind(window);

    window.fetch = async function (resource, options) {
      const response = await originalFetch(resource, options);

      try {
        const url = typeof resource === "string" ? resource : resource.url;

        if (url && url.includes("/json")) {
          const cloned = response.clone();
          const data = await cloned.json();
          const simulated = applySimulation(data);

          return new Response(JSON.stringify(simulated), {
            status: response.status,
            statusText: response.statusText,
            headers: {
              "Content-Type": "application/json; charset=utf-8"
            }
          });
        }
      } catch (err) {
        console.warn("simulation fetch patch skipped", err);
      }

      return response;
    };
  }

  function forceSimulationBannerLoop() {
    return;
  }


  function installAudioAttention() {
    const audioButton =
      document.getElementById("audioButton") ||
      Array.from(document.querySelectorAll("button, a"))
        .find(el => {
          const t = (el.textContent || "").trim().toLowerCase();
          return t.includes("activar audio") || t.includes("audio");
        });

    if (!audioButton) return;

    audioButton.classList.add("audio-attention");
    audioButton.dataset.audioLabel = "ACTIVAR";

    audioButton.addEventListener("click", () => {
      /*
        Conservamos audio-attention porque su pseudo-elemento
        ya está probado visualmente. audio-test cambia el texto
        y desactiva solamente la animación.
      */
      audioButton.classList.add("audio-attention");
      audioButton.classList.add("audio-enabled");
      audioButton.classList.add("audio-test");
      audioButton.dataset.audioLabel = "PROBAR";
    });
  }

  installFetchInterceptor();

  document.addEventListener("DOMContentLoaded", () => {
    installSimulationButton();
    installAudioAttention();
    forceSimulationBannerLoop();

    if (simulationActive()) {
      return;
    }
  });
})();
