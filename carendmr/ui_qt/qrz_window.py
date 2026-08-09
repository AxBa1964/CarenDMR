"""Nicht-modales QRZ.com-Stationsfenster mit interaktiver Funkkarte."""
from __future__ import annotations

import html
import json
import math
import queue
import threading
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from PySide6.QtCore import QTimer, Qt, QUrl
from PySide6.QtGui import QDesktopServices, QPixmap
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from carendmr.qrz import QrzProfile

try:
    from PySide6.QtWebEngineCore import QWebEngineSettings
    from PySide6.QtWebEngineWidgets import QWebEngineView
except ImportError:  # pragma: no cover - depends on local PySide6 packaging
    QWebEngineSettings = None
    QWebEngineView = None


def _yes_no(value: str) -> str:
    normalized = str(value or "").strip().lower()
    if normalized in {"1", "y", "yes", "true"}:
        return "Ja"
    if normalized in {"0", "n", "no", "false"}:
        return "Nein"
    return value or "Nicht angegeben"


def _distance_and_bearing(
    own: QrzProfile | None, remote: QrzProfile
) -> tuple[float | None, float | None]:
    if (
        own is None
        or own.latitude is None
        or own.longitude is None
        or remote.latitude is None
        or remote.longitude is None
    ):
        return None, None

    lat1 = math.radians(own.latitude)
    lon1 = math.radians(own.longitude)
    lat2 = math.radians(remote.latitude)
    lon2 = math.radians(remote.longitude)
    dlat = lat2 - lat1
    dlon = lon2 - lon1

    a = (
        math.sin(dlat / 2.0) ** 2
        + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2.0) ** 2
    )
    distance_km = 6371.0088 * 2.0 * math.atan2(math.sqrt(a), math.sqrt(max(0.0, 1.0 - a)))

    y = math.sin(dlon) * math.cos(lat2)
    x = math.cos(lat1) * math.sin(lat2) - (
        math.sin(lat1) * math.cos(lat2) * math.cos(dlon)
    )
    bearing = (math.degrees(math.atan2(y, x)) + 360.0) % 360.0
    return distance_km, bearing


def _profile_point(profile: QrzProfile | None) -> dict | None:
    if profile is None or profile.latitude is None or profile.longitude is None:
        return None
    return {
        "call": profile.callsign,
        "lat": float(profile.latitude),
        "lon": float(profile.longitude),
        "grid": profile.grid or "",
        "name": profile.display_name or "",
        "country": profile.country or "",
    }


