import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import api from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Plus, MapPin, User, Calendar } from "lucide-react";
import { toast } from "sonner";

const STATUS_STYLES = {
  pending: "bg-amber-500/10 text-amber-400 border-amber-500/30",
  overdue: "bg-red-500/10 text-red-400 border-red-500/30",
  in_progress: "bg-teal-500/10 text-teal-400 border-teal-500/30",
  completed: "bg-emerald-500/10 text-emerald-400 border-emerald-500/30",
  cancelled: "bg-slate-500/10 text-slate-400 border-slate-500/30",
};

export default function Tasks() {
  const { can, user } = useAuth();
  const [tasks, setTasks] = useState([]);
  const [customers, setCustomers] = useState([]);
  const [techs, setTechs] = useState([]);
  const [filter, setFilter] = useState("all");
  const [open, setOpen] = useState(false);
  const [form, setForm] = useState({ customer_id: "", technician_id: "", scheduled_date: "", scheduled_time: "09:00", work_target: "", work_description: "" });

  const load = () => {
    const url = filter === "all" ? "/tasks" : `/tasks?filter=${filter}`;
    api.get(url).then((r) => setTasks(r.data));
  };
  useEffect(() => { load(); /* eslint-disable-next-line */ }, [filter]);
  useEffect(() => {
    if (can("customers", "view")) api.get("/customers").then((r) => setCustomers(r.data));
    if (can("members", "view")) api.get("/users").then((r) => setTechs(r.data.filter((u) => u.role === "technician")));
  // eslint-disable-next-line
  }, []);

  const create = async () => {
    try {
      await api.post("/tasks", form);
      toast.success("Task created");
      setOpen(false);
      setForm({ customer_id: "", technician_id: "", scheduled_date: "", scheduled_time: "09:00", work_target: "", work_description: "" });
      load();
    } catch (e) { toast.error(e?.response?.data?.detail || "Failed"); }
  };

  return (
    <div className="space-y-4" data-testid="tasks-page">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div>
          <h1 className="font-display text-3xl font-extrabold text-white">Work Orders</h1>
          <p className="text-slate-400 text-sm">Manage and track all field tasks.</p>
        </div>
        {can("tasks", "create") && (
          <Dialog open={open} onOpenChange={setOpen}>
            <DialogTrigger asChild>
              <Button data-testid="btn-create-task" className="bg-emerald-500 hover:bg-emerald-600 text-slate-950 font-semibold">
                <Plus className="w-4 h-4 mr-1" /> Buat Tugas
              </Button>
            </DialogTrigger>
            <DialogContent className="bg-slate-900 border-slate-800 text-white">
              <DialogHeader><DialogTitle>New Task</DialogTitle></DialogHeader>
              <div className="space-y-3">
                <div>
                  <Label>Customer</Label>
                  <Select value={form.customer_id} onValueChange={(v) => setForm({ ...form, customer_id: v })}>
                    <SelectTrigger data-testid="task-customer" className="bg-slate-950 border-slate-800"><SelectValue placeholder="Select customer" /></SelectTrigger>
                    <SelectContent className="bg-slate-900 border-slate-800">
                      {customers.map((c) => <SelectItem key={c.id} value={c.id}>{c.company_name}</SelectItem>)}
                    </SelectContent>
                  </Select>
                </div>
                <div>
                  <Label>Technician</Label>
                  <Select value={form.technician_id} onValueChange={(v) => setForm({ ...form, technician_id: v })}>
                    <SelectTrigger data-testid="task-technician" className="bg-slate-950 border-slate-800"><SelectValue placeholder="Assign to..." /></SelectTrigger>
                    <SelectContent className="bg-slate-900 border-slate-800">
                      {techs.map((t) => <SelectItem key={t.id} value={t.id}>{t.full_name}</SelectItem>)}
                    </SelectContent>
                  </Select>
                </div>
                <div className="grid grid-cols-2 gap-3">
                  <div><Label>Date</Label><Input type="date" value={form.scheduled_date} onChange={(e) => setForm({ ...form, scheduled_date: e.target.value })} className="bg-slate-950 border-slate-800" /></div>
                  <div><Label>Time</Label><Input type="time" value={form.scheduled_time} onChange={(e) => setForm({ ...form, scheduled_time: e.target.value })} className="bg-slate-950 border-slate-800" /></div>
                </div>
                <div><Label>Work Target</Label><Input data-testid="task-target" value={form.work_target} onChange={(e) => setForm({ ...form, work_target: e.target.value })} className="bg-slate-950 border-slate-800" placeholder="e.g. Pest control - kitchen area" /></div>
                <div><Label>Description</Label><Textarea value={form.work_description} onChange={(e) => setForm({ ...form, work_description: e.target.value })} className="bg-slate-950 border-slate-800" /></div>
                <Button data-testid="task-save" onClick={create} className="w-full bg-emerald-500 hover:bg-emerald-600 text-slate-950">Create Task</Button>
              </div>
            </DialogContent>
          </Dialog>
        )}
      </div>

      <Tabs value={filter} onValueChange={setFilter}>
        <TabsList className="bg-slate-900 border border-slate-800">
          {["all", "pending", "overdue", "in_progress", "completed"].map((k) => (
            <TabsTrigger key={k} value={k} data-testid={`filter-${k}`} className="data-[state=active]:bg-emerald-500 data-[state=active]:text-slate-950">
              {k === "all" ? "Semua" : k === "pending" ? "Belum Dikerjakan" : k === "overdue" ? "Ditunda" : k === "in_progress" ? "Berjalan" : "Selesai"}
            </TabsTrigger>
          ))}
        </TabsList>
      </Tabs>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
        {tasks.length === 0 && <div className="text-slate-500 col-span-full text-center py-10">No tasks yet.</div>}
        {tasks.map((t) => (
          <Card key={t.id} data-testid={`task-card-${t.id}`} className="p-4 bg-slate-900/60 border-slate-800 hover:border-emerald-500/40 transition">
            <div className="flex justify-between items-start">
              <Badge className={`${STATUS_STYLES[t.status]} font-mono uppercase text-[10px]`}>{t.status.replace("_", " ")}</Badge>
              <span className="text-[10px] font-mono text-slate-600">#{t.id.slice(0, 8)}</span>
            </div>
            <div className="mt-2 font-display font-bold text-white">{t.work_target}</div>
            <div className="text-xs text-slate-400 mt-1 line-clamp-2">{t.work_description}</div>
            <div className="mt-3 space-y-1 text-xs text-slate-400">
              <div className="flex items-center gap-1.5"><MapPin className="w-3 h-3" /> {t.customer?.company_name}</div>
              <div className="flex items-center gap-1.5"><User className="w-3 h-3" /> {t.technician?.full_name}</div>
              <div className="flex items-center gap-1.5"><Calendar className="w-3 h-3" /> {t.scheduled_date} · {t.scheduled_time}</div>
            </div>
            <div className="mt-3 flex flex-wrap gap-2">
              <Link to={`/tasks/${t.id}`} className="flex-1">
                <Button size="sm" variant="outline" className="w-full">Details</Button>
              </Link>
              {t.customer?.latitude && (
                <Button size="sm" variant="outline" onClick={() => window.open(`https://www.google.com/maps/dir/?api=1&destination=${t.customer.latitude},${t.customer.longitude}`, "_blank")} data-testid={`task-nav-${t.id}`}>
                  Navigate
                </Button>
              )}
              {t.technician_id === user?.id && t.status !== "completed" && (
                <Link to={`/service-reports/new/${t.id}`}>
                  <Button size="sm" className="bg-primary text-primary-foreground">Complete</Button>
                </Link>
              )}
            </div>
          </Card>
        ))}
      </div>
    </div>
  );
}
