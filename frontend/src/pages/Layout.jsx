import { useEffect, useState } from "react";
import { NavLink, Outlet, useNavigate } from "react-router-dom";
import { useAuth } from "@/lib/auth";
import { useGPS } from "@/lib/gps";
import { useTheme } from "@/lib/theme";
import { useI18n } from "@/lib/i18n";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import {
  LayoutDashboard, ClipboardList, Users, MapPin, Navigation, Calendar,
  Building2, FileCheck2, BarChart3, ShieldCheck, LogOut, Bug, Palmtree,
  Settings as SettingsIcon, Camera, Menu, X, Sun, Moon, Globe, Paintbrush, FileBarChart, Mail
} from "lucide-react";

function NAV_ITEMS(t) {
  return [
    { to: "/", label: t("nav.home"), icon: LayoutDashboard, mod: null },
    { to: "/tasks", label: t("nav.tasks"), icon: ClipboardList, mod: "tasks" },
    { to: "/attendance", label: t("nav.attendance"), icon: Camera, mod: "attendance", hideForClient: true },
    { to: "/service-reports", label: t("nav.service_reports"), icon: FileCheck2, mod: "service_reports" },
    { to: "/schedule", label: t("nav.schedule"), icon: Calendar, mod: "schedule" },
    { to: "/travel", label: t("nav.travel"), icon: Navigation, mod: "travel", hideForClient: true },
    { to: "/map", label: t("nav.map"), icon: MapPin, mod: "location" },
    { to: "/customers", label: t("nav.customers"), icon: Building2, mod: "customers", hideForClient: true },
    { to: "/members", label: t("nav.members"), icon: Users, mod: "members", hideForClient: true },
    { to: "/leave", label: t("nav.leave"), icon: Palmtree, mod: "leave", hideForClient: true },
    { to: "/reports", label: t("nav.reports"), icon: BarChart3, mod: "reports" },
    { to: "/monthly-report", label: t("nav.monthly"), icon: FileBarChart, mod: "monthly_reports" },
    { to: "/branding", label: t("nav.branding"), icon: Paintbrush, mod: "branding" },
    { to: "/audit-log", label: t("nav.audit"), icon: ShieldCheck, mod: "audit_log" },
    { to: "/settings", label: t("nav.settings"), icon: SettingsIcon, mod: "settings" },
    { to: "/email-settings", label: "Email Integration", icon: Mail, mod: "settings" },
  ];
}

function GPSBadge({ status }) {
  const map = {
    active: { bg: "bg-emerald-500 text-slate-950", label: "GPS ACTIVE" },
    searching: { bg: "bg-amber-500 text-slate-950", label: "GPS SEARCHING" },
    limited: { bg: "bg-orange-500 text-white", label: "GPS LIMITED" },
    denied: { bg: "bg-red-600 text-white", label: "GPS DENIED" },
    disabled: { bg: "bg-slate-600 text-white", label: "GPS DISABLED" },
    error: { bg: "bg-red-500 text-white", label: "GPS ERROR" },
  };
  const c = map[status] || map.searching;
  return (
    <div data-testid="gps-status" className={`inline-flex items-center gap-2 px-2.5 py-1 rounded-full text-xs font-mono uppercase tracking-wider ${c.bg}`}>
      <span className="w-1.5 h-1.5 rounded-full bg-current pulse-dot" /> {c.label}
    </div>
  );
}

