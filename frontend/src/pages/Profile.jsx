import { useAuth } from "@/lib/auth";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";

export default function Profile() {
  const { user } = useAuth();
  return (
    <div className="space-y-4 max-w-2xl" data-testid="profile-page">
      <h1 className="font-display text-3xl font-extrabold text-white">My Profile</h1>
      <Card className="p-6 bg-slate-900/60 border-slate-800">
        <div className="flex items-center gap-4">
          <div className="w-16 h-16 rounded-full bg-gradient-to-br from-emerald-500 to-teal-600 grid place-items-center text-slate-950 text-xl font-bold">
            {(user?.full_name || user?.email || "U").slice(0, 2).toUpperCase()}
          </div>
          <div>
            <div className="font-display text-xl font-bold text-white">{user?.full_name}</div>
            <div className="text-sm text-slate-500">{user?.email}</div>
            <Badge className="mt-1 bg-emerald-500/10 text-emerald-400 border-emerald-500/30 text-[10px] font-mono uppercase">{user?.role}</Badge>
          </div>
        </div>
        <div className="mt-6 grid grid-cols-2 gap-4 text-sm">
          <div><div className="text-[10px] uppercase font-mono text-slate-500">Position</div><div className="text-white">{user?.position || "—"}</div></div>
          <div><div className="text-[10px] uppercase font-mono text-slate-500">Phone</div><div className="text-white">{user?.phone || "—"}</div></div>
          <div><div className="text-[10px] uppercase font-mono text-slate-500">ID Number</div><div className="text-white">{user?.id_number || "—"}</div></div>
          <div><div className="text-[10px] uppercase font-mono text-slate-500">Address</div><div className="text-white">{user?.address || "—"}</div></div>
          <div><div className="text-[10px] uppercase font-mono text-slate-500">Leave Quota</div><div className="text-white">{user?.leave_used || 0} / {user?.leave_quota || 12}</div></div>
          <div><div className="text-[10px] uppercase font-mono text-slate-500">Status</div><div className="text-white">{user?.status}</div></div>
        </div>
      </Card>
    </div>
  );
}
