import api from "@/lib/api";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { FileText, FileSpreadsheet } from "lucide-react";
import { toast } from "sonner";

async function download(url, filename) {
  try {
    const r = await api.get(url, { responseType: "blob" });
    const u = URL.createObjectURL(r.data);
    const a = document.createElement("a"); a.href = u; a.download = filename; a.click();
    URL.revokeObjectURL(u);
  } catch { toast.error("Export failed"); }
}

const REPORTS = [
  { key: "attendance", label: "Attendance Report", url: "/reports/attendance" },
  { key: "customers", label: "Customer Report", url: "/reports/customers" },
  { key: "employees", label: "Employee Data Report", url: "/reports/employees" },
];

export default function Reports() {
  return (
    <div className="space-y-4" data-testid="reports-page">
      <div><h1 className="font-display text-3xl font-extrabold text-white">Reports & Exports</h1><p className="text-slate-400 text-sm">Generate PDF or Excel exports of operational data.</p></div>
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
        {REPORTS.map((r) => (
          <Card key={r.key} className="p-5 bg-slate-900/60 border-slate-800">
            <div className="font-display font-bold text-white">{r.label}</div>
            <div className="text-xs text-slate-500 font-mono uppercase mt-1">Export options</div>
            <div className="flex gap-2 mt-4">
              <Button className="flex-1 bg-red-600 hover:bg-red-700 text-white" onClick={() => download(`${r.url}?format=pdf`, `${r.key}.pdf`)} data-testid={`export-pdf-${r.key}`}><FileText className="w-4 h-4 mr-1" />PDF</Button>
              <Button className="flex-1 bg-emerald-600 hover:bg-emerald-700 text-white" onClick={() => download(`${r.url}?format=excel`, `${r.key}.xlsx`)} data-testid={`export-excel-${r.key}`}><FileSpreadsheet className="w-4 h-4 mr-1" />Excel</Button>
            </div>
          </Card>
        ))}
      </div>
    </div>
  );
}
