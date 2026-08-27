import { useEffect, useState } from "react";
import api from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Switch } from "@/components/ui/switch";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { toast } from "sonner";
import { Mail, Send, KeyRound, FileText, Zap } from "lucide-react";

const PLACEHOLDER_HELP = (
  <div className="text-xs text-muted-foreground mt-1">
    Placeholders: <code className="text-primary">{"{client_name}"}</code> <code className="text-primary">{"{period}"}</code> <code className="text-primary">{"{report_number}"}</code> <code className="text-primary">{"{company_name}"}</code> <code className="text-primary">{"{technician}"}</code>
  </div>
);

export default function EmailSettings() {
  const { user } = useAuth();
  const [s, setS] = useState(null);
  const [testTo, setTestTo] = useState("");
  const isEditor = user?.role === "admin" || user?.role === "developer";

  useEffect(() => { api.get("/email-settings").then((r) => { setS(r.data); setTestTo(user?.email || ""); }); }, [user]);

  const save = async () => {
    try {
      const payload = { ...s };
      delete payload.smtp_password_set;
      // if user did not enter new password, don't send it (existing password preserved)
      if (payload.smtp_password === undefined || payload.smtp_password === "") delete payload.smtp_password;
      const { data } = await api.put("/email-settings", payload);
      setS(data);
      toast.success("Email settings saved");
    } catch (e) { toast.error(e?.response?.data?.detail || "Failed"); }
  };

  const test = async () => {
    try {
      const { data } = await api.post("/email-settings/test", { to: testTo });
      if (data.ok) toast.success(`Test email sent via ${data.sent_via}`);
      else toast.error(`Failed: ${data.error}`);
    } catch (e) { toast.error(e?.response?.data?.detail || "Failed"); }
  };

  if (!s) return <div className="text-muted-foreground">Loading...</div>;

  return (
    <div className="space-y-4 max-w-4xl" data-testid="email-settings-page">
      <div className="flex items-center gap-2">
        <Mail className="w-6 h-6 text-primary" />
        <h1 className="font-display text-3xl font-extrabold">Email Integration</h1>
      </div>
      <p className="text-muted-foreground text-sm">Configure your company SMTP so all reports are sent from your own email. If SMTP is not configured, the system falls back to Emergent-managed email.</p>

      <Tabs defaultValue="smtp" className="space-y-4">
        <TabsList>
          <TabsTrigger value="smtp" data-testid="tab-smtp"><KeyRound className="w-4 h-4 mr-1" />SMTP</TabsTrigger>
          <TabsTrigger value="templates" data-testid="tab-templates"><FileText className="w-4 h-4 mr-1" />Templates</TabsTrigger>
          <TabsTrigger value="automation" data-testid="tab-automation"><Zap className="w-4 h-4 mr-1" />Automation</TabsTrigger>
          <TabsTrigger value="test" data-testid="tab-test"><Send className="w-4 h-4 mr-1" />Test</TabsTrigger>
        </TabsList>

        <TabsContent value="smtp">
          <Card className="p-5 space-y-3">
            <div className="flex items-center gap-2">
              <Badge className={s.smtp_password_set ? "bg-emerald-500/10 text-emerald-500 border-emerald-500/30" : "bg-amber-500/10 text-amber-500 border-amber-500/30"}>
                {s.smtp_password_set ? "SMTP Configured" : "Not Configured (using Emergent fallback)"}
              </Badge>
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div><Label>SMTP Host</Label><Input value={s.smtp_host || ""} onChange={(e) => setS({ ...s, smtp_host: e.target.value })} placeholder="smtp.gmail.com" disabled={!isEditor} data-testid="smtp-host" /></div>
              <div><Label>Port</Label><Input type="number" value={s.smtp_port || 587} onChange={(e) => setS({ ...s, smtp_port: +e.target.value })} placeholder="587" disabled={!isEditor} data-testid="smtp-port" /></div>
              <div><Label>Username</Label><Input value={s.smtp_username || ""} onChange={(e) => setS({ ...s, smtp_username: e.target.value })} placeholder="you@company.com" disabled={!isEditor} data-testid="smtp-user" /></div>
              <div>
                <Label>Password {s.smtp_password_set && <span className="text-xs text-emerald-500">(set — leave blank to keep)</span>}</Label>
                <Input type="password" value={s.smtp_password || ""} onChange={(e) => setS({ ...s, smtp_password: e.target.value })} placeholder={s.smtp_password_set ? "•••••••• (keep)" : "App password / SMTP secret"} disabled={!isEditor} data-testid="smtp-pw" />
              </div>
              <div><Label>From Email</Label><Input value={s.from_email || ""} onChange={(e) => setS({ ...s, from_email: e.target.value })} placeholder="reports@company.com" disabled={!isEditor} data-testid="from-email" /></div>
              <div><Label>From Display Name</Label><Input value={s.from_name || ""} onChange={(e) => setS({ ...s, from_name: e.target.value })} placeholder="Proteksi Pest Control" disabled={!isEditor} data-testid="from-name" /></div>
              <div><Label>Reply-To</Label><Input value={s.reply_to || ""} onChange={(e) => setS({ ...s, reply_to: e.target.value })} placeholder="info@company.com" disabled={!isEditor} data-testid="reply-to" /></div>
              <div className="flex items-center gap-2 pt-6"><Switch checked={!!s.smtp_use_tls} onCheckedChange={(v) => setS({ ...s, smtp_use_tls: v })} disabled={!isEditor} data-testid="smtp-tls" /><Label>Use STARTTLS (port 587 recommended)</Label></div>
              <div className="col-span-2"><Label>Email Signature (footer)</Label><Textarea rows={3} value={s.signature || ""} onChange={(e) => setS({ ...s, signature: e.target.value })} placeholder={"Best regards,\nProteksi Pest Control\n+62 21 ..."} disabled={!isEditor} data-testid="signature" /></div>
            </div>
            <div className="p-3 rounded-md bg-muted text-xs text-muted-foreground">
              <b className="text-primary">Gmail tip:</b> Use App Password (not your normal password). Go to <a className="text-primary underline" href="https://myaccount.google.com/apppasswords" target="_blank" rel="noreferrer">myaccount.google.com/apppasswords</a>, create one for "Mail", paste the 16-char code above. Host = <code>smtp.gmail.com</code>, Port = <code>587</code>, STARTTLS ON.
            </div>
            {isEditor && <Button onClick={save} className="bg-primary text-primary-foreground" data-testid="save-email"><Send className="w-4 h-4 mr-1" />Save Settings</Button>}
          </Card>
        </TabsContent>

        <TabsContent value="templates">
          <Card className="p-5 space-y-4">
            <div>
              <div className="text-sm font-semibold mb-1">Service Report Email</div>
              <Label>Subject</Label>
              <Input value={s.sr_subject_template || ""} onChange={(e) => setS({ ...s, sr_subject_template: e.target.value })} disabled={!isEditor} data-testid="sr-subject-tpl" />
              <Label className="mt-2 block">Body</Label>
              <Textarea rows={8} value={s.sr_body_template || ""} onChange={(e) => setS({ ...s, sr_body_template: e.target.value })} disabled={!isEditor} data-testid="sr-body-tpl" />
              {PLACEHOLDER_HELP}
            </div>
            <div className="border-t border-border pt-4">
              <div className="text-sm font-semibold mb-1">Monthly Report Email</div>
              <Label>Subject</Label>
              <Input value={s.mr_subject_template || ""} onChange={(e) => setS({ ...s, mr_subject_template: e.target.value })} disabled={!isEditor} data-testid="mr-subject-tpl" />
              <Label className="mt-2 block">Body</Label>
              <Textarea rows={10} value={s.mr_body_template || ""} onChange={(e) => setS({ ...s, mr_body_template: e.target.value })} disabled={!isEditor} data-testid="mr-body-tpl" />
              {PLACEHOLDER_HELP}
            </div>
            {isEditor && <Button onClick={save} className="bg-primary text-primary-foreground" data-testid="save-templates">Save Templates</Button>}
          </Card>
        </TabsContent>

        <TabsContent value="automation">
          <Card className="p-5 space-y-4">
            <div className="flex items-center gap-3">
              <Switch checked={!!s.auto_monthly_send} onCheckedChange={(v) => setS({ ...s, auto_monthly_send: v })} disabled={!isEditor} data-testid="auto-monthly" />
              <div>
                <Label className="text-base">Auto-send Monthly Report</Label>
                <div className="text-xs text-muted-foreground">System automatically sends previous-month Monthly Report to all active clients on the 1st of each month at 08:00 UTC.</div>
              </div>
            </div>
            <div className="p-3 rounded-md bg-muted text-xs text-muted-foreground">
              <b className="text-primary">How it works:</b> A scheduled cron calls the backend endpoint <code>POST /api/cron/auto-monthly-send</code>. If the toggle is ON, all active customers with a saved email receive the previous-month Monthly Report generated with your latest branding + template + SMTP configuration. All sends are logged to the Audit Log.
            </div>
            {isEditor && <Button onClick={save} className="bg-primary text-primary-foreground" data-testid="save-automation">Save Automation</Button>}
          </Card>
        </TabsContent>

        <TabsContent value="test">
          <Card className="p-5 space-y-3">
            <Label>Send Test Email To</Label>
            <Input value={testTo} onChange={(e) => setTestTo(e.target.value)} placeholder="your@email.com" data-testid="test-to" />
            <Button onClick={test} className="bg-teal-600 hover:bg-teal-700 text-white" data-testid="test-send"><Send className="w-4 h-4 mr-1" />Send Test</Button>
            <div className="text-xs text-muted-foreground">Verifies your SMTP config end-to-end. If SMTP fails, the system falls back to Emergent-managed email and reports which route was used.</div>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}
