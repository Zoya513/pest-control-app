import { useEffect, useState } from "react";
import api from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { Textarea } from "@/components/ui/textarea";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Download, Mail, Package } from "lucide-react";
import { toast } from "sonner";

async function download(url, filename) {
  try {
    const r = await api.get(url, { responseType: "blob" });
    const u = URL.createObjectURL(r.data);
    const a = document.createElement("a"); a.href = u; a.download = filename; a.click();
    URL.revokeObjectURL(u);
  } catch (e) { toast.error("Download failed"); }
}

export default function ServiceReports() {
  const { can } = useAuth();
  const [list, setList] = useState([]);
  const [customers, setCustomers] = useState([]);
  const [techs, setTechs] = useState([]);
  const [filter, setFilter] = useState({ customer_id: "", technician_id: "", date_from: "", date_to: "" });
  const [emailOpen, setEmailOpen] = useState(false);
  const [emailFor, setEmailFor] = useState(null);
  const [email, setEmail] = useState({ subject: "", message: "", override_recipient: "" });

  const load = () => {
    const q = new URLSearchParams();
    Object.entries(filter).forEach(([k, v]) => { if (v) q.set(k, v); });
    api.get(`/service-reports${q.toString() ? "?" + q : ""}`).then((r) => setList(r.data));
  };
  useEffect(() => {
    load();
    if (can("customers", "view")) api.get("/customers").then((r) => setCustomers(r.data));
    if (can("members", "view")) api.get("/users").then((r) => setTechs(r.data.filter((u) => u.role === "technician")));
    // eslint-disable-next-line
  }, []);

  const openEmail = (sr) => {
    setEmailFor(sr);
    setEmail({ subject: `Service Report ${sr.report_number}`, message: "", override_recipient: "" });
    setEmailOpen(true);
  };

  const sendEmail = async () => {
    try {
      await api.post(`/service-reports/${emailFor.id}/email`, email);
      toast.success("Email sent");
      setEmailOpen(false);
    } catch (e) { toast.error(e?.response?.data?.detail || "Failed"); }
  };

  const bulkZip = () => {
    const q = new URLSearchParams();
    Object.entries(filter).forEach(([k, v]) => { if (v && k !== "technician_id") q.set(k, v); });
    download(`/service-reports/export/zip${q.toString() ? "?" + q : ""}`, "service_reports.zip");
  };

  return (
    <div className="space-y-4" data-testid="sr-page">
      <h1 className="font-display text-3xl font-extrabold">Service Reports</h1>

      <Card className="p-4 flex flex-wrap gap-3 items-end">
        {can("customers", "view") && (
          <div><Label>Client</Label>
            <Select value={filter.customer_id || "__all__"} onValueChange={(v) => setFilter({ ...filter, customer_id: v === "__all__" ? "" : v })}>
              <SelectTrigger className="w-48" data-testid="filter-cust"><SelectValue placeholder="All" /></SelectTrigger>
              <SelectContent><SelectItem value="__all__">All</SelectItem>{customers.map((c) => <SelectItem key={c.id} value={c.id}>{c.company_name}</SelectItem>)}</SelectContent>
            </Select>
          </div>
        )}
        {can("members", "view") && (
          <div><Label>Technician</Label>
            <Select value={filter.technician_id || "__all__"} onValueChange={(v) => setFilter({ ...filter, technician_id: v === "__all__" ? "" : v })}>
              <SelectTrigger className="w-48"><SelectValue placeholder="All" /></SelectTrigger>
              <SelectContent><SelectItem value="__all__">All</SelectItem>{techs.map((t) => <SelectItem key={t.id} value={t.id}>{t.full_name}</SelectItem>)}</SelectContent>
            </Select>
          </div>
        )}
        <div><Label>From</Label><Input type="date" value={filter.date_from} onChange={(e) => setFilter({ ...filter, date_from: e.target.value })} /></div>
        <div><Label>To</Label><Input type="date" value={filter.date_to} onChange={(e) => setFilter({ ...filter, date_to: e.target.value })} /></div>
        <Button onClick={load} className="bg-primary text-primary-foreground" data-testid="sr-apply">Apply</Button>
        <Button variant="outline" onClick={() => { setFilter({ customer_id: "", technician_id: "", date_from: "", date_to: "" }); setTimeout(load, 50); }}>Reset</Button>
        {can("service_reports", "export") && <Button onClick={bulkZip} className="bg-teal-600 hover:bg-teal-700 text-white" data-testid="sr-bulk-zip"><Package className="w-4 h-4 mr-1" />Bulk ZIP</Button>}
      </Card>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
        {list.length === 0 && <div className="text-muted-foreground col-span-full text-center py-10">No service reports.</div>}
        {list.map((s) => (
          <Card key={s.id} className="p-4">
            <div className="flex justify-between">
              <div className="font-mono text-xs text-primary">{s.report_number}</div>
              <Badge className="bg-primary/10 text-primary border-primary/30">{s.status}</Badge>
            </div>
            <div className="mt-2 text-sm font-medium">{s.customer_name}</div>
            <div className="text-xs text-muted-foreground">{s.technician_name} · {s.date} {s.time}</div>
            <div className="text-xs text-muted-foreground mt-1">{s.scope_of_area}</div>
            <div className="mt-2 text-[10px] font-mono text-muted-foreground">Pest: {(s.pest_findings || []).map((f) => `${f.code}=${f.quantity}`).join(" ") || "—"}</div>
            <div className="mt-3 flex gap-2">
              <Button size="sm" className="flex-1 bg-primary text-primary-foreground" onClick={() => download(`/service-reports/${s.id}/pdf`, `${s.report_number}.pdf`)} data-testid={`sr-pdf-${s.id}`}>
                <Download className="w-4 h-4 mr-1" />PDF
              </Button>
              {can("email", "create") && (
                <Button size="sm" variant="outline" onClick={() => openEmail(s)} data-testid={`sr-email-${s.id}`}><Mail className="w-4 h-4" /></Button>
              )}
            </div>
          </Card>
        ))}
      </div>

      <Dialog open={emailOpen} onOpenChange={setEmailOpen}>
        <DialogContent>
          <DialogHeader><DialogTitle>Email Service Report</DialogTitle></DialogHeader>
          <div className="space-y-3">
            <div><Label>Recipient (leave blank to use client email)</Label><Input value={email.override_recipient} onChange={(e) => setEmail({ ...email, override_recipient: e.target.value })} data-testid="sr-em-to" /></div>
            <div><Label>Subject</Label><Input value={email.subject} onChange={(e) => setEmail({ ...email, subject: e.target.value })} data-testid="sr-em-subject" /></div>
            <div><Label>Message</Label><Textarea rows={5} value={email.message} onChange={(e) => setEmail({ ...email, message: e.target.value })} data-testid="sr-em-msg" /></div>
            <Button onClick={sendEmail} className="w-full bg-primary text-primary-foreground" data-testid="sr-em-send"><Mail className="w-4 h-4 mr-2" />Send</Button>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}
