import { useEffect, useState } from "react";
import api from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Badge } from "@/components/ui/badge";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
import { Plus, Calendar as CalIcon, Trash2 } from "lucide-react";
import { toast } from "sonner";

const WEEKDAYS = [
  { v: 0, l: "Mon" }, { v: 1, l: "Tue" }, { v: 2, l: "Wed" },
  { v: 3, l: "Thu" }, { v: 4, l: "Fri" }, { v: 5, l: "Sat" }, { v: 6, l: "Sun" },
];

export default function Schedule() {
  const { can } = useAuth();
  const [list, setList] = useState([]);
  const [customers, setCustomers] = useState([]);
  const [techs, setTechs] = useState([]);
  const [open, setOpen] = useState(false);
  const [preview, setPreview] = useState(null);
  const [filter, setFilter] = useState({ customer_id: "", technician_id: "", date_from: "", date_to: "" });
  const empty = { customer_id: "", technician_id: "", start_date: "", end_date: "", start_time: "08:00", end_time: "17:00", weekdays: [0, 1, 2, 3, 4, 5], notes: "" };
  const [form, setForm] = useState(empty);

  const load = () => {
    const q = new URLSearchParams();
    Object.entries(filter).forEach(([k, v]) => { if (v) q.set(k, v); });
    api.get(`/schedules${q.toString() ? "?" + q : ""}`).then((r) => setList(r.data));
  };
  useEffect(() => {
    load();
    if (can("customers", "view")) api.get("/customers").then((r) => setCustomers(r.data));
    if (can("members", "view")) api.get("/users").then((r) => setTechs(r.data.filter((u) => u.role === "technician")));
    // eslint-disable-next-line
  }, []);

  const toggleWd = (v) => setForm({ ...form, weekdays: form.weekdays.includes(v) ? form.weekdays.filter((x) => x !== v) : [...form.weekdays, v] });

  const previewCount = () => {
    if (!form.start_date || !form.end_date) return 0;
    const sd = new Date(form.start_date), ed = new Date(form.end_date);
    let c = 0;
    for (let d = new Date(sd); d <= ed; d.setDate(d.getDate() + 1)) {
      const wd = (d.getDay() + 6) % 7; // Mon=0
      if (form.weekdays.includes(wd)) c++;
    }
    return c;
  };

  const submit = async () => {
    try {
      const { data } = await api.post("/schedules/mass-create", form);
      toast.success(`${data.count} schedules created`);
      setOpen(false); setForm(empty); load();
    } catch (e) { toast.error(e?.response?.data?.detail || "Failed"); }
  };

  const del = async (id) => {
    try { await api.delete(`/schedules/${id}`); toast.success("Deleted"); load(); }
    catch (e) { toast.error(e?.response?.data?.detail || "Failed"); }
  };

  // Group by date
  const grouped = {};
  list.forEach((s) => { grouped[s.date] = grouped[s.date] || []; grouped[s.date].push(s); });

  return (
    <div className="space-y-4" data-testid="schedule-page">
      <div className="flex justify-between items-start">
        <div>
          <h1 className="font-display text-3xl font-extrabold">Schedule / Standby</h1>
          <p className="text-muted-foreground text-sm">Manage recurring standby assignments for technicians.</p>
        </div>
        {can("schedule", "create") && (
          <Dialog open={open} onOpenChange={setOpen}>
            <DialogTrigger asChild>
              <Button className="bg-primary text-primary-foreground hover:opacity-90" data-testid="btn-mass-schedule"><Plus className="w-4 h-4 mr-1" />Mass Schedule</Button>
            </DialogTrigger>
            <DialogContent className="max-w-lg">
              <DialogHeader><DialogTitle>Create Mass Schedule</DialogTitle></DialogHeader>
              <div className="space-y-3">
                <div>
                  <Label>Client</Label>
                  <Select value={form.customer_id} onValueChange={(v) => setForm({ ...form, customer_id: v })}>
                    <SelectTrigger data-testid="mass-customer"><SelectValue placeholder="Select client" /></SelectTrigger>
                    <SelectContent>{customers.map((c) => <SelectItem key={c.id} value={c.id}>{c.company_name}</SelectItem>)}</SelectContent>
                  </Select>
                </div>
                <div>
                  <Label>Technician</Label>
                  <Select value={form.technician_id} onValueChange={(v) => setForm({ ...form, technician_id: v })}>
                    <SelectTrigger data-testid="mass-tech"><SelectValue placeholder="Select technician" /></SelectTrigger>
                    <SelectContent>{techs.map((t) => <SelectItem key={t.id} value={t.id}>{t.full_name}</SelectItem>)}</SelectContent>
                  </Select>
                </div>
                <div className="grid grid-cols-2 gap-3">
                  <div><Label>Start Date</Label><Input type="date" value={form.start_date} onChange={(e) => setForm({ ...form, start_date: e.target.value })} data-testid="mass-start-date" /></div>
                  <div><Label>End Date</Label><Input type="date" value={form.end_date} onChange={(e) => setForm({ ...form, end_date: e.target.value })} data-testid="mass-end-date" /></div>
                  <div><Label>Start Time</Label><Input type="time" value={form.start_time} onChange={(e) => setForm({ ...form, start_time: e.target.value })} /></div>
                  <div><Label>End Time</Label><Input type="time" value={form.end_time} onChange={(e) => setForm({ ...form, end_time: e.target.value })} /></div>
                </div>
                <div>
                  <Label className="mb-2 block">Weekdays</Label>
                  <div className="flex gap-1 flex-wrap">
                    {WEEKDAYS.map((w) => (
                      <button key={w.v} type="button" onClick={() => toggleWd(w.v)}
                              className={`px-3 py-1.5 rounded-md text-xs font-medium ${form.weekdays.includes(w.v) ? "bg-primary text-primary-foreground" : "bg-muted text-muted-foreground"}`}
                              data-testid={`wd-${w.v}`}>
                        {w.l}
                      </button>
                    ))}
                  </div>
                </div>
                <div><Label>Notes</Label><Textarea value={form.notes} onChange={(e) => setForm({ ...form, notes: e.target.value })} /></div>
                <div className="text-sm text-muted-foreground">Preview: <b className="text-primary">{previewCount()}</b> schedule entries will be created.</div>
                <Button onClick={submit} className="w-full bg-primary text-primary-foreground" data-testid="mass-submit">Create Schedules</Button>
              </div>
            </DialogContent>
          </Dialog>
        )}
      </div>

      <Card className="p-4 flex flex-wrap gap-3 items-end">
        <div><Label>{"Client"}</Label>
          <Select value={filter.customer_id || "__all__"} onValueChange={(v) => setFilter({ ...filter, customer_id: v === "__all__" ? "" : v })}>
            <SelectTrigger className="w-48" data-testid="filter-customer"><SelectValue placeholder="All clients" /></SelectTrigger>
            <SelectContent>
              <SelectItem value="__all__">All</SelectItem>
              {customers.map((c) => <SelectItem key={c.id} value={c.id}>{c.company_name}</SelectItem>)}
            </SelectContent>
          </Select>
        </div>
        <div><Label>Technician</Label>
          <Select value={filter.technician_id || "__all__"} onValueChange={(v) => setFilter({ ...filter, technician_id: v === "__all__" ? "" : v })}>
            <SelectTrigger className="w-48" data-testid="filter-tech"><SelectValue placeholder="All technicians" /></SelectTrigger>
            <SelectContent>
              <SelectItem value="__all__">All</SelectItem>
              {techs.map((t) => <SelectItem key={t.id} value={t.id}>{t.full_name}</SelectItem>)}
            </SelectContent>
          </Select>
        </div>
        <div><Label>From</Label><Input type="date" value={filter.date_from} onChange={(e) => setFilter({ ...filter, date_from: e.target.value })} /></div>
        <div><Label>To</Label><Input type="date" value={filter.date_to} onChange={(e) => setFilter({ ...filter, date_to: e.target.value })} /></div>
        <Button onClick={load} className="bg-primary text-primary-foreground" data-testid="apply-schedule-filter">Apply</Button>
        <Button variant="outline" onClick={() => { setFilter({ customer_id: "", technician_id: "", date_from: "", date_to: "" }); setTimeout(load, 50); }}>Reset</Button>
      </Card>

      <div className="space-y-3">
        {Object.keys(grouped).sort().map((d) => (
          <Card key={d} className="p-4">
            <div className="flex items-center gap-2 mb-2">
              <CalIcon className="w-4 h-4 text-primary" />
              <div className="text-xs font-mono uppercase text-primary">{d}</div>
              <Badge variant="outline">{grouped[d].length} entries</Badge>
            </div>
            <div className="space-y-1">
              {grouped[d].map((s) => (
                <div key={s.id} className="flex justify-between items-center text-sm border-t border-border py-2">
                  <div>
                    <div className="font-medium">{s.customer?.company_name} — {s.technician?.full_name}</div>
                    <div className="text-xs text-muted-foreground font-mono">{s.start_time} - {s.end_time} · {s.notes || "standby"}</div>
                  </div>
                  {can("schedule", "delete") && (
                    <Button variant="ghost" size="icon" onClick={() => del(s.id)} data-testid={`del-sched-${s.id}`}>
                      <Trash2 className="w-4 h-4 text-red-500" />
                    </Button>
                  )}
                </div>
              ))}
            </div>
          </Card>
        ))}
        {list.length === 0 && <div className="text-muted-foreground text-center py-10">No schedules yet.</div>}
      </div>
    </div>
  );
}
