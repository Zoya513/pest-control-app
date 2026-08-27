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
import { Plus, Check, X } from "lucide-react";
import { toast } from "sonner";

export default function Leave() {
  const { can } = useAuth();
  const [list, setList] = useState([]);
  const [open, setOpen] = useState(false);
  const [form, setForm] = useState({ leave_type: "Cuti", start_date: "", end_date: "", return_date: "", reason: "" });
  const load = () => api.get("/leave").then((r) => setList(r.data));
  useEffect(load, []);

  const create = async () => {
    try { await api.post("/leave", form); toast.success("Leave request submitted"); setOpen(false); load(); }
    catch (e) { toast.error(e?.response?.data?.detail || "Failed"); }
  };

  const decide = async (id, decision) => {
    try { await api.post(`/leave/${id}/decide`, { decision }); toast.success(`Request ${decision}`); load(); }
    catch (e) { toast.error(e?.response?.data?.detail || "Failed"); }
  };

  return (
    <div className="space-y-4" data-testid="leave-page">
      <div className="flex justify-between">
        <h1 className="font-display text-3xl font-extrabold text-white">Leave Requests</h1>
        {can("leave", "create") && (
          <Dialog open={open} onOpenChange={setOpen}>
            <DialogTrigger asChild><Button className="bg-emerald-500 hover:bg-emerald-600 text-slate-950" data-testid="leave-new"><Plus className="w-4 h-4 mr-1" />Ajukan Cuti</Button></DialogTrigger>
            <DialogContent className="bg-slate-900 border-slate-800 text-white">
              <DialogHeader><DialogTitle>New Leave Request</DialogTitle></DialogHeader>
              <div className="space-y-3">
                <div><Label>Type</Label>
                  <Select value={form.leave_type} onValueChange={(v) => setForm({ ...form, leave_type: v })}>
                    <SelectTrigger className="bg-slate-950 border-slate-800"><SelectValue /></SelectTrigger>
                    <SelectContent className="bg-slate-900 border-slate-800"><SelectItem value="Cuti">Cuti</SelectItem><SelectItem value="Izin">Izin</SelectItem></SelectContent>
                  </Select>
                </div>
                <div className="grid grid-cols-2 gap-3">
                  <div><Label>Start Date</Label><Input type="date" value={form.start_date} onChange={(e) => setForm({ ...form, start_date: e.target.value })} className="bg-slate-950 border-slate-800" data-testid="leave-start" /></div>
                  <div><Label>End Date</Label><Input type="date" value={form.end_date} onChange={(e) => setForm({ ...form, end_date: e.target.value })} className="bg-slate-950 border-slate-800" data-testid="leave-end" /></div>
                </div>
                <div><Label>Return Date</Label><Input type="date" value={form.return_date} onChange={(e) => setForm({ ...form, return_date: e.target.value })} className="bg-slate-950 border-slate-800" /></div>
                <div><Label>Reason</Label><Textarea value={form.reason} onChange={(e) => setForm({ ...form, reason: e.target.value })} className="bg-slate-950 border-slate-800" data-testid="leave-reason" /></div>
                <Button onClick={create} className="w-full bg-emerald-500 hover:bg-emerald-600 text-slate-950" data-testid="leave-submit">Submit</Button>
              </div>
            </DialogContent>
          </Dialog>
        )}
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
        {list.map((l) => (
          <Card key={l.id} className="p-4 bg-slate-900/60 border-slate-800">
            <div className="flex justify-between">
              <div>
                <div className="font-display font-semibold text-white">{l.user_name}</div>
                <div className="text-xs text-slate-500">{l.leave_type}</div>
              </div>
              <Badge className={l.status === "approved" ? "bg-emerald-500/10 text-emerald-400 border-emerald-500/30" : l.status === "rejected" ? "bg-red-500/10 text-red-400 border-red-500/30" : "bg-amber-500/10 text-amber-400 border-amber-500/30"}>{l.status}</Badge>
            </div>
            <div className="text-sm text-slate-300 mt-2">{l.start_date} → {l.end_date}</div>
            <div className="text-xs text-slate-400 mt-1">{l.reason}</div>
            {l.status === "pending" && can("leave", "approve") && (
              <div className="flex gap-2 mt-3">
                <Button size="sm" className="flex-1 bg-emerald-500 hover:bg-emerald-600 text-slate-950" onClick={() => decide(l.id, "approved")} data-testid={`leave-approve-${l.id}`}><Check className="w-3 h-3 mr-1" />Approve</Button>
                <Button size="sm" variant="outline" className="flex-1 border-red-500/30 text-red-400 hover:bg-red-500/10" onClick={() => decide(l.id, "rejected")} data-testid={`leave-reject-${l.id}`}><X className="w-3 h-3 mr-1" />Reject</Button>
              </div>
            )}
          </Card>
        ))}
      </div>
    </div>
  );
}
