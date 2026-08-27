import { useEffect, useState } from "react";
import api from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { Label } from "@/components/ui/label";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Plus, Search, Shield } from "lucide-react";
import { toast } from "sonner";

const MODULES = ["tasks", "customers", "service_reports", "attendance", "location", "members", "leave", "reports", "schedule", "travel", "settings", "audit_log"];
const ACTIONS = ["view", "create", "update", "delete", "approve", "export", "track", "manage"];

export default function Members() {
  const { can } = useAuth();
  const [users, setUsers] = useState([]);
  const [q, setQ] = useState("");
  const [open, setOpen] = useState(false);
  const [permOpen, setPermOpen] = useState(false);
  const [selected, setSelected] = useState(null);
  const [form, setForm] = useState({ email: "", password: "", full_name: "", role: "technician", position: "", phone: "", id_number: "", address: "", leave_quota: 12 });

  const load = () => api.get(`/users${q ? "?q=" + encodeURIComponent(q) : ""}`).then((r) => setUsers(r.data));
  useEffect(() => { load(); /* eslint-disable-next-line */ }, [q]);

  const create = async () => {
    try { await api.post("/users", form); toast.success("Member created"); setOpen(false); load(); }
    catch (e) { toast.error(e?.response?.data?.detail || "Failed"); }
  };

  const togglePerm = (mod, act) => {
    const p = { ...(selected.permissions || {}) };
    p[mod] = { ...(p[mod] || {}) };
    p[mod][act] = !p[mod][act];
    setSelected({ ...selected, permissions: p });
  };

  const savePerms = async () => {
    try {
      await api.put(`/users/${selected.id}`, { permissions: selected.permissions });
      toast.success("Permissions updated");
      setPermOpen(false);
      load();
    } catch (e) { toast.error(e?.response?.data?.detail || "Failed"); }
  };

  return (
    <div className="space-y-4" data-testid="members-page">
      <div className="flex flex-col sm:flex-row justify-between gap-3">
        <div><h1 className="font-display text-3xl font-extrabold text-white">Team Members</h1><p className="text-slate-400 text-sm">Manage users and per-user permissions.</p></div>
        {can("members", "create") && (
          <Dialog open={open} onOpenChange={setOpen}>
            <DialogTrigger asChild><Button data-testid="btn-add-member" className="bg-emerald-500 hover:bg-emerald-600 text-slate-950"><Plus className="w-4 h-4 mr-1" /> Add Member</Button></DialogTrigger>
            <DialogContent className="bg-slate-900 border-slate-800 text-white max-w-lg">
              <DialogHeader><DialogTitle>New Member</DialogTitle></DialogHeader>
              <div className="grid grid-cols-2 gap-3">
                <div><Label>Full Name</Label><Input value={form.full_name} onChange={(e) => setForm({ ...form, full_name: e.target.value })} className="bg-slate-950 border-slate-800" data-testid="mem-name" /></div>
                <div><Label>Email</Label><Input value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} className="bg-slate-950 border-slate-800" data-testid="mem-email" /></div>
                <div><Label>Password</Label><Input type="password" value={form.password} onChange={(e) => setForm({ ...form, password: e.target.value })} className="bg-slate-950 border-slate-800" data-testid="mem-password" /></div>
                <div><Label>Role</Label>
                  <Select value={form.role} onValueChange={(v) => setForm({ ...form, role: v })}>
                    <SelectTrigger className="bg-slate-950 border-slate-800"><SelectValue /></SelectTrigger>
                    <SelectContent className="bg-slate-900 border-slate-800"><SelectItem value="technician">Technician</SelectItem><SelectItem value="admin">Admin</SelectItem></SelectContent>
                  </Select>
                </div>
                <div><Label>Position</Label><Input value={form.position} onChange={(e) => setForm({ ...form, position: e.target.value })} className="bg-slate-950 border-slate-800" /></div>
                <div><Label>Phone</Label><Input value={form.phone} onChange={(e) => setForm({ ...form, phone: e.target.value })} className="bg-slate-950 border-slate-800" /></div>
                <div><Label>ID/KTP</Label><Input value={form.id_number} onChange={(e) => setForm({ ...form, id_number: e.target.value })} className="bg-slate-950 border-slate-800" /></div>
                <div><Label>Leave Quota</Label><Input type="number" value={form.leave_quota} onChange={(e) => setForm({ ...form, leave_quota: +e.target.value })} className="bg-slate-950 border-slate-800" /></div>
                <div className="col-span-2"><Label>Address</Label><Input value={form.address} onChange={(e) => setForm({ ...form, address: e.target.value })} className="bg-slate-950 border-slate-800" /></div>
              </div>
              <Button onClick={create} className="bg-emerald-500 hover:bg-emerald-600 text-slate-950" data-testid="mem-save">Create</Button>
            </DialogContent>
          </Dialog>
        )}
      </div>

      <div className="relative max-w-md">
        <Search className="w-4 h-4 absolute left-3 top-3 text-slate-500" />
        <Input placeholder="Search by name or email..." value={q} onChange={(e) => setQ(e.target.value)} className="pl-9 bg-slate-900 border-slate-800" />
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
        {users.map((u) => (
          <Card key={u.id} className="p-4 bg-slate-900/60 border-slate-800">
            <div className="flex items-start justify-between">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-full bg-gradient-to-br from-emerald-500 to-teal-600 grid place-items-center text-slate-950 font-bold text-sm">
                  {(u.full_name || u.email).slice(0, 2).toUpperCase()}
                </div>
                <div>
                  <div className="font-display font-semibold text-white text-sm">{u.full_name}</div>
                  <div className="text-xs text-slate-500">{u.email}</div>
                </div>
              </div>
              <Badge className={u.role === "admin" ? "bg-emerald-500/10 text-emerald-400 border-emerald-500/30" : "bg-teal-500/10 text-teal-400 border-teal-500/30"}>{u.role}</Badge>
            </div>
            <div className="mt-3 text-xs text-slate-400 space-y-1">
              <div>Position: {u.position || "—"}</div>
              <div>Leave: {u.leave_used || 0} / {u.leave_quota}</div>
              <div>Status: <span className={u.status === "active" ? "text-emerald-400" : "text-red-400"}>{u.status}</span></div>
            </div>
            {can("members", "manage") && (
              <Button variant="outline" size="sm" className="mt-3 w-full border-slate-800 hover:bg-slate-800 text-slate-300"
                onClick={() => { setSelected(u); setPermOpen(true); }} data-testid={`perm-${u.id}`}>
                <Shield className="w-3 h-3 mr-1" /> Permissions
              </Button>
            )}
          </Card>
        ))}
      </div>

      <Dialog open={permOpen} onOpenChange={setPermOpen}>
        <DialogContent className="bg-slate-900 border-slate-800 text-white max-w-3xl max-h-[80vh] overflow-y-auto">
          <DialogHeader><DialogTitle>Permissions — {selected?.full_name}</DialogTitle></DialogHeader>
          <div className="overflow-x-auto">
            <table className="w-full text-xs">
              <thead><tr><th className="text-left p-2 text-slate-400">Module</th>{ACTIONS.map((a) => <th key={a} className="p-2 text-slate-400 font-mono uppercase">{a}</th>)}</tr></thead>
              <tbody>
                {MODULES.map((m) => (
                  <tr key={m} className="border-t border-slate-800">
                    <td className="p-2 text-white font-medium">{m}</td>
                    {ACTIONS.map((a) => (
                      <td key={a} className="p-2 text-center">
                        <input type="checkbox" checked={!!selected?.permissions?.[m]?.[a]} onChange={() => togglePerm(m, a)}
                          data-testid={`perm-${m}-${a}`} className="w-4 h-4 accent-emerald-500" />
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <Button onClick={savePerms} className="bg-emerald-500 hover:bg-emerald-600 text-slate-950" data-testid="perm-save">Save Permissions</Button>
        </DialogContent>
      </Dialog>
    </div>
  );
}