export default function Layout() {
  const { user, logout, can } = useAuth();
  const { theme, toggle } = useTheme();
  const { t, lang, setLang } = useI18n();
  const nav = useNavigate();
  const { status: gpsStatus, position } = useGPS(user?.role !== "client" && user?.role !== "developer");
  const [collapsed, setCollapsed] = useState(false);
  const [mobileOpen, setMobileOpen] = useState(false);
  const [now, setNow] = useState(new Date());

  useEffect(() => {
    const i = setInterval(() => setNow(new Date()), 1000);
    return () => clearInterval(i);
  }, []);

  const NAV = NAV_ITEMS(t);
  const isClient = user?.role === "client";
  const isDeveloper = user?.role === "developer";

  const items = NAV.filter((n) => {
    if (!n.mod) return true;
    if (isClient && n.hideForClient) return false;
    if (isDeveloper) return ["branding", "settings", "audit_log"].includes(n.mod) || !n.mod;
    return can(n.mod, "view") || user?.role === "admin";
  });

  return (
    <div className="min-h-screen bg-background text-foreground flex">
      <aside data-testid="sidebar" className={`fixed md:static inset-y-0 left-0 z-40 bg-card border-r border-border transition-all
                        ${mobileOpen ? "translate-x-0" : "-translate-x-full"} md:translate-x-0
                        ${collapsed ? "md:w-16" : "md:w-64"} w-64`}>
        <div className="h-16 flex items-center justify-between px-4 border-b border-border">
          <div className="flex items-center gap-2">
            <div className="w-9 h-9 rounded-lg bg-primary grid place-items-center">
              <Bug className="w-5 h-5 text-primary-foreground" />
            </div>
            {!collapsed && <div className="font-display font-bold text-sm">PestOps Pro</div>}
          </div>
          <button className="md:hidden text-muted-foreground" onClick={() => setMobileOpen(false)}><X className="w-5 h-5" /></button>
        </div>

        <nav className="p-2 space-y-0.5 overflow-y-auto h-[calc(100vh-4rem)]">
          {items.map((n) => (
            <NavLink key={n.to} to={n.to} end={n.to === "/"} onClick={() => setMobileOpen(false)}
                     data-testid={`nav-${n.to.replace(/\//g, "") || "home"}`}
                     className={({ isActive }) => `sidebar-item flex items-center gap-3 px-3 py-2.5 rounded-md text-sm border-l-2 border-transparent ${isActive ? "active" : "text-muted-foreground"}`}>
              <n.icon className="w-4 h-4 flex-shrink-0" />
              {!collapsed && <span>{n.label}</span>}
            </NavLink>
          ))}
        </nav>
      </aside>

      <div className="flex-1 flex flex-col min-w-0">
        <header className="h-16 border-b border-border bg-card/60 backdrop-blur flex items-center px-4 md:px-6 gap-3 sticky top-0 z-30">
          <button className="md:hidden" onClick={() => setMobileOpen(true)}><Menu className="w-5 h-5" /></button>
          <button className="hidden md:block text-muted-foreground hover:text-primary" onClick={() => setCollapsed(!collapsed)}>
            <Menu className="w-5 h-5" />
          </button>

          <div className="flex-1 flex items-center gap-3">
            {!isClient && !isDeveloper && <GPSBadge status={gpsStatus} />}
            {position && !isClient && !isDeveloper && <span className="hidden sm:inline text-xs font-mono text-muted-foreground">
              {position.latitude.toFixed(4)}, {position.longitude.toFixed(4)}
            </span>}
          </div>

          <div className="hidden sm:flex flex-col items-end text-xs">
            <div className="font-mono text-primary">{now.toLocaleTimeString("en-GB")}</div>
            <div className="text-muted-foreground">{now.toLocaleDateString(lang === "id" ? "id-ID" : "en-GB", { weekday: "short", day: "2-digit", month: "short", year: "numeric" })}</div>
          </div>

          {/* Theme + Language */}
          <Button variant="ghost" size="icon" onClick={toggle} data-testid="theme-toggle" title="Toggle theme">
            {theme === "dark" ? <Sun className="w-4 h-4" /> : <Moon className="w-4 h-4" />}
          </Button>
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button variant="ghost" size="icon" data-testid="lang-toggle" title="Language">
                <Globe className="w-4 h-4" />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end">
              <DropdownMenuItem onClick={() => setLang("id")} data-testid="lang-id">Bahasa Indonesia {lang === "id" && "✓"}</DropdownMenuItem>
              <DropdownMenuItem onClick={() => setLang("en")} data-testid="lang-en">English {lang === "en" && "✓"}</DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>

          <button onClick={() => nav("/profile")} data-testid="topbar-profile"
                  className="flex items-center gap-2 px-2 py-1.5 rounded-lg hover:bg-muted">
            <div className="w-8 h-8 rounded-full bg-gradient-to-br from-emerald-500 to-teal-600 grid place-items-center text-slate-950 font-bold text-xs">
              {(user?.full_name || user?.email || "U").slice(0, 2).toUpperCase()}
            </div>
            <div className="hidden sm:block text-left">
              <div className="text-xs font-semibold">{user?.full_name || user?.email}</div>
              <div className="text-[10px] font-mono uppercase text-primary">{user?.role}</div>
            </div>
          </button>

          <Button variant="ghost" size="sm" onClick={logout} data-testid="btn-logout" className="text-muted-foreground hover:text-red-500">
            <LogOut className="w-4 h-4" />
          </Button>
        </header>

        <main className="flex-1 p-4 md:p-6 overflow-y-auto">
          <Outlet />
        </main>
      </div>

      {mobileOpen && <div className="fixed inset-0 bg-black/60 z-30 md:hidden" onClick={() => setMobileOpen(false)} />}
    </div>
  );
}
