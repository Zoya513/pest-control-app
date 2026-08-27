import { useEffect, useRef, useState } from "react";
import api from "@/lib/api";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useGPS } from "@/lib/gps";
import { Camera, CheckCircle2, LogOut, MapPin, ExternalLink } from "lucide-react";
import { toast } from "sonner";

export default function Attendance() {
  const { position, status } = useGPS(true);
  const videoRef = useRef(null);
  const canvasRef = useRef(null);
  const [photo, setPhoto] = useState(null);
  const [streamOn, setStreamOn] = useState(false);
  const [history, setHistory] = useState([]);
  const [filter, setFilter] = useState({ date_from: "", date_to: "" });

  const load = () => {
    const q = new URLSearchParams();
    Object.entries(filter).forEach(([k, v]) => { if (v) q.set(k, v); });
    api.get(`/attendance${q.toString() ? "?" + q : ""}`).then((r) => setHistory(r.data));
  };
  useEffect(() => { load(); return () => stopCamera(); /* eslint-disable-next-line */ }, []);

  const startCamera = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ video: { facingMode: "user" }, audio: false });
      if (videoRef.current) { videoRef.current.srcObject = stream; setStreamOn(true); }
    } catch { toast.error("Camera unavailable"); }
  };
  const stopCamera = () => { const s = videoRef.current?.srcObject; if (s) s.getTracks().forEach((t) => t.stop()); setStreamOn(false); };
  const capture = () => {
    if (!videoRef.current) return;
    const c = canvasRef.current;
    c.width = videoRef.current.videoWidth; c.height = videoRef.current.videoHeight;
    c.getContext("2d").drawImage(videoRef.current, 0, 0);
    setPhoto(c.toDataURL("image/jpeg", 0.85));
    stopCamera();
  };

  const submit = async (type) => {
    if (!photo) return toast.error("Take a photo first");
    if (!position) return toast.error("GPS not available");
    try {
      const up = await api.post("/upload/base64", { data: photo, ext: "jpg" });
      if (type === "check_in") {
        await api.post("/attendance/checkin", { latitude: position.latitude, longitude: position.longitude, accuracy: position.accuracy, photo: up.data.path });
        toast.success("Checked in!");
      } else {
        const lastCi = history.find((h) => h.type === "check_in" && !h.checkout_id);
        if (!lastCi) return toast.error("No open check-in found");
        await api.post("/attendance/checkout", { latitude: position.latitude, longitude: position.longitude, accuracy: position.accuracy, photo: up.data.path, attendance_id: lastCi.id });
        toast.success("Checked out!");
      }
      setPhoto(null); load();
    } catch (e) { toast.error(e?.response?.data?.detail || "Failed"); }
  };

  const openMap = (lat, lng) => window.open(`https://www.google.com/maps?q=${lat},${lng}`, "_blank");

  return (
    <div className="space-y-4" data-testid="attendance-page">
      <h1 className="font-display text-3xl font-extrabold">Attendance</h1>

      <Card className="p-5">
        <div className="flex justify-between mb-3">
          <div className="text-sm text-muted-foreground">GPS: <span className="text-primary font-mono uppercase">{status}</span></div>
          {position && <div className="text-xs font-mono text-muted-foreground">{position.latitude.toFixed(4)}, {position.longitude.toFixed(4)}</div>}
        </div>

        <div className="grid md:grid-cols-2 gap-4">
          <div className="aspect-video bg-muted rounded-lg overflow-hidden relative border border-border">
            {photo ? <img src={photo} alt="capture" className="w-full h-full object-cover" /> :
              <video ref={videoRef} autoPlay playsInline muted className="w-full h-full object-cover" />}
            {!streamOn && !photo && <div className="absolute inset-0 grid place-items-center text-muted-foreground text-sm">Camera off</div>}
            <canvas ref={canvasRef} className="hidden" />
          </div>
          <div className="space-y-2">
            {!streamOn && !photo && <Button onClick={startCamera} className="w-full bg-primary text-primary-foreground" data-testid="att-start-cam"><Camera className="w-4 h-4 mr-2" />Start Camera</Button>}
            {streamOn && <Button onClick={capture} className="w-full bg-teal-500 hover:bg-teal-600 text-slate-950" data-testid="att-capture">Capture Photo</Button>}
            {photo && <Button variant="outline" onClick={() => { setPhoto(null); startCamera(); }} className="w-full">Retake</Button>}
            <Button onClick={() => submit("check_in")} disabled={!photo} className="w-full bg-emerald-600 hover:bg-emerald-700 text-white" data-testid="att-checkin"><CheckCircle2 className="w-4 h-4 mr-2" />Check In</Button>
            <Button onClick={() => submit("check_out")} disabled={!photo} className="w-full bg-red-600 hover:bg-red-700 text-white" data-testid="att-checkout"><LogOut className="w-4 h-4 mr-2" />Check Out</Button>
          </div>
        </div>
      </Card>

      <Card className="p-4 flex flex-wrap gap-3 items-end">
        <div><Label>From</Label><Input type="date" value={filter.date_from} onChange={(e) => setFilter({ ...filter, date_from: e.target.value })} data-testid="att-from" /></div>
        <div><Label>To</Label><Input type="date" value={filter.date_to} onChange={(e) => setFilter({ ...filter, date_to: e.target.value })} data-testid="att-to" /></div>
        <Button onClick={load} className="bg-primary text-primary-foreground" data-testid="att-apply">Apply</Button>
        <Button variant="outline" onClick={() => { setFilter({ date_from: "", date_to: "" }); setTimeout(load, 50); }}>Reset</Button>
      </Card>

      <Card className="p-4">
        <div className="text-xs font-mono uppercase text-primary mb-3">Recent History</div>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead><tr className="text-left text-xs uppercase text-muted-foreground border-b border-border">
              <th className="p-2">User</th><th className="p-2">Type</th><th className="p-2">Time</th><th className="p-2">Address</th><th className="p-2">Working Hrs</th><th className="p-2">Map</th>
            </tr></thead>
            <tbody>
              {history.map((h) => (
                <tr key={h.id} className="border-b border-border/50">
                  <td className="p-2">{h.user_name}</td>
                  <td className="p-2"><Badge className={`${h.type === "check_in" ? "bg-emerald-500/10 text-emerald-500" : "bg-red-500/10 text-red-500"} font-mono uppercase text-[10px]`}>{h.type}</Badge></td>
                  <td className="p-2 font-mono text-xs">{new Date(h.timestamp).toLocaleString()}</td>
                  <td className="p-2 text-xs max-w-xs truncate" title={h.address}>{h.address || `${h.latitude?.toFixed(4)}, ${h.longitude?.toFixed(4)}`}</td>
                  <td className="p-2 text-xs">{h.working_hours ? `${h.working_hours}h` : "—"}</td>
                  <td className="p-2"><Button size="icon" variant="ghost" onClick={() => openMap(h.latitude, h.longitude)} data-testid={`att-map-${h.id}`}><ExternalLink className="w-4 h-4 text-primary" /></Button></td>
                </tr>
              ))}
            </tbody>
          </table>
          {history.length === 0 && <div className="text-center text-muted-foreground py-6">No attendance records.</div>}
        </div>
      </Card>
    </div>
  );
}
