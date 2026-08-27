import { useEffect, useState } from "react";
import api from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { toast } from "sonner";
import { Paintbrush } from "lucide-react";

export default function Branding() {
  const { user } = useAuth();
  const [b, setB] = useState({});
  useEffect(() => { api.get("/branding").then((r) => setB(r.data)); }, []);
  const isEditor = user?.role === "developer" || user?.role === "admin";

  const save = async () => {
    try { const { data } = await api.put("/branding", b); setB(data); toast.success("Branding updated"); }
    catch (e) { toast.error(e?.response?.data?.detail || "Failed"); }
  };

  const upload = async (e) => {
    const f = e.target.files?.[0]; if (!f) return;
    const reader = new FileReader();
    reader.onload = async () => {
      try {
        const { data } = await api.post("/upload/base64", { data: reader.result, ext: f.name.split(".").pop() });
        setB({ ...b, logo_path: data.path });
        toast.success("Logo uploaded");
      } catch { toast.error("Upload failed"); }
    };
    reader.readAsDataURL(f);
  };

  return (
    <div className="space-y-4 max-w-2xl" data-testid="branding-page">
      <div className="flex items-center gap-2">
        <Paintbrush className="w-6 h-6 text-primary" />
        <h1 className="font-display text-3xl font-extrabold">Application Branding</h1>
      </div>
      <p className="text-muted-foreground text-sm">Central branding used on reports, header, and emails. {!isEditor && "Read-only for your role."}</p>
      <Card className="p-6 space-y-4">
        <div>
          <Label>App Name</Label>
          <Input value={b.app_name || ""} onChange={(e) => setB({ ...b, app_name: e.target.value })} disabled={!isEditor} data-testid="br-app" />
        </div>
        <div>
          <Label>Company / PT Name</Label>
          <Input value={b.company_name || ""} onChange={(e) => setB({ ...b, company_name: e.target.value })} disabled={!isEditor} data-testid="br-name" />
        </div>
        <div>
          <Label>Company Address</Label>
          <Input value={b.company_address || ""} onChange={(e) => setB({ ...b, company_address: e.target.value })} disabled={!isEditor} data-testid="br-addr" />
        </div>
        <div className="grid grid-cols-2 gap-3">
          <div>
            <Label>Email</Label>
            <Input value={b.company_email || ""} onChange={(e) => setB({ ...b, company_email: e.target.value })} disabled={!isEditor} />
          </div>
          <div>
            <Label>Phone</Label>
            <Input value={b.company_phone || ""} onChange={(e) => setB({ ...b, company_phone: e.target.value })} disabled={!isEditor} />
          </div>
        </div>
        <div>
          <Label>Logo</Label>
          <Input type="file" accept="image/*" onChange={upload} disabled={!isEditor} data-testid="br-logo" />
          {b.logo_path && <div className="text-xs text-muted-foreground mt-1 font-mono">{b.logo_path}</div>}
        </div>
        {isEditor && <Button onClick={save} className="bg-primary text-primary-foreground" data-testid="br-save">Save Branding</Button>}
      </Card>
    </div>
  );
}
