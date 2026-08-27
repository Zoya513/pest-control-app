import { useEffect, useState } from "react";
import api from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
import { Plus, Search, Building2, ExternalLink } from "lucide-react";
import { toast } from "sonner";
import AddressAutocomplete from "@/components/AddressAutocomplete";

export default function Customers() {
  const { can } = useAuth();
  const [list, setList] = useState([]);
  const [q, setQ] = useState("");
  const [open, setOpen] = useState(false);
  const empty = { company_name: "", project_name: "", contact_person: "", phone: "", email: "", address: "", location_text: "", latitude: null, longitude: null, category: "Regular", contract_start: "", contract_end: "", client_email: "", client_password: "" };
  const [form, setForm] = useState(empty);
  const [enableClient, setEnableClient] = useState(false);

  const load = () => api.get(`/customers${q ? "?q=" + encodeURIComponent(q) : ""}`).then((r) => setList(r.data));
  useEffect(() => { load(); /* eslint-disable-next-line */ }, [q]);

  const create = async () => {
    try {
      const payload = { ...form };
      if (!enableClient) { payload.client_email = null; payload.client_password = null; }
      await api.post("/customers", payload);
      toast.success("Customer created");
      setOpen(false); setForm(empty); setEnableClient(false); load();
    } catch (e) { toast.error(e?.response?.data?.detail || "Failed"); }
  };

  return (
    <div className="space-y-4" data-testid="customers-page">
      <div className="flex flex-col sm:flex-row justify-between gap-3">
        <div><h1 className="font-display text-3xl font-extrabold">Clients</h1><p className="text-muted-foreground text-sm">Manage customer accounts and contracts.</p></div>
        {can("customers", "create") && (
          <Dialog open={open} onOpenChange={setOpen}>
            <DialogTrigger asChild><Button data-testid="btn-add-customer" className="bg-primary text-primary-foreground"><Plus className="w-4 h-4 mr-1" /> Add Client</Button></DialogTrigger>
            <DialogContent className="max-w-lg">
              <DialogHeader><DialogTitle>New Client</DialogTitle></DialogHeader>
              <div className="grid grid-cols-2 gap-3 max-h-[70vh] overflow-y-auto pr-2">
                <div className="col-span-2"><Label>Company Name *</Label><Input value={form.company_name} onChange={(e) => setForm({ ...form, company_name: e.target.value })} data-testid="cust-name" /></div>
                <div className="col-span-2"><Label>Project / Building Name</Label><Input value={form.project_name} onChange={(e) => setForm({ ...form, project_name: e.target.value })} placeholder="e.g. Gedung A / Head Office" /></div>
                <div><Label>Contact Person</Label><Input value={form.contact_person} onChange={(e) => setForm({ ...form, contact_person: e.target.value })} /></div>
                <div><Label>Phone</Label><Input value={form.phone} onChange={(e) => setForm({ ...form, phone: e.target.value })} /></div>
                <div className="col-span-2"><Label>Client Email (used for report delivery)</Label><Input value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} data-testid="cust-email" /></div>
                <div><Label>Category</Label><Input value={form.category} onChange={(e) => setForm({ ...form, category: e.target.value })} /></div>
                <div className="col-span-2">
                  <Label>Address (with auto-geocode)</Label>
                  <AddressAutocomplete value={form.address} onChange={(v) => setForm({ ...form, address: v })}
                    onSelect={(r) => setForm({ ...form, address: r.display_name, latitude: r.lat, longitude: r.lng })} />
                  {form.latitude && <div className="text-[10px] font-mono text-primary mt-1">Coordinates locked: {form.latitude.toFixed(5)}, {form.longitude.toFixed(5)}</div>}
                </div>
                <div><Label>Contract Start</Label><Input type="date" value={form.contract_start} onChange={(e) => setForm({ ...form, contract_start: e.target.value })} /></div>
                <div><Label>Contract End</Label><Input type="date" value={form.contract_end} onChange={(e) => setForm({ ...form, contract_end: e.target.value })} /></div>

                <div className="col-span-2 border-t border-border pt-3 space-y-2">
                  <label className="flex items-center gap-2 text-sm"><input type="checkbox" checked={enableClient} onChange={(e) => setEnableClient(e.target.checked)} data-testid="enable-client-login" className="accent-primary" /> Create client login account</label>
                  {enableClient && (
                    <div className="grid grid-cols-2 gap-3">
                      <div><Label>Client Login Email</Label><Input value={form.client_email} onChange={(e) => setForm({ ...form, client_email: e.target.value })} data-testid="client-email" /></div>
                      <div><Label>Password</Label><Input type="password" value={form.client_password} onChange={(e) => setForm({ ...form, client_password: e.target.value })} data-testid="client-pw" /></div>
                    </div>
                  )}
                </div>
              </div>
              <Button onClick={create} className="bg-primary text-primary-foreground" data-testid="cust-save">Create</Button>
            </DialogContent>
          </Dialog>
        )}
      </div>

      <div className="relative max-w-md">
        <Search className="w-4 h-4 absolute left-3 top-3 text-muted-foreground" />
        <Input placeholder="Search customer..." value={q} onChange={(e) => setQ(e.target.value)} className="pl-9" />
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
        {list.map((c) => (
          <Card key={c.id} className="p-4">
            <div className="flex items-start gap-3">
              <div className="w-10 h-10 rounded-lg bg-teal-500/10 grid place-items-center"><Building2 className="w-5 h-5 text-teal-500" /></div>
              <div className="flex-1 min-w-0">
                <div className="font-display font-semibold truncate">{c.company_name}</div>
                {c.project_name && <div className="text-xs text-primary truncate">{c.project_name}</div>}
                <div className="text-xs text-muted-foreground truncate">{c.contact_person} · {c.phone}</div>
              </div>
              <Badge className={c.status === "active" ? "bg-emerald-500/10 text-emerald-500 border-emerald-500/30" : "bg-slate-500/10 text-slate-400"}>{c.status}</Badge>
            </div>
            <div className="mt-3 text-xs text-muted-foreground space-y-1">
              <div className="line-clamp-2">{c.address}</div>
              <div>Contract: {c.contract_start || "—"} → {c.contract_end || "—"}</div>
              {c.latitude && <button onClick={() => window.open(`https://www.google.com/maps?q=${c.latitude},${c.longitude}`, "_blank")} className="text-primary text-xs flex items-center gap-1 hover:underline"><ExternalLink className="w-3 h-3" /> View on Map</button>}
            </div>
          </Card>
        ))}
      </div>
    </div>
  );
}
