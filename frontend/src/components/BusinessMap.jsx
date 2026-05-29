import { useEffect, useMemo, useRef } from "react";
import { MapContainer, Marker, Popup, TileLayer, useMap } from "react-leaflet";
import L from "leaflet";
import "leaflet/dist/leaflet.css";

import { getMapCenter } from "../utils/mapHelpers";

function createBusinessIcon(isSelected) {
  return L.divIcon({
    className: "business-map-marker",
    html: `
      <div class="business-map-marker__outer ${isSelected ? "business-map-marker__outer--active" : ""}">
        <div class="business-map-marker__core ${isSelected ? "business-map-marker__core--active" : ""}"></div>
      </div>
    `,
    iconSize: [28, 28],
    iconAnchor: [14, 14],
    popupAnchor: [0, -12],
  });
}

function MapFocus({ activePoint }) {
  const map = useMap();

  useEffect(() => {
    if (!activePoint) return;
    map.flyTo([activePoint.latitude, activePoint.longitude], 15, {
      duration: 0.55,
      animate: true,
    });
  }, [activePoint, map]);

  return null;
}

function MarkerFocus({ activePointId, markerRefs }) {
  useEffect(() => {
    if (!activePointId) return;
    const marker = markerRefs.current.get(activePointId);
    if (!marker) return;

    const timeoutId = window.setTimeout(() => {
      try {
        // marker from react-leaflet may be a ref object with `openPopup` on the instance
        if (typeof marker.openPopup === "function") marker.openPopup();
        else if (marker?.current && typeof marker.current.openPopup === "function") marker.current.openPopup();
      } catch (err) {
        // swallow to avoid crashing the map UI
        // console.debug('Failed to open popup for marker', err);
      }
    }, 650);

    return () => window.clearTimeout(timeoutId);
  }, [activePointId, markerRefs]);

  return null;
}

function formatNumber(value, fallback = "—") {
  if (value == null || Number.isNaN(Number(value))) return fallback;
  return Number(value).toLocaleString();
}

function buildPopupContent(biz) {
  return {
    title: biz.name || "Không rõ tên",
    address: biz.address || "Chưa có địa chỉ",
    rating: biz.rating != null ? biz.rating.toFixed(1) : null,
    reviews: formatNumber(biz.review_count),
    website: biz.website || null,
  };
}

