import { useEffect, useState } from "react";
import api from "@/lib/api";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { toast } from "sonner";

export default function Settings() {
  const [s, setS] = useState({});
  useEffect(() => { api.get("/settings").then((r) => setS(r.data)); }, []);
  const save = async () => { try { const { data } = await api.put("/settings", s); setS(data); toast.success("Saved"); } catch (e) { toast.error(e?.response?.data?.detail || "Failed"); } };
  return (
    <div className="space-y-4 max-w-2xl" data-testid="settings-page">
      <h1 className="font-display text-3xl font-extrabold text-white">System Settings</h1>
      <Card className="p-5 bg-slate-900/60 border-slate-800 space-y-3">
        <div><Label>Company Name</Label><Input value={s.company_name || ""} onChange={(e) => setS({ ...s, company_name: e.target.value })} className="bg-slate-950 border-slate-800" /></div>
        <div><Label>Company Address</Label><Input value={s.company_address || ""} onChange={(e) => setS({ ...s, company_address: e.target.value })} className="bg-slate-950 border-slate-800" /></div>
        <div><Label>Company Email</Label><Input value={s.company_email || ""} onChange={(e) => setS({ ...s, company_email: e.target.value })} className="bg-slate-950 border-slate-800" /></div>
        <div className="grid grid-cols-2 gap-3">
          <div><Label>Geofence Radius (m)</Label><Input type="number" value={s.geofence_radius || 100} onChange={(e) => setS({ ...s, geofence_radius: +e.target.value })} className="bg-slate-950 border-slate-800" data-testid="setting-geofence" /></div>
          <div><Label>GPS Interval (s)</Label><Input type="number" value={s.gps_interval || 4} onChange={(e) => setS({ ...s, gps_interval: +e.target.value })} className="bg-slate-950 border-slate-800" /></div>
        </div>
        <Button onClick={save} className="bg-emerald-500 hover:bg-emerald-600 text-slate-950" data-testid="settings-save">Save Settings</Button>
      </Card>
    </div>
  );
}