def _build_leaflet_html(
    own: QrzProfile | None,
    remote: QrzProfile,
    maptiler_api_key: str = "",
) -> str:
    own_point = _profile_point(own)
    remote_point = _profile_point(remote)
    distance_km, bearing = _distance_and_bearing(own, remote)

    payload = {
        "own": own_point,
        "remote": remote_point,
        "distanceKm": round(distance_km, 1) if distance_km is not None else None,
        "bearing": round(bearing) if bearing is not None else None,
    }
    data = json.dumps(payload, ensure_ascii=False)
    maptiler_key_json = json.dumps(str(maptiler_api_key or ""), ensure_ascii=False)

    # Leaflet is loaded from its public CDN. The visible raster layer is the
    # official OSM Standard tile endpoint and attribution remains on-screen.
    return f"""<!doctype html>
<html lang="de">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"
 integrity="sha256-p4NxAoJBhIIN+hmNHrzRCf9tD/miZyoHS5obTRR9BMY="
 crossorigin="">
<style>
html, body {{ width: 100%; height: 100%; margin: 0; overflow: hidden; background: #101923; }}
#map {{ position: absolute; inset: 0; width: 100%; height: 100%; }}
.leaflet-container {{ font-family: "Segoe UI", sans-serif; background: #102331; }}
.station-popup b {{ font-size: 14px; }}
.ham-grid-label {{
  color: #ffd54a; font-size: 11px; font-weight: 700;
  text-shadow: 0 0 3px #000, 0 0 3px #000;
  background: transparent; border: 0; box-shadow: none;
}}
.route-info {{
  background: rgba(16,25,35,.92); color: #f7fafc; border: 1px solid #4c6078;
  border-radius: 6px; padding: 6px 9px; font: 12px "Segoe UI", sans-serif;
}}
</style>
</head>
<body>
<div id="map"></div>
<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"
 integrity="sha256-20nQCchB9co0qIjJZRGuk2/Z9VM+kNiyxNV1lvTlZBo="
 crossorigin=""></script>
<script>
const stationData = {data};
const mapTilerKey = {maptiler_key_json};
const map = L.map('map', {{
    zoomControl: true,
    scrollWheelZoom: true,
    worldCopyJump: true,
    minZoom: 2,
    maxZoom: 19
}}).setView([20, 0], 2);

const osm = L.tileLayer('https://tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png', {{
    maxZoom: 19,
    attribution: '&copy; OpenStreetMap contributors'
}}).addTo(map);

const satellite = mapTilerKey ? L.tileLayer(
    'https://api.maptiler.com/maps/satellite-v4/{{z}}/{{x}}/{{y}}@2x.jpg?key=' + encodeURIComponent(mapTilerKey),
    {{
        tileSize: 512,
        zoomOffset: -1,
        minZoom: 1,
        maxZoom: 20,
        crossOrigin: true,
        attribution: '&copy; MapTiler &copy; OpenStreetMap contributors'
    }}
) : null;

if (satellite) {{
    satellite.on('tileerror', function(event) {{
        console.error(
            'CarenDMR MapTiler satellite tile failed',
            event && event.tile ? event.tile.src : ''
        );
    }});
}}

const hamGrid = L.layerGroup().addTo(map);
let routeLine = null;

function flagPinIcon(role) {{
    const own = role === 'own';
    const pinColor = own ? '#f2c94c' : '#ef5b62';
    const flagColor = own ? '#ffd54a' : '#ff6b73';
    const title = own ? 'Eigener Standort' : 'Gegenstation';
    return L.divIcon({{
        className: '',
        html: `<div title="${{title}}" style="
          position:relative;width:34px;height:42px;">
          <div style="
            position:absolute;left:13px;top:3px;width:3px;height:27px;
            background:#f7fafc;border-radius:2px;
            box-shadow:0 1px 3px rgba(0,0,0,.75);"></div>
          <div style="
            position:absolute;left:16px;top:4px;width:16px;height:11px;
            background:${{flagColor}};border:1px solid #fff;
            clip-path:polygon(0 0,100% 18%,78% 52%,100% 82%,0 100%);
            box-shadow:0 1px 3px rgba(0,0,0,.75);"></div>
          <div style="
            position:absolute;left:8px;top:27px;width:13px;height:13px;
            border-radius:50% 50% 50% 0;background:${{pinColor}};
            border:2px solid #fff;transform:rotate(-45deg);
            box-shadow:0 1px 4px rgba(0,0,0,.8);"></div>
        </div>`,
        iconSize: [34,42],
        iconAnchor: [15,38],
        popupAnchor: [2,-36],
        tooltipAnchor: [2,-36]
    }});
}}

function addStation(point, label, role) {{
    if (!point) return null;
    const m = L.marker([point.lat, point.lon], {{
        icon: flagPinIcon(role),
        zIndexOffset: role === 'remote' ? 1000 : 900
    }}).addTo(map);
    const location = [point.grid, point.country].filter(Boolean).join(' · ');
    const roleText = role === 'own' ? 'Eigener Standort' : 'Gegenstation';
    m.bindPopup(
      `<div class="station-popup"><b>${{label}}</b> · ${{roleText}}` +
      `${{point.name ? '<br>' + point.name : ''}}` +
      `${{location ? '<br>' + location : ''}}` +
      `<br>${{point.lat.toFixed(4)}}, ${{point.lon.toFixed(4)}}</div>`
    );
    m.bindTooltip(label, {{
        permanent:true, direction:'top', offset:[2,-31], opacity:.95
    }});
    return m;
}}

const ownMarker = addStation(
    stationData.own,
    stationData.own ? stationData.own.call : 'Ich',
    'own'
);
const remoteMarker = addStation(
    stationData.remote,
    stationData.remote ? stationData.remote.call : '',
    'remote'
);

if (stationData.own && stationData.remote) {{
    routeLine = L.polyline(
      [[stationData.own.lat, stationData.own.lon],
       [stationData.remote.lat, stationData.remote.lon]],
      {{color:'#64b5ff', weight:2, opacity:.85, dashArray:'8,7'}}
    ).addTo(map);
}}

const sourceInfo = L.control({{position:'topleft'}});
sourceInfo.onAdd = function() {{
    const div = L.DomUtil.create('div', 'route-info');
    div.id = 'map-source-info';
    div.innerHTML = 'Karte';
    return div;
}};
sourceInfo.addTo(map);

const info = L.control({{position:'bottomleft'}});
info.onAdd = function() {{
    const div = L.DomUtil.create('div', 'route-info');
    if (stationData.distanceKm !== null) {{
        div.innerHTML = `<b>${{stationData.own.call}} → ${{stationData.remote.call}}</b>` +
          `<br>${{stationData.distanceKm}} km · ${{stationData.bearing}}°`;
    }} else if (stationData.remote) {{
        div.innerHTML = `<b>${{stationData.remote.call}}</b>` +
          `${{stationData.remote.grid ? '<br>Locator ' + stationData.remote.grid : ''}}`;
    }}
    return div;
}};
info.addTo(map);

function fieldName(lon, lat) {{
    const adjLon = Math.max(-180, Math.min(179.999999, lon)) + 180;
    const adjLat = Math.max(-90, Math.min(89.999999, lat)) + 90;
    const a = String.fromCharCode(65 + Math.floor(adjLon / 20));
    const b = String.fromCharCode(65 + Math.floor(adjLat / 10));
    return a + b;
}}

function squareName(lon, lat) {{
    const adjLon = Math.max(-180, Math.min(179.999999, lon)) + 180;
    const adjLat = Math.max(-90, Math.min(89.999999, lat)) + 90;
    const field = fieldName(lon, lat);
    const lonInField = adjLon % 20;
    const latInField = adjLat % 10;
    const x = Math.floor(lonInField / 2);
    const y = Math.floor(latInField);
    return field + String(x) + String(y);
}}

function gridLabel(text, center, size=42) {{
    return L.marker(center, {{
        interactive:false,
        icon:L.divIcon({{
            className:'ham-grid-label',
            html:text,
            iconSize:[size,18],
            iconAnchor:[size/2,9]
        }})
    }}).addTo(hamGrid);
}}

function drawHamGrid() {{
    if (!map._loaded || !map.hasLayer(hamGrid)) return;
    hamGrid.clearLayers();
    const zoom = map.getZoom();
    const bounds = map.getBounds();

    if (zoom <= 5) {{
        // Maidenhead-Felder: 20° Länge × 10° Breite. Bereits in der
        // Weltansicht sichtbar, damit HAM Grid eindeutig erkennbar ist.
        const west = Math.floor((bounds.getWest()+180)/20)*20-180;
        const east = Math.ceil((bounds.getEast()+180)/20)*20-180;
        const south = Math.floor((bounds.getSouth()+90)/10)*10-90;
        const north = Math.ceil((bounds.getNorth()+90)/10)*10-90;
        for (let lon=west; lon<east; lon+=20) {{
            for (let lat=south; lat<north; lat+=10) {{
                if (lon < -180 || lon >= 180 || lat < -90 || lat >= 90) continue;
                L.rectangle([[lat,lon],[lat+10,lon+20]], {{
                    color:'#ffd54a',
                    weight:2.2,
                    opacity:.90,
                    fill:true,
                    fillColor:'#ffd54a',
                    fillOpacity:.035,
                    interactive:false
                }}).addTo(hamGrid);
                gridLabel(fieldName(lon+10,lat+5), [lat+5, lon+10], 38);
            }}
        }}
    }} else {{
        // 4-stellige Maidenhead-Squares: 2° Länge × 1° Breite.
        const west = Math.floor(bounds.getWest()/2)*2;
        const east = Math.ceil(bounds.getEast()/2)*2;
        const south = Math.floor(bounds.getSouth());
        const north = Math.ceil(bounds.getNorth());
        const maxCells = 900;
        let cells = 0;
        for (let lon=west; lon<east && cells<maxCells; lon+=2) {{
            for (let lat=south; lat<north && cells<maxCells; lat+=1) {{
                if (lon < -180 || lon >= 180 || lat < -90 || lat >= 90) continue;
                L.rectangle([[lat,lon],[lat+1,lon+2]], {{
                    color:'#ffd54a',
                    weight:1.25,
                    opacity:.72,
                    fill:false,
                    interactive:false
                }}).addTo(hamGrid);
                if (zoom >= 7) {{
                    gridLabel(squareName(lon+1,lat+.5), [lat+.5, lon+1], 50);
                }}
                cells++;
            }}
        }}
    }}
}}
map.on('zoomend moveend', drawHamGrid);

function syncMapSize() {{
    if (!map._loaded) return;
    map.invalidateSize({{pan:false, debounceMoveend:true}});
}}

function worldView() {{
    syncMapSize();
    const points = [];
    if (stationData.own) points.push([stationData.own.lat, stationData.own.lon]);
    if (stationData.remote) points.push([stationData.remote.lat, stationData.remote.lon]);
    if (points.length >= 2) {{
        map.fitBounds(points, {{padding:[55,55], maxZoom:7}});
    }} else if (points.length === 1) {{
        map.setView(points[0], 5);
    }} else {{
        map.setView([20,0], 2);
    }}
    setTimeout(drawHamGrid, 120);
}}

function detailView() {{
    syncMapSize();
    if (stationData.remote) {{
        map.setView([stationData.remote.lat, stationData.remote.lon], 11);
        if (remoteMarker) remoteMarker.openPopup();
    }}
    setTimeout(drawHamGrid, 120);
}}

function toggleGrid(enabled) {{
    if (enabled) {{
        if (!map.hasLayer(hamGrid)) hamGrid.addTo(map);
        drawHamGrid();
    }} else {{
        if (map.hasLayer(hamGrid)) map.removeLayer(hamGrid);
    }}
}}

function setBaseLayer(mode) {{
    if (mode === 'satellite' && satellite) {{
        if (map.hasLayer(osm)) map.removeLayer(osm);
        if (!map.hasLayer(satellite)) satellite.addTo(map);
        satellite.bringToBack();
        if (routeLine) routeLine.bringToFront();
        const source = document.getElementById('map-source-info');
        if (source) source.innerHTML = 'Satellit';
        drawHamGrid();
        return 'satellite';
    }}
    if (satellite && map.hasLayer(satellite)) map.removeLayer(satellite);
    if (!map.hasLayer(osm)) osm.addTo(map);
    osm.bringToBack();
    if (routeLine) routeLine.bringToFront();
    const source = document.getElementById('map-source-info');
    if (source) source.innerHTML = 'Karte';
    drawHamGrid();
    return 'map';
}}

window.syncMapSize = syncMapSize;
window.worldView = worldView;
window.detailView = detailView;
window.toggleGrid = toggleGrid;
window.setBaseLayer = setBaseLayer;

const baseLayers = {{'Karte': osm}};
if (satellite) baseLayers['Satellit'] = satellite;
L.control.layers(baseLayers, {{'HAM Grid': hamGrid}}, {{collapsed:false}}).addTo(map);
setTimeout(() => {{
    syncMapSize();
    worldView();
}}, 120);
</script>
</body>
</html>"""


