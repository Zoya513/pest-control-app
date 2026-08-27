import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "@/lib/auth";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card } from "@/components/ui/card";
import { Eye, EyeOff, Shield, Bug } from "lucide-react";
import { toast } from "sonner";

export default function Login() {
  const nav = useNavigate();
  const { login } = useAuth();
  const [email, setEmail] = useState("admin@pestops.com");
  const [password, setPassword] = useState("Admin@123");
  const [show, setShow] = useState(false);
  const [loading, setLoading] = useState(false);

  const submit = async (e) => {
    e.preventDefault();
    setLoading(true);
    try {
      await login(email, password);
      toast.success("Welcome back!");
      nav("/");
    } catch (err) {
      toast.error(err?.response?.data?.detail || "Login failed");
    } finally { setLoading(false); }
  };

  const preset = (r) => {
    if (r === "admin") { setEmail("admin@pestops.com"); setPassword("Admin@123"); }
    else if (r === "tech") { setEmail("technician@pestops.com"); setPassword("Tech@123"); }
    else if (r === "client") { setEmail("client@pestops.com"); setPassword("Client@123"); }
    else if (r === "dev") { setEmail("developer@pestops.com"); setPassword("Dev@123"); }
  };

  return (
    <div className="min-h-screen bg-slate-950 relative overflow-hidden">
      {/* Ambient */}
      <div className="absolute inset-0 grain" />
      <div className="absolute -top-40 -left-40 w-96 h-96 bg-emerald-500/10 blur-3xl rounded-full" />
      <div className="absolute -bottom-40 -right-40 w-96 h-96 bg-teal-500/10 blur-3xl rounded-full" />

      <div className="relative z-10 min-h-screen grid md:grid-cols-2">
        {/* Left brand panel */}
        <div className="hidden md:flex flex-col justify-between p-12 border-r border-slate-800/60">
          <div className="flex items-center gap-3">
            <div className="w-11 h-11 rounded-xl bg-gradient-to-br from-emerald-500 to-teal-600 grid place-items-center shadow-lg shadow-emerald-500/20">
              <Bug className="w-6 h-6 text-slate-950" />
            </div>
            <div>
              <div className="font-display text-xl font-bold text-white">PestOps Pro</div>
              <div className="text-xs font-mono uppercase tracking-widest text-emerald-400/80">Field Ops Command</div>
            </div>
          </div>

          <div>
            <h1 className="font-display text-5xl font-extrabold text-white leading-tight">
              Command your <br /><span className="text-emerald-400">field operations</span>
            </h1>
            <p className="mt-6 text-slate-400 text-base max-w-md leading-relaxed">
              Real-time GPS, geofenced attendance, pest findings, and service reports — one command center for your entire pest control workforce.
            </p>
            <div className="mt-8 grid grid-cols-3 gap-4 max-w-md">
              {["Live GPS", "Geofence", "Reports"].map((t) => (
                <div key={t} className="p-3 rounded-lg border border-slate-800 bg-slate-900/50">
                  <div className="text-xs font-mono uppercase text-emerald-400">{t}</div>
                </div>
              ))}
            </div>
          </div>

          <div className="text-xs text-slate-600 font-mono">© 2026 PestOps Pro · Enterprise Field Operations Platform</div>
        </div>

        {/* Right form panel */}
        <div className="flex items-center justify-center p-6 md:p-12">
          <Card className="w-full max-w-md p-8 bg-slate-900/70 border-slate-800 backdrop-blur">
            <div className="flex items-center gap-2 mb-6 md:hidden">
              <div className="w-9 h-9 rounded-lg bg-emerald-500 grid place-items-center">
                <Bug className="w-5 h-5 text-slate-950" />
              </div>
              <div className="font-display font-bold text-white">PestOps Pro</div>
            </div>
            <h2 className="font-display text-2xl font-bold text-white">Sign in to your workspace</h2>
            <p className="text-sm text-slate-400 mt-1">Authorized personnel only.</p>

            <form onSubmit={submit} className="mt-6 space-y-4">
              <div>
                <Label htmlFor="email" className="text-slate-300 text-xs font-mono uppercase tracking-wider">Email</Label>
                <Input id="email" data-testid="login-email" type="email" value={email}
                       onChange={(e) => setEmail(e.target.value)}
                       className="mt-1.5 bg-slate-950 border-slate-800 text-white placeholder:text-slate-600" required />
              </div>
              <div>
                <Label htmlFor="pw" className="text-slate-300 text-xs font-mono uppercase tracking-wider">Password</Label>
                <div className="relative mt-1.5">
                  <Input id="pw" data-testid="login-password" type={show ? "text" : "password"} value={password}
                         onChange={(e) => setPassword(e.target.value)}
                         className="bg-slate-950 border-slate-800 text-white pr-10" required />
                  <button type="button" onClick={() => setShow(!show)} className="absolute right-2 top-1/2 -translate-y-1/2 text-slate-500 hover:text-emerald-400">
                    {show ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                  </button>
                </div>
              </div>

              <Button type="submit" data-testid="login-submit" disabled={loading}
                      className="w-full h-11 bg-emerald-500 hover:bg-emerald-600 text-slate-950 font-semibold">
                {loading ? "Authenticating..." : "Sign In"}
              </Button>

              <div className="flex items-center gap-2 text-xs text-slate-500 pt-2">
                <div className="h-px bg-slate-800 flex-1" /> Quick demo access <div className="h-px bg-slate-800 flex-1" />
              </div>
              <div className="grid grid-cols-2 gap-2">
                <Button type="button" data-testid="preset-admin" variant="outline" onClick={() => preset("admin")}
                        className="border-slate-800 bg-slate-950 hover:bg-slate-800 text-slate-300">
                  <Shield className="w-4 h-4 mr-2 text-emerald-400" /> Admin
                </Button>
                <Button type="button" data-testid="preset-tech" variant="outline" onClick={() => preset("tech")}
                        className="border-slate-800 bg-slate-950 hover:bg-slate-800 text-slate-300">
                  <Bug className="w-4 h-4 mr-2 text-teal-400" /> Technician
                </Button>
                <Button type="button" data-testid="preset-client" variant="outline" onClick={() => preset("client")}
                        className="border-slate-800 bg-slate-950 hover:bg-slate-800 text-slate-300">
                  <Shield className="w-4 h-4 mr-2 text-amber-400" /> Client
                </Button>
                <Button type="button" data-testid="preset-dev" variant="outline" onClick={() => preset("dev")}
                        className="border-slate-800 bg-slate-950 hover:bg-slate-800 text-slate-300">
                  <Shield className="w-4 h-4 mr-2 text-purple-400" /> Developer
                </Button>
              </div>
            </form>
          </Card>
        </div>
      </div>
    </div>
  );
}