export default function BusinessMap({ data, selectedBusinessId, onSelectBusiness }) {
  const markerRefs = useRef(new Map());

  const points = useMemo(() => {
    if (!Array.isArray(data)) return [];

    return data
      .map((biz) => {
        const latitude = Number(biz.latitude);
        const longitude = Number(biz.longitude);

        if (!Number.isFinite(latitude) || !Number.isFinite(longitude)) {
          return null;
        }

        return {
          id: biz.id ?? `${biz.name}-${latitude}-${longitude}`,
          latitude,
          longitude,
          source: biz,
          popup: buildPopupContent(biz),
        };
      })
      .filter(Boolean);
  }, [data]);

  const center = useMemo(() => getMapCenter(points), [points]);
  const selectedPoint = useMemo(
    () => points.find((point) => point.id === selectedBusinessId) || points[0] || null,
    [points, selectedBusinessId]
  );
  const activePointId = selectedBusinessId ?? selectedPoint?.id ?? null;

  if (!points.length) {
    return (
      <div className="mt-6 rounded-2xl border border-white/10 bg-gradient-to-br from-slate-900 via-slate-900 to-slate-800 p-5 shadow-2xl shadow-black/20">
        <div className="mb-4 flex items-center justify-between gap-3">
          <div>
            <p className="font-display text-sm font-bold text-white/80 mb-1">Bản đồ địa điểm</p>
            <p className="font-mono text-xs text-dim">
              Chưa có tọa độ hợp lệ để hiển thị bản đồ. Hãy đảm bảo pipeline lưu `latitude` và `longitude` cho các địa điểm.
            </p>
          </div>
          <span className="rounded-full border border-emerald-400/20 bg-emerald-400/10 px-3 py-1 font-mono text-[10px] uppercase tracking-[0.25em] text-emerald-300">
            Map
          </span>
        </div>
        <div className="rounded-2xl border border-white/10 bg-black/20 p-4">
          <p className="font-mono text-[11px] uppercase tracking-[0.25em] text-dim mb-2">Lý do</p>
          <p className="font-mono text-xs text-dim">
            Chưa có tọa độ hợp lệ để hiển thị bản đồ. Hãy đảm bảo pipeline lưu `latitude` và `longitude` cho các địa điểm.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="mt-6 overflow-hidden rounded-2xl border border-white/10 bg-gradient-to-br from-slate-900 via-slate-900 to-slate-800 p-5 shadow-2xl shadow-black/20">
      <div className="mb-4 flex flex-wrap items-end justify-between gap-3">
        <div>
          <p className="font-display text-sm font-bold text-white/80">Bản đồ địa điểm tìm được</p>
          <p className="font-mono text-xs text-dim">
            Hiển thị {points.length.toLocaleString()} điểm có tọa độ hợp lệ
          </p>
        </div>
        <div className="flex items-center gap-2 text-[10px] uppercase tracking-[0.25em] font-mono text-dim">
          <span className="rounded-full border border-white/10 bg-white/5 px-3 py-1 text-emerald-300">Click bảng để bay tới điểm</span>
          <span className="rounded-full border border-white/10 bg-white/5 px-3 py-1">Click marker để xem chi tiết</span>
        </div>
      </div>

      <div className="relative overflow-hidden rounded-2xl border border-white/10 shadow-2xl shadow-black/30">
        <div className="pointer-events-none absolute inset-0 z-[401] bg-[radial-gradient(circle_at_top_left,rgba(0,255,148,0.12),transparent_28%),radial-gradient(circle_at_bottom_right,rgba(129,140,248,0.10),transparent_30%)]" />
        <MapContainer
          center={center}
          zoom={12}
          scrollWheelZoom
          zoomControl={false}
          className="business-map h-[460px] w-full"
        >
          <TileLayer
            attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
            url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
          />
          <MapFocus activePoint={selectedPoint} />
          <MarkerFocus activePointId={selectedBusinessId} markerRefs={markerRefs} />
          {points.map((point) => (
            <Marker
              key={point.id}
              ref={(marker) => {
                if (marker) markerRefs.current.set(point.id, marker);
                else markerRefs.current.delete(point.id);
              }}
              position={[point.latitude, point.longitude]}
              icon={point.id === activePointId ? createBusinessIcon(true) : createBusinessIcon(false)}
              eventHandlers={{
                click: () => onSelectBusiness?.(point.id),
              }}
            >
              <Popup>
                <div className="min-w-[240px] space-y-2 rounded-xl bg-slate-950 px-1 py-1 text-slate-100">
                  <div>
                    <p className="text-sm font-semibold text-white">{point.popup.title}</p>
                    <p className="text-xs text-slate-300">{point.popup.address}</p>
                  </div>
                  <div className="flex items-center gap-2 text-[11px] text-slate-300">
                    <span className="rounded-full border border-emerald-400/20 bg-emerald-400/10 px-2 py-0.5 text-emerald-300">
                      ⭐ {point.popup.rating ?? "—"}
                    </span>
                    <span className="rounded-full border border-white/10 bg-white/5 px-2 py-0.5">
                      {point.popup.reviews} review
                    </span>
                  </div>
                  {point.popup.website && (
                    <a
                      href={point.popup.website}
                      target="_blank"
                      rel="noreferrer"
                      className="text-xs text-emerald-300 underline underline-offset-2 break-all"
                    >
                      {point.popup.website}
                    </a>
                  )}
                </div>
              </Popup>
            </Marker>
          ))}
        </MapContainer>
      </div>
    </div>
  );
}
