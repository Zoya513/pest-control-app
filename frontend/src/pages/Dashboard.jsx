import { useEffect, useState } from "react";
import api from "@/lib/api";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { BarChart, Bar, XAxis, YAxis, ResponsiveContainer, Tooltip } from "recharts";
import { ClipboardList, CheckCircle2, AlertTriangle, Clock, Users, Camera, MapPin, Bug } from "lucide-react";
import { useAuth } from "@/lib/auth";

function Kpi({ icon: Icon, label, value, tone = "emerald", testid }) {
  const tones = {
    emerald: "text-emerald-400 border-emerald-500/20",
    amber: "text-amber-400 border-amber-500/20",
    red: "text-red-400 border-red-500/20",
    teal: "text-teal-400 border-teal-500/20",
    slate: "text-slate-300 border-slate-700",
  };
  return (
    <Card data-testid={testid} className={`p-5 bg-slate-900/60 border ${tones[tone]} relative overflow-hidden`}>
      <div className="flex justify-between items-start">
        <div>
          <div className="text-xs font-mono uppercase tracking-wider text-slate-500">{label}</div>
          <div className={`font-display text-3xl font-extrabold mt-2 ${tones[tone].split(" ")[0]}`}>{value}</div>
        </div>
        <Icon className={`w-6 h-6 ${tones[tone].split(" ")[0]}`} />
      </div>
    </Card>
  );
}

export default function Dashboard() {
  const { user } = useAuth();
  const [data, setData] = useState(null);
  useEffect(() => { api.get("/dashboard").then((r) => setData(r.data)).catch(() => {}); }, []);
  if (!data) return <div className="text-slate-500">Loading dashboard...</div>;

  const pestData = [
    { name: "Fly (F)", value: data.pest_findings_month.F, fill: "#F59E0B" },
    { name: "Mosquito (M)", value: data.pest_findings_month.M, fill: "#3B82F6" },
    { name: "Cockroach (C)", value: data.pest_findings_month.C, fill: "#EF4444" },
    { name: "Rodent (R)", value: data.pest_findings_month.R, fill: "#8B5CF6" },
    { name: "Ant (A)", value: data.pest_findings_month.A, fill: "#10B981" },
    { name: "Other (O)", value: data.pest_findings_month.O, fill: "#64748B" },
  ];

  return (
    <div className="space-y-6" data-testid="dashboard-page">
      <div>
        <h1 className="font-display text-3xl font-extrabold text-white">Command Center</h1>
        <p className="text-slate-400 text-sm mt-1">Welcome back, {user?.full_name}. Here is your operations snapshot.</p>
      </div>

      {/* Task KPIs */}
      <div>
        <div className="text-xs font-mono uppercase tracking-widest text-slate-500 mb-3">Task Summary</div>
        <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
          <Kpi testid="kpi-total-tasks" icon={ClipboardList} label="Total Tasks" value={data.tasks.total} tone="slate" />
          <Kpi testid="kpi-pending" icon={Clock} label="Pending" value={data.tasks.pending} tone="amber" />
          <Kpi testid="kpi-overdue" icon={AlertTriangle} label="Overdue" value={data.tasks.overdue} tone="red" />
          <Kpi testid="kpi-completed" icon={CheckCircle2} label="Completed" value={data.tasks.completed} tone="emerald" />
          <Kpi testid="kpi-today" icon={Clock} label="Today" value={data.tasks.today} tone="teal" />
        </div>
      </div>

      {data.technicians && (
        <div>
          <div className="text-xs font-mono uppercase tracking-widest text-slate-500 mb-3">Technician Fleet</div>
          <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
            <Kpi testid="kpi-tech-total" icon={Users} label="Total" value={data.technicians.total} tone="slate" />
            <Kpi testid="kpi-tech-online" icon={MapPin} label="Online" value={data.technicians.online} tone="emerald" />
            <Kpi icon={Users} label="Offline" value={data.technicians.offline} tone="red" />
            <Kpi icon={ClipboardList} label="On Task" value={data.technicians.on_task} tone="teal" />
            <Kpi icon={Users} label="Idle" value={data.technicians.not_on_task} tone="amber" />
          </div>
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <Card className="lg:col-span-2 p-5 bg-slate-900/60 border-slate-800">
          <div className="flex items-center justify-between mb-4">
            <div>
              <div className="font-display text-lg font-bold text-white">Pest Findings — This Month</div>
              <div className="text-xs text-slate-500 font-mono uppercase">Aggregated F / M / C / R / A / O</div>
            </div>
            <Bug className="w-5 h-5 text-emerald-400" />
          </div>
          <ResponsiveContainer width="100%" height={280}>
            <BarChart data={pestData}>
              <XAxis dataKey="name" stroke="#64748B" tick={{ fontSize: 11 }} />
              <YAxis stroke="#64748B" tick={{ fontSize: 11 }} />
              <Tooltip contentStyle={{ background: "#0F172A", border: "1px solid #1E293B", borderRadius: 6 }} />
              <Bar dataKey="value" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </Card>

        <Card className="p-5 bg-slate-900/60 border-slate-800">
          <div className="flex items-center gap-2 mb-4">
            <Camera className="w-4 h-4 text-emerald-400" />
            <div className="font-display text-base font-bold text-white">Today's Attendance</div>
          </div>
          <div className="space-y-3">
            <div className="flex items-center justify-between p-3 rounded-lg bg-slate-950/60 border border-slate-800">
              <span className="text-sm text-slate-300">Checked In</span>
              <Badge className="bg-emerald-500/10 text-emerald-400 border border-emerald-500/30">{data.attendance.checked_in}</Badge>
            </div>
            <div className="flex items-center justify-between p-3 rounded-lg bg-slate-950/60 border border-slate-800">
              <span className="text-sm text-slate-300">Checked Out</span>
              <Badge className="bg-teal-500/10 text-teal-400 border border-teal-500/30">{data.attendance.checked_out}</Badge>
            </div>
          </div>
        </Card>
      </div>
    </div>
  );
}
