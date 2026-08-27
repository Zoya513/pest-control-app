import { useEffect, useState } from "react";
import { MapContainer, TileLayer, Marker, Popup } from "react-leaflet";
import L from "leaflet";
import api from "@/lib/api";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";

const techIcon = new L.DivIcon({
  className: "custom-marker",
  html: `<div style="width:32px;height:32px;border-radius:50%;background:#10B981;border:3px solid #0B0F17;display:grid;place-items:center;color:#0B0F17;font-weight:700;font-size:12px;box-shadow:0 0 0 3px rgba(16,185,129,0.35)">T</div>`,
  iconSize: [32, 32], iconAnchor: [16, 16],
});

export default function LiveMap() {
  const [users, setUsers] = useState([]);
  useEffect(() => {
    const load = () => api.get("/location/live").then((r) => setUsers(r.data)).catch(() => {});
    load();
    const i = setInterval(load, 10000);
    return () => clearInterval(i);
  }, []);

  const center = users.find((u) => u.last_lat) ? [users.find((u) => u.last_lat).last_lat, users.find((u) => u.last_lat).last_lng] : [-6.2088, 106.8456];

  return (
    <div className="space-y-4" data-testid="livemap-page">
      <div className="flex justify-between items-center">
        <div><h1 className="font-display text-3xl font-extrabold text-white">Live Field Map</h1><p className="text-slate-400 text-sm">Real-time technician locations · updates every 10s</p></div>
        <Badge className="bg-emerald-500/10 text-emerald-400 border-emerald-500/30 font-mono">{users.filter((u) => u.online).length} online</Badge>
      </div>
      <Card className="p-2 bg-slate-900/60 border-slate-800">
        <MapContainer center={center} zoom={12} style={{ height: "70vh", borderRadius: 8 }}>
          <TileLayer url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png" attribution="OSM" />
          {users.filter((u) => u.last_lat).map((u) => (
            <Marker key={u.id} position={[u.last_lat, u.last_lng]} icon={techIcon}>
              <Popup>
                <div style={{ minWidth: 180 }}>
                  <div style={{ fontWeight: 700 }}>{u.full_name}</div>
                  <div style={{ fontSize: 12, color: "#64748B" }}>{u.position || u.role}</div>
                  <div style={{ marginTop: 4, fontSize: 11 }}>
                    Status: <b style={{ color: u.online ? "#10B981" : "#EF4444" }}>{u.online ? "Online" : "Offline"}</b><br />
                    GPS: {u.gps_status || "n/a"}<br />
                    Last seen: {u.last_seen ? new Date(u.last_seen).toLocaleTimeString() : "—"}
                  </div>
                </div>
              </Popup>
            </Marker>
          ))}
        </MapContainer>
      </Card>
    </div>
  );
}
