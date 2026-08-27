import { useEffect, useState } from "react";
import api from "@/lib/api";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
import { BarChart, Bar, XAxis, YAxis, ResponsiveContainer, Tooltip, Legend } from "recharts";
import { toast } from "sonner";
import { Download, Mail, MessageCircle, FileSpreadsheet, Presentation } from "lucide-react";

export default function MonthlyReport() {
  const [customers, setCustomers] = useState([]);
  const [cid, setCid] = useState("");
  const [month, setMonth] = useState(new Date().toISOString().slice(0, 7));
  const [data, setData] = useState(null);
  const [emailOpen, setEmailOpen] = useState(false);
  const [email, setEmail] = useState({ subject: "", message: "", override_recipient: "" });

  useEffect(() => { api.get("/customers").then((r) => { setCustomers(r.data); if (r.data.length) setCid(r.data[0].id); }); }, []);

  const generate = async () => {
    if (!cid || !month) return;
    try {
      const { data } = await api.get(`/monthly-report?customer_id=${cid}&month=${month}`);
      setData(data);
    } catch (e) { toast.error(e?.response?.data?.detail || "Failed"); }
  };

  const downloadPdf = async () => {
    try {
      const r = await api.get(`/monthly-report/pdf?customer_id=${cid}&month=${month}`, { responseType: "blob" });
      const u = URL.createObjectURL(r.data);
      const a = document.createElement("a"); a.href = u; a.download = `monthly-${month}.pdf`; a.click();
      URL.revokeObjectURL(u);
    } catch { toast.error("Download failed"); }
  };

  const sendEmail = async () => {
    try {
      await api.post("/monthly-report/email", { customer_id: cid, month, body: email });
      toast.success("Email sent");
      setEmailOpen(false);
    } catch (e) { toast.error(e?.response?.data?.detail || "Failed"); }
  };

  const downloadFile = async (url, filename) => {
    try {
      const r = await api.get(url, { responseType: "blob" });
      const u = URL.createObjectURL(r.data);
      const a = document.createElement("a"); a.href = u; a.download = filename; a.click();
      URL.revokeObjectURL(u);
    } catch (e) { toast.error(e?.response?.data?.detail || "Download failed"); }
  };

  const sendWA = async () => {
    const phone = data?.customer?.phone;
    if (!phone) return toast.error("Klien tidak memiliki nomor WA");
    try {
      await api.post("/monthly-report/whatsapp", { customer_id: cid, month, body: {} });
      toast.success(`WA terkirim ke ${phone}`);
    } catch (e) { toast.error(e?.response?.data?.detail || "Failed"); }
  };

  return (
    <div className="space-y-4" data-testid="monthly-page">
      <div>
        <h1 className="font-display text-3xl font-extrabold">Monthly Report</h1>
        <p className="text-muted-foreground text-sm">Comprehensive report per client with pest historical chart, work realization, attendance and photos.</p>
      </div>

      <Card className="p-4 flex flex-wrap gap-3 items-end">
        <div>
          <Label>Client</Label>
          <Select value={cid} onValueChange={setCid}>
            <SelectTrigger className="w-64" data-testid="mr-customer"><SelectValue placeholder="Select client" /></SelectTrigger>
            <SelectContent>{customers.map((c) => <SelectItem key={c.id} value={c.id}>{c.company_name}</SelectItem>)}</SelectContent>
          </Select>
        </div>
        <div>
          <Label>Month</Label>
          <Input type="month" value={month} onChange={(e) => setMonth(e.target.value)} data-testid="mr-month" />
        </div>
        <Button onClick={generate} className="bg-primary text-primary-foreground" data-testid="mr-generate">Generate</Button>
        {data && <Button onClick={downloadPdf} variant="outline" data-testid="mr-pdf"><Download className="w-4 h-4 mr-1" />PDF</Button>}
        {data && <Button onClick={() => downloadFile(`/monthly-report/excel?customer_id=${cid}&month=${month}`, `monthly-${month}.xlsx`)} variant="outline" data-testid="mr-excel"><FileSpreadsheet className="w-4 h-4 mr-1" />Excel</Button>}
        {data && <Button onClick={() => downloadFile(`/monthly-report/pptx?customer_id=${cid}&month=${month}`, `monthly-${month}.pptx`)} variant="outline" data-testid="mr-pptx"><Presentation className="w-4 h-4 mr-1" />PPTX</Button>}
        {data && <Button onClick={() => { setEmail({ subject: `Monthly Report - ${month}`, message: "", override_recipient: data.customer?.email || "" }); setEmailOpen(true); }} className="bg-teal-600 hover:bg-teal-700 text-white" data-testid="mr-email"><Mail className="w-4 h-4 mr-1" />Send Email</Button>}
        {data && <Button onClick={() => sendWA()} className="bg-emerald-600 hover:bg-emerald-700 text-white" data-testid="mr-wa"><MessageCircle className="w-4 h-4 mr-1" />Send WA</Button>}
      </Card>

      {data && (
        <>
          <Card className="p-5">
            <div className="text-xs font-mono uppercase text-primary mb-3">Client Information</div>
            <div className="grid grid-cols-2 gap-3 text-sm">
              <div><b>Company:</b> {data.customer.company_name}</div>
              <div><b>Project:</b> {data.customer.project_name || "—"}</div>
              <div className="col-span-2"><b>Address:</b> {data.customer.address}</div>
              <div><b>Contract Start:</b> {data.customer.contract_start || "—"}</div>
              <div><b>Period:</b> {data.month}</div>
            </div>
          </Card>

          <Card className="p-5">
            <div className="text-xs font-mono uppercase text-primary mb-3">Pest Findings — Historical (first report → current)</div>
            <ResponsiveContainer width="100%" height={300}>
              <BarChart data={data.historical_pest}>
                <XAxis dataKey="month" tick={{ fontSize: 11 }} />
                <YAxis tick={{ fontSize: 11 }} />
                <Tooltip />
                <Legend />
                <Bar dataKey="F" fill="#F59E0B" />
                <Bar dataKey="M" fill="#3B82F6" />
                <Bar dataKey="C" fill="#EF4444" />
                <Bar dataKey="R" fill="#8B5CF6" />
                <Bar dataKey="A" fill="#10B981" />
                <Bar dataKey="O" fill="#64748B" />
              </BarChart>
            </ResponsiveContainer>
          </Card>

          <Card className="p-5">
            <div className="text-xs font-mono uppercase text-primary mb-3">Work Realization ({data.month})</div>
            <table className="w-full text-sm">
              <thead><tr className="text-left text-xs uppercase text-muted-foreground border-b border-border"><th className="p-2">Date</th><th className="p-2">Technician</th><th className="p-2">Scope</th><th className="p-2">Recommendation</th></tr></thead>
              <tbody>
                {data.service_reports.map((s) => (
                  <tr key={s.id} className="border-b border-border/50"><td className="p-2 font-mono text-xs">{s.date}</td><td className="p-2">{s.technician_name}</td><td className="p-2">{s.scope_of_area}</td><td className="p-2 text-xs text-muted-foreground">{s.recommendation}</td></tr>
                ))}
              </tbody>
            </table>
            {data.service_reports.length === 0 && <div className="text-muted-foreground text-center py-4">No service reports this month.</div>}
          </Card>

          <Card className="p-5">
            <div className="text-xs font-mono uppercase text-primary mb-3">Attendance ({data.month})</div>
            <table className="w-full text-sm">
              <thead><tr className="text-left text-xs uppercase text-muted-foreground border-b border-border"><th className="p-2">Technician</th><th className="p-2">Date</th><th className="p-2">Check-in</th><th className="p-2">Check-out</th><th className="p-2">Hours</th></tr></thead>
              <tbody>
                {data.attendance.map((a) => (
                  <tr key={a.id} className="border-b border-border/50"><td className="p-2">{a.user_name}</td><td className="p-2 font-mono text-xs">{a.date}</td><td className="p-2 font-mono text-xs">{a.timestamp?.slice(11, 19)}</td><td className="p-2 font-mono text-xs">{a.checkout_timestamp?.slice(11, 19) || "—"}</td><td className="p-2">{a.working_hours ?? "—"}</td></tr>
                ))}
              </tbody>
            </table>
            {data.attendance.length === 0 && <div className="text-muted-foreground text-center py-4">No attendance records.</div>}
          </Card>
        </>
      )}

      <Dialog open={emailOpen} onOpenChange={setEmailOpen}>
        <DialogContent>
          <DialogHeader><DialogTitle>Send Monthly Report</DialogTitle></DialogHeader>
          <div className="space-y-3">
            <div><Label>Recipient</Label><Input value={email.override_recipient} onChange={(e) => setEmail({ ...email, override_recipient: e.target.value })} data-testid="em-to" /></div>
            <div><Label>Subject</Label><Input value={email.subject} onChange={(e) => setEmail({ ...email, subject: e.target.value })} data-testid="em-subject" /></div>
            <div><Label>Message (plaintext, embedded in template)</Label><Textarea rows={5} value={email.message} onChange={(e) => setEmail({ ...email, message: e.target.value })} data-testid="em-msg" /></div>
            <Button onClick={sendEmail} className="w-full bg-primary text-primary-foreground" data-testid="em-send"><Mail className="w-4 h-4 mr-2" />Send</Button>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}