class QrzStationWindow(QMainWindow):
    def __init__(
        self,
        profile: QrzProfile,
        *,
        own_profile: QrzProfile | None = None,
        maptiler_api_key: str = "",
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.profile = profile
        self.own_profile = own_profile
        self.maptiler_api_key = str(maptiler_api_key or "").strip()
        self._image_updates: queue.Queue[bytes | Exception] = queue.Queue()
        self._map_ready = False
        self.setWindowTitle(f"QRZ.com – {profile.callsign}")
        self.resize(1040, 760)
        self.setMinimumSize(860, 650)

        central = QWidget(self)
        root = QVBoxLayout(central)
        root.setContentsMargins(14, 12, 14, 12)
        root.setSpacing(9)

        heading_row = QHBoxLayout()
        heading = QLabel(profile.callsign)
        heading.setObjectName("callsignDisplay")
        heading_row.addWidget(heading)
        heading_row.addStretch(1)

        subtitle_parts = [
            profile.display_name,
            profile.grid,
            profile.country,
        ]
        subtitle = QLabel(" · ".join(part for part in subtitle_parts if part))
        subtitle.setObjectName("secondaryText")
        heading_row.addWidget(subtitle)
        root.addLayout(heading_row)

        top = QHBoxLayout()
        top.setSpacing(14)

        image_frame = QFrame()
        image_frame.setObjectName("card")
        image_layout = QVBoxLayout(image_frame)
        image_layout.setContentsMargins(8, 8, 8, 8)
        self.image_label = QLabel("Kein Profilbild")
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.image_label.setFixedSize(300, 300)
        self.image_label.setFrameShape(QFrame.Shape.NoFrame)
        image_layout.addWidget(self.image_label)
        top.addWidget(image_frame, 0, Qt.AlignmentFlag.AlignTop)

        details_frame = QFrame()
        details_frame.setObjectName("card")
        details = QGridLayout(details_frame)
        details.setContentsMargins(12, 10, 12, 10)
        details.setHorizontalSpacing(8)
        details.setVerticalSpacing(5)
        details.setColumnMinimumWidth(0, 92)
        details.setColumnStretch(1, 1)

        distance_km, bearing = _distance_and_bearing(own_profile, profile)
        distance_text = (
            f"{distance_km:.0f} km · {bearing:.0f}°"
            if distance_km is not None and bearing is not None
            else "Nicht verfügbar"
        )
        rows = [
            ("Name", profile.display_name or "Nicht angegeben"),
            ("Ort", profile.city or "Nicht angegeben"),
            ("Region", profile.state or "Nicht angegeben"),
            ("Land", profile.country or "Nicht angegeben"),
            ("Locator", profile.grid or "Nicht angegeben"),
            ("Koordinaten", self._coordinates_text(profile)),
            ("Entfernung", distance_text),
            ("CQ / ITU", self._zones_text(profile)),
            ("QSL-Manager", profile.qsl_manager or "Nicht angegeben"),
            ("LoTW", _yes_no(profile.lotw)),
            ("eQSL", _yes_no(profile.eqsl)),
        ]
        for row, (caption, value) in enumerate(rows):
            cap = QLabel(caption)
            cap.setObjectName("fieldCaption")
            cap.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
            val = QLabel(value)
            val.setObjectName("fieldValue")
            val.setMinimumHeight(28)
            val.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
            details.addWidget(cap, row, 0)
            details.addWidget(val, row, 1)

        top.addWidget(details_frame, 1)
        root.addLayout(top)

        map_frame = QFrame()
        map_frame.setObjectName("card")
        map_layout = QVBoxLayout(map_frame)
        map_layout.setContentsMargins(5, 5, 5, 5)

        self.map_view = None
        if QWebEngineView is not None:
            self.map_view = QWebEngineView(map_frame)
            self.map_view.setMinimumHeight(300)
            if QWebEngineSettings is not None:
                settings = self.map_view.settings()
                settings.setAttribute(
                    QWebEngineSettings.WebAttribute.LocalContentCanAccessRemoteUrls,
                    True,
                )
            self.map_view.loadFinished.connect(self._map_loaded)
            self.map_view.setHtml(
                _build_leaflet_html(
                    own_profile,
                    profile,
                    maptiler_api_key=self.maptiler_api_key,
                ),
                QUrl("https://unpkg.com/"),
            )
            map_layout.addWidget(self.map_view, 1)
        else:
            fallback = QLabel(
                "Interaktive Karte nicht verfügbar.\n"
                "PySide6 QtWebEngineWidgets ist in dieser Umgebung nicht installiert."
            )
            fallback.setAlignment(Qt.AlignmentFlag.AlignCenter)
            fallback.setObjectName("secondaryText")
            fallback.setMinimumHeight(220)
            map_layout.addWidget(fallback)

        root.addWidget(map_frame, 1)

        buttons = QHBoxLayout()
        self.world_button = QPushButton("Welt")
        self.world_button.clicked.connect(self._world_view)
        buttons.addWidget(self.world_button)

        self.detail_button = QPushButton("Details")
        self.detail_button.clicked.connect(self._detail_view)
        buttons.addWidget(self.detail_button)

        self.grid_button = QPushButton("HAM Grid")
        self.grid_button.setCheckable(True)
        self.grid_button.setChecked(True)
        self.grid_button.toggled.connect(self._toggle_grid)
        buttons.addWidget(self.grid_button)

        self.satellite_button = QPushButton("Satellit")
        self.satellite_button.setCheckable(True)
        self.satellite_button.setEnabled(bool(self.maptiler_api_key))
        self.satellite_button.setToolTip(
            "Zwischen OpenStreetMap und MapTiler Satellite wechseln."
            if self.maptiler_api_key
            else "MapTiler API-Key fehlt in config/qrz.local.json."
        )
        self.satellite_button.toggled.connect(self._toggle_satellite)
        buttons.addWidget(self.satellite_button)

        buttons.addStretch(1)

        open_button = QPushButton("QRZ.com öffnen")
        open_button.clicked.connect(
            lambda: QDesktopServices.openUrl(QUrl(self.profile.qrz_page_url))
        )
        buttons.addWidget(open_button)
        root.addLayout(buttons)

        self.setCentralWidget(central)

        self._image_timer = QTimer(self)
        self._image_timer.setInterval(100)
        self._image_timer.timeout.connect(self._poll_image)
        self._image_timer.start()

        if profile.image_url:
            self.image_label.setText("Profilbild wird geladen …")
            threading.Thread(
                target=self._load_image_worker,
                name=f"CarenDMR-QRZ-Image-{profile.callsign}",
                daemon=True,
            ).start()

    @staticmethod
    def _coordinates_text(profile: QrzProfile) -> str:
        if profile.latitude is None or profile.longitude is None:
            return "Nicht angegeben"
        return f"{profile.latitude:.4f}, {profile.longitude:.4f}"

    @staticmethod
    def _zones_text(profile: QrzProfile) -> str:
        cq = profile.cq_zone or "–"
        itu = profile.itu_zone or "–"
        return f"CQ {cq} · ITU {itu}"

    def _map_loaded(self, ok: bool) -> None:
        self._map_ready = bool(ok and self.map_view is not None)
        if not self._map_ready:
            return
        QTimer.singleShot(
            80,
            lambda: self._run_map_js(
                "if (typeof syncMapSize === 'function') { syncMapSize(); }"
            ),
        )
        QTimer.singleShot(
            180,
            lambda: self._run_map_js(
                "if (typeof syncMapSize === 'function' && "
                "typeof worldView === 'function') { syncMapSize(); worldView(); }"
            ),
        )

    def resizeEvent(self, event) -> None:  # noqa: N802 - Qt API
        super().resizeEvent(event)
        if self.map_view is not None and self._map_ready:
            QTimer.singleShot(
                60,
                lambda: self._run_map_js(
                    "if (typeof syncMapSize === 'function') { syncMapSize(); }"
                ),
            )

    def _run_map_js(self, script: str) -> None:
        if self.map_view is not None and self._map_ready:
            self.map_view.page().runJavaScript(script)

    def _world_view(self) -> None:
        self._run_map_js(
            "if (typeof syncMapSize === 'function' && "
            "typeof worldView === 'function') { syncMapSize(); worldView(); }"
        )
        QTimer.singleShot(
            120,
            lambda: self._run_map_js(
                "if (typeof syncMapSize === 'function') { syncMapSize(); }"
            ),
        )

    def _detail_view(self) -> None:
        self._run_map_js(
            "if (typeof syncMapSize === 'function' && "
            "typeof detailView === 'function') { syncMapSize(); detailView(); }"
        )
        QTimer.singleShot(
            120,
            lambda: self._run_map_js(
                "if (typeof syncMapSize === 'function') { syncMapSize(); }"
            ),
        )

    def _toggle_satellite(self, enabled: bool) -> None:
        mode = "satellite" if enabled else "map"
        self._run_map_js(
            f"if (typeof setBaseLayer === 'function') {{ setBaseLayer('{mode}'); }}"
        )
        self.satellite_button.setText("Karte" if enabled else "Satellit")
        self.satellite_button.setToolTip(
            "Zur OpenStreetMap-Karte wechseln."
            if enabled
            else "Zur MapTiler-Satellitenansicht wechseln."
        )

    def _toggle_grid(self, enabled: bool) -> None:
        value = str(bool(enabled)).lower()
        self._run_map_js(
            f"if (typeof toggleGrid === 'function') {{ toggleGrid({value}); }}"
        )

    def _load_image_worker(self) -> None:
        try:
            request = Request(
                self.profile.image_url,
                headers={"User-Agent": "CarenDMR-QRZ/0.2"},
            )
            with urlopen(request, timeout=10) as response:
                self._image_updates.put(response.read())
        except (HTTPError, URLError, TimeoutError, OSError) as error:
            self._image_updates.put(error)

    def _poll_image(self) -> None:
        try:
            value = self._image_updates.get_nowait()
        except queue.Empty:
            return
        if isinstance(value, Exception):
            self.image_label.setText("Profilbild nicht verfügbar")
            return
        pixmap = QPixmap()
        if not pixmap.loadFromData(value):
            self.image_label.setText("Profilbild nicht lesbar")
            return
        scaled = pixmap.scaled(
            self.image_label.size(),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        self.image_label.setPixmap(scaled)
