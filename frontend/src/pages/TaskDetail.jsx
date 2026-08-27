import { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import api from "@/lib/api";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { MapContainer, TileLayer, Marker } from "react-leaflet";
import L from "leaflet";
import { ArrowLeft } from "lucide-react";

const icon = new L.Icon({ iconUrl: "https://cdn.jsdelivr.net/npm/leaflet@1.9.4/dist/images/marker-icon.png", iconSize: [25, 41], iconAnchor: [12, 41] });

export default function TaskDetail() {
  const { id } = useParams();
  const [task, setTask] = useState(null);
  useEffect(() => { api.get(`/tasks/${id}`).then((r) => setTask(r.data)); }, [id]);
  if (!task) return <div className="text-slate-500">Loading...</div>;
  const c = task.customer;
  return (
    <div className="space-y-4">
      <Link to="/tasks" className="text-emerald-400 text-sm flex items-center gap-1"><ArrowLeft className="w-4 h-4" /> Back to tasks</Link>
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <Card className="lg:col-span-2 p-6 bg-slate-900/60 border-slate-800">
          <div className="flex items-start justify-between">
            <div>
              <h1 className="font-display text-2xl font-bold text-white">{task.work_target}</h1>
              <div className="text-xs font-mono text-slate-500 mt-1">#{task.id.slice(0, 8)}</div>
            </div>
            <Badge className="bg-emerald-500/10 text-emerald-400 border-emerald-500/30 font-mono uppercase">{task.status}</Badge>
          </div>
          <p className="text-slate-300 mt-4">{task.work_description}</p>

          <div className="grid grid-cols-2 gap-4 mt-6 text-sm">
            <div><div className="text-[10px] uppercase font-mono text-slate-500">Customer</div><div className="text-white">{c?.company_name}</div></div>
            <div><div className="text-[10px] uppercase font-mono text-slate-500">Contact</div><div className="text-white">{c?.contact_person}</div></div>
            <div><div className="text-[10px] uppercase font-mono text-slate-500">Location</div><div className="text-white">{c?.address}</div></div>
            <div><div className="text-[10px] uppercase font-mono text-slate-500">Technician</div><div className="text-white">{task.technician?.full_name}</div></div>
            <div><div className="text-[10px] uppercase font-mono text-slate-500">Scheduled</div><div className="text-white">{task.scheduled_date} · {task.scheduled_time}</div></div>
            <div><div className="text-[10px] uppercase font-mono text-slate-500">Check-in</div><div className="text-white">{task.check_in_at || "—"}</div></div>
          </div>

          {!task.service_report_id && (
            <div className="mt-6 flex flex-wrap gap-2">
              {c?.latitude && c?.longitude && (
                <>
                  <Button onClick={() => window.open(`https://www.google.com/maps?q=${c.latitude},${c.longitude}`, "_blank")} variant="outline" data-testid="btn-view-map">
                    <ArrowLeft className="w-4 h-4 mr-1 rotate-45" /> View on Map
                  </Button>
                  <Button onClick={() => window.open(`https://www.google.com/maps/dir/?api=1&destination=${c.latitude},${c.longitude}`, "_blank")} className="bg-teal-600 hover:bg-teal-700 text-white" data-testid="btn-navigate">
                    Navigate
                  </Button>
                </>
              )}
              <Link to={`/service-reports/new/${task.id}`}>
                <Button className="bg-primary text-primary-foreground" data-testid="btn-complete-task">Fill Service Report</Button>
              </Link>
            </div>
          )}
        </Card>

        <Card className="p-3 bg-slate-900/60 border-slate-800 min-h-[300px]">
          <div className="text-xs font-mono uppercase text-slate-500 mb-2 px-1">Customer Location</div>
          {c?.latitude && c?.longitude ? (
            <MapContainer center={[c.latitude, c.longitude]} zoom={15} style={{ height: 320, borderRadius: 8 }}>
              <TileLayer url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png" attribution="OSM" />
              <Marker position={[c.latitude, c.longitude]} icon={icon} />
            </MapContainer>
          ) : <div className="text-slate-500 text-sm p-4">No coordinates set for this customer.</div>}
        </Card>
      </div>
    </div>
  );
}
