import { Toaster } from "sonner";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { AuthProvider, useAuth } from "@/lib/auth";
import { ThemeProvider } from "@/lib/theme";
import { I18nProvider } from "@/lib/i18n";
import Login from "@/pages/Login";
import Layout from "@/pages/Layout";
import Dashboard from "@/pages/Dashboard";
import Tasks from "@/pages/Tasks";
import TaskDetail from "@/pages/TaskDetail";
import Members from "@/pages/Members";
import Customers from "@/pages/Customers";
import LiveMap from "@/pages/LiveMap";
import Travel from "@/pages/Travel";
import Schedule from "@/pages/Schedule";
import ServiceReports from "@/pages/ServiceReports";
import CreateServiceReport from "@/pages/CreateServiceReport";
import Leave from "@/pages/Leave";
import Reports from "@/pages/Reports";
import MonthlyReport from "@/pages/MonthlyReport";
import Branding from "@/pages/Branding";
import AuditLog from "@/pages/AuditLog";
import Settings from "@/pages/Settings";
import Profile from "@/pages/Profile";
import Attendance from "@/pages/Attendance";
import "leaflet/dist/leaflet.css";
import "@/App.css";

function Guard({ children }) {
  const { user, ready } = useAuth();
  if (!ready) return <div className="min-h-screen grid place-items-center bg-background text-primary">Loading...</div>;
  if (!user) return <Navigate to="/login" replace />;
  return children;
}

function App() {
  return (
    <ThemeProvider>
      <I18nProvider>
        <BrowserRouter>
          <AuthProvider>
            <Toaster position="top-right" richColors />
            <Routes>
              <Route path="/login" element={<Login />} />
              <Route path="/" element={<Guard><Layout /></Guard>}>
                <Route index element={<Dashboard />} />
                <Route path="tasks" element={<Tasks />} />
                <Route path="tasks/:id" element={<TaskDetail />} />
                <Route path="members" element={<Members />} />
                <Route path="customers" element={<Customers />} />
                <Route path="map" element={<LiveMap />} />
                <Route path="travel" element={<Travel />} />
                <Route path="schedule" element={<Schedule />} />
                <Route path="service-reports" element={<ServiceReports />} />
                <Route path="service-reports/new/:taskId" element={<CreateServiceReport />} />
                <Route path="attendance" element={<Attendance />} />
                <Route path="leave" element={<Leave />} />
                <Route path="reports" element={<Reports />} />
                <Route path="monthly-report" element={<MonthlyReport />} />
                <Route path="branding" element={<Branding />} />
                <Route path="audit-log" element={<AuditLog />} />
                <Route path="settings" element={<Settings />} />
                <Route path="profile" element={<Profile />} />
              </Route>
            </Routes>
          </AuthProvider>
        </BrowserRouter>
      </I18nProvider>
    </ThemeProvider>
  );
}

export default App;
