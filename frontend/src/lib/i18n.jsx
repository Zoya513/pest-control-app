import { createContext, useContext, useState, useEffect } from "react";

const DICT = {
  en: {
    "app.name": "PestOps Pro",
    "nav.home": "Home", "nav.tasks": "Tasks", "nav.attendance": "Attendance",
    "nav.service_reports": "Service Reports", "nav.schedule": "Schedule",
    "nav.travel": "Travel", "nav.map": "Live Map", "nav.customers": "Clients",
    "nav.members": "Members", "nav.leave": "Leave", "nav.reports": "Reports",
    "nav.monthly": "Monthly Report", "nav.audit": "Audit Log",
    "nav.settings": "Settings", "nav.branding": "Branding",
    "action.create": "Create", "action.save": "Save", "action.cancel": "Cancel",
    "action.delete": "Delete", "action.edit": "Edit", "action.apply": "Apply",
    "action.reset": "Reset", "action.export": "Export", "action.send_email": "Send Email",
    "action.download_pdf": "Download PDF", "action.download_zip": "Download ZIP",
    "filter.date_from": "From", "filter.date_to": "To",
    "filter.technician": "Technician", "filter.customer": "Client",
    "filter.period": "Period", "filter.all": "All",
    "status.pending": "Pending", "status.overdue": "Overdue",
    "status.in_progress": "In Progress", "status.completed": "Completed",
    "auth.signin": "Sign In", "auth.email": "Email", "auth.password": "Password",
  },
  id: {
    "app.name": "PestOps Pro",
    "nav.home": "Beranda", "nav.tasks": "Tugas", "nav.attendance": "Absensi",
    "nav.service_reports": "Service Report", "nav.schedule": "Jadwal",
    "nav.travel": "Perjalanan", "nav.map": "Lokasi", "nav.customers": "Pelanggan",
    "nav.members": "Anggota", "nav.leave": "Cuti", "nav.reports": "Laporan",
    "nav.monthly": "Laporan Bulanan", "nav.audit": "Audit Log",
    "nav.settings": "Pengaturan", "nav.branding": "Branding",
    "action.create": "Buat", "action.save": "Simpan", "action.cancel": "Batal",
    "action.delete": "Hapus", "action.edit": "Ubah", "action.apply": "Terapkan",
    "action.reset": "Reset", "action.export": "Ekspor", "action.send_email": "Kirim Email",
    "action.download_pdf": "Unduh PDF", "action.download_zip": "Unduh ZIP",
    "filter.date_from": "Dari", "filter.date_to": "Sampai",
    "filter.technician": "Teknisi", "filter.customer": "Klien",
    "filter.period": "Periode", "filter.all": "Semua",
    "status.pending": "Belum Dikerjakan", "status.overdue": "Ditunda",
    "status.in_progress": "Berjalan", "status.completed": "Selesai",
    "auth.signin": "Masuk", "auth.email": "Email", "auth.password": "Kata Sandi",
  },
};

const I18nCtx = createContext({ t: (k) => k, lang: "en", setLang: () => {} });

export function I18nProvider({ children }) {
  const [lang, setLang] = useState(() => localStorage.getItem("pest_lang") || "id");
  useEffect(() => localStorage.setItem("pest_lang", lang), [lang]);
  const t = (key) => DICT[lang]?.[key] || DICT.en[key] || key;
  return <I18nCtx.Provider value={{ t, lang, setLang }}>{children}</I18nCtx.Provider>;
}

export const useI18n = () => useContext(I18nCtx);
