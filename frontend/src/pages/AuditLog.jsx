import { useEffect, useState } from "react";
import api from "@/lib/api";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { ShieldCheck } from "lucide-react";

export default function AuditLog() {
  const [logs, setLogs] = useState([]);
  useEffect(() => { api.get("/audit-logs").then((r) => setLogs(r.data)); }, []);
  return (
    <div className="space-y-4" data-testid="audit-page">
      <h1 className="font-display text-3xl font-extrabold text-white">Audit Trail</h1>
      <Card className="bg-slate-900/60 border-slate-800 divide-y divide-slate-800">
        {logs.map((l) => (
          <div key={l.id} className="p-4 flex items-start gap-3">
            <ShieldCheck className="w-4 h-4 text-emerald-400 mt-1" />
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2 flex-wrap">
                <span className="text-white text-sm font-medium">{l.user_name}</span>
                <Badge className="bg-emerald-500/10 text-emerald-400 border-emerald-500/30 text-[10px] font-mono uppercase">{l.action}</Badge>
                <Badge className="bg-slate-800 text-slate-300 text-[10px]">{l.module}</Badge>
              </div>
              <div className="text-xs text-slate-400 mt-1 font-mono truncate">record: {l.record_id?.slice(0, 12)}</div>
              {l.new_value && <div className="text-[11px] text-slate-500 mt-1 font-mono">→ {JSON.stringify(l.new_value).slice(0, 200)}</div>}
            </div>
            <div className="text-xs font-mono text-slate-500 whitespace-nowrap">{new Date(l.timestamp).toLocaleString()}</div>
          </div>
        ))}
        {logs.length === 0 && <div className="p-8 text-center text-slate-500">No audit entries yet.</div>}
      </Card>
    </div>
  );
}
