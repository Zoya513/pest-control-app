import { useEffect, useState } from "react";
import api from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";

export default function Travel() {
  const { can } = useAuth();
  const [trips, setTrips] = useState([]);
  const [customers, setCustomers] = useState([]);
  const [techs, setTechs] = useState([]);
  const [filter, setFilter] = useState({ date_from: "", date_to: "", user_id: "" });

  const load = () => {
    const q = new URLSearchParams();
    Object.entries(filter).forEach(([k, v]) => { if (v) q.set(k, v); });
    api.get(`/travel${q.toString() ? "?" + q : ""}`).then((r) => setTrips(r.data));
  };
  useEffect(() => {
    load();
    if (can("customers", "view")) api.get("/customers").then((r) => setCustomers(r.data));
    if (can("members", "view")) api.get("/users").then((r) => setTechs(r.data.filter((u) => u.role === "technician")));
    // eslint-disable-next-line
  }, []);

  const cmap = Object.fromEntries(customers.map((c) => [c.id, c]));
  const tmap = Object.fromEntries(techs.map((t) => [t.id, t]));

  return (
    <div className="space-y-4" data-testid="travel-page">
      <h1 className="font-display text-3xl font-extrabold">Travel Log</h1>
      <Card className="p-4 flex flex-wrap gap-3 items-end">
        {can("members", "view") && (
          <div><Label>Technician</Label>
            <Select value={filter.user_id || "__all__"} onValueChange={(v) => setFilter({ ...filter, user_id: v === "__all__" ? "" : v })}>
              <SelectTrigger className="w-48" data-testid="travel-tech"><SelectValue placeholder="All" /></SelectTrigger>
              <SelectContent><SelectItem value="__all__">All</SelectItem>{techs.map((t) => <SelectItem key={t.id} value={t.id}>{t.full_name}</SelectItem>)}</SelectContent>
            </Select>
          </div>
        )}
        <div><Label>From</Label><Input type="date" value={filter.date_from} onChange={(e) => setFilter({ ...filter, date_from: e.target.value })} data-testid="travel-from" /></div>
        <div><Label>To</Label><Input type="date" value={filter.date_to} onChange={(e) => setFilter({ ...filter, date_to: e.target.value })} data-testid="travel-to" /></div>
        <Button onClick={load} className="bg-primary text-primary-foreground" data-testid="travel-apply">Apply</Button>
        <Button variant="outline" onClick={() => { setFilter({ date_from: "", date_to: "", user_id: "" }); setTimeout(load, 50); }}>Reset</Button>
      </Card>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
        {trips.length === 0 && <div className="text-muted-foreground col-span-full text-center py-10">No travel data yet.</div>}
        {trips.map((t, i) => (
          <Card key={i} className="p-4">
            <div className="flex justify-between">
              <div>
                <div className="font-medium">{tmap[t.user_id]?.full_name || `User ${t.user_id.slice(0, 6)}`}</div>
                <div className="text-xs text-muted-foreground font-mono">{new Date(t.start_time).toLocaleString()}</div>
              </div>
              <Badge className="bg-teal-500/10 text-teal-500 border-teal-500/30 font-mono">{(t.distance_m / 1000).toFixed(2)} KM</Badge>
            </div>
            <div className="mt-2 text-xs text-muted-foreground">GPS points: {t.point_count}</div>
            <div className="mt-2 flex gap-2 text-xs">
              <button onClick={() => window.open(`https://www.google.com/maps?q=${t.start.lat},${t.start.lng}`, "_blank")} className="text-primary hover:underline">Start</button>
              <span className="text-muted-foreground">→</span>
              <button onClick={() => window.open(`https://www.google.com/maps?q=${t.end.lat},${t.end.lng}`, "_blank")} className="text-primary hover:underline">End</button>
            </div>
          </Card>
        ))}
      </div>
    </div>
  );
}
