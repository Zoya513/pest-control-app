import { useEffect, useRef, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import api from "@/lib/api";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import SignatureCanvas from "react-signature-canvas";
import { toast } from "sonner";
import { Save, Eraser, Trash2, ImagePlus } from "lucide-react";

const CODES = [
  { code: "F", name: "Fly" }, { code: "M", name: "Mosquito" }, { code: "C", name: "Cockroach" },
  { code: "R", name: "Rodent" }, { code: "A", name: "Ant" }, { code: "O", name: "Other" },
];

export default function CreateServiceReport() {
  const { taskId } = useParams();
  const nav = useNavigate();
  const [task, setTask] = useState(null);
  const [scope, setScope] = useState("");
  const [pestDesc, setPestDesc] = useState("");
  const [serviceArea, setServiceArea] = useState("");
  const [recommendation, setRecommendation] = useState("");
  const [findings, setFindings] = useState(CODES.map((c) => ({ code: c.code, description: "", quantity: 0 })));
  const [photos, setPhotos] = useState([]); // [{data, caption, path}]
  const [submitting, setSubmitting] = useState(false);
  const techSig = useRef(null);
  const clientSig = useRef(null);

  useEffect(() => { api.get(`/tasks/${taskId}`).then((r) => setTask(r.data)); }, [taskId]);

  const setF = (idx, key, val) => setFindings(findings.map((f, i) => i === idx ? { ...f, [key]: val } : f));

  const addPhoto = (files) => {
    Array.from(files || []).forEach((f) => {
      const r = new FileReader();
      r.onload = () => setPhotos((p) => [...p, { data: r.result, caption: "", path: null }]);
      r.readAsDataURL(f);
    });
  };

  const rmPhoto = (i) => setPhotos(photos.filter((_, idx) => idx !== i));
  const setCap = (i, v) => setPhotos(photos.map((p, idx) => idx === i ? { ...p, caption: v } : p));

  const uploadDataUrl = async (dataUrl, ext) => {
    const { data } = await api.post("/upload/base64", { data: dataUrl, ext });
    return data.path;
  };

  const submit = async () => {
    if (submitting) return;
    setSubmitting(true);
    try {
      // Upload signatures
      let techPath = null, clientPath = null;
      if (techSig.current && !techSig.current.isEmpty()) {
        techPath = await uploadDataUrl(techSig.current.toDataURL("image/png"), "png");
      }
      if (clientSig.current && !clientSig.current.isEmpty()) {
        clientPath = await uploadDataUrl(clientSig.current.toDataURL("image/png"), "png");
      }
      // Upload photos
      const uploaded = [];
      for (const p of photos) {
        if (p.path) { uploaded.push({ path: p.path, caption: p.caption }); continue; }
        const path = await uploadDataUrl(p.data, "jpg");
        uploaded.push({ path, caption: p.caption });
      }
      await api.post("/service-reports", {
        task_id: taskId,
        pest_description: pestDesc,
        scope_of_area: scope,
        service_area: serviceArea,
        recommendation,
        pest_findings: findings.filter((f) => f.quantity || f.description),
        technician_signature: techPath,
        client_signature: clientPath,
        photos: uploaded,
      });
      toast.success("Service Report submitted");
      nav("/service-reports");
    } catch (e) { toast.error(e?.response?.data?.detail || "Failed"); }
    finally { setSubmitting(false); }
  };

  if (!task) return <div className="text-muted-foreground">Loading task...</div>;

  return (
    <div className="space-y-4 max-w-4xl mx-auto" data-testid="sr-create-page">
      <div>
        <h1 className="font-display text-3xl font-extrabold">SERVICE REPORT</h1>
        <p className="text-muted-foreground text-sm">Complete the report for task: {task.work_target}</p>
      </div>

      <Card className="p-5">
        <div className="text-xs font-mono uppercase text-primary mb-3">Client Information (Auto)</div>
        <div className="grid grid-cols-2 gap-4 text-sm">
          <div><div className="text-[10px] uppercase font-mono text-muted-foreground">Company</div><div>{task.customer?.company_name}</div></div>
          <div><div className="text-[10px] uppercase font-mono text-muted-foreground">Contact</div><div>{task.customer?.contact_person}</div></div>
          <div className="col-span-2"><div className="text-[10px] uppercase font-mono text-muted-foreground">Location</div><div>{task.customer?.address}</div></div>
          <div><div className="text-[10px] uppercase font-mono text-muted-foreground">Technician</div><div>{task.technician?.full_name}</div></div>
          <div><div className="text-[10px] uppercase font-mono text-muted-foreground">Date · Time</div><div>{task.scheduled_date} · {task.scheduled_time}</div></div>
        </div>
      </Card>

      <Card className="p-5 space-y-3">
        <div><Label>Scope of Area</Label><Input value={scope} onChange={(e) => setScope(e.target.value)} placeholder="e.g. Unit Office" data-testid="sr-scope" /></div>
        <div><Label>Pest Description</Label><Textarea value={pestDesc} onChange={(e) => setPestDesc(e.target.value)} data-testid="sr-pest-desc" /></div>
        <div><Label>Inspection / Service Area</Label><Textarea value={serviceArea} onChange={(e) => setServiceArea(e.target.value)} data-testid="sr-service-area" /></div>
        <div><Label>Recommendation</Label><Textarea value={recommendation} onChange={(e) => setRecommendation(e.target.value)} data-testid="sr-recommendation" /></div>
      </Card>

      <Card className="p-5">
        <div className="text-xs font-mono uppercase text-primary mb-3">Kind of Pest / Pest Findings</div>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-xs font-mono uppercase text-muted-foreground border-b border-border">
                <th className="py-2 px-2 w-16">Code</th><th className="p-2 w-32">Type</th><th className="p-2">Description</th><th className="p-2 w-32">Quantity</th>
              </tr>
            </thead>
            <tbody>
              {findings.map((f, i) => (
                <tr key={f.code} className="border-b border-border/50">
                  <td className="py-2 px-2 font-mono text-primary font-bold">{f.code}</td>
                  <td className="p-2">{CODES[i].name}</td>
                  <td className="p-2"><Input value={f.description} onChange={(e) => setF(i, "description", e.target.value)} className="h-9" data-testid={`sr-pest-${f.code}-desc`} /></td>
                  <td className="p-2"><Input type="number" min="0" value={f.quantity} onChange={(e) => setF(i, "quantity", +e.target.value)} className="h-9" data-testid={`sr-pest-${f.code}-qty`} /></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>

      <Card className="p-5">
        <div className="flex justify-between items-center mb-3">
          <div className="text-xs font-mono uppercase text-primary">Photo Documentation</div>
          <label className="cursor-pointer inline-flex items-center gap-1 text-sm px-3 py-1.5 rounded-md bg-primary text-primary-foreground">
            <ImagePlus className="w-4 h-4" /> Add Photos
            <input type="file" multiple accept="image/*" className="hidden" onChange={(e) => addPhoto(e.target.files)} data-testid="sr-add-photo" />
          </label>
        </div>
        <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
          {photos.map((p, i) => (
            <div key={i} className="border border-border rounded-lg overflow-hidden">
              <img src={p.data} alt={`photo-${i}`} className="w-full h-32 object-cover" />
              <div className="p-2 space-y-1">
                <Input placeholder="Caption..." value={p.caption} onChange={(e) => setCap(i, e.target.value)} className="text-xs h-8" data-testid={`sr-caption-${i}`} />
                <Button size="sm" variant="ghost" className="w-full text-red-500" onClick={() => rmPhoto(i)} data-testid={`sr-rm-photo-${i}`}><Trash2 className="w-3 h-3 mr-1" />Remove</Button>
              </div>
            </div>
          ))}
        </div>
        {photos.length === 0 && <div className="text-center text-muted-foreground text-sm py-6">No photos yet — add work documentation photos.</div>}
      </Card>

      <div className="grid md:grid-cols-2 gap-4">
        <Card className="p-5">
          <div className="text-xs font-mono uppercase text-primary mb-3">Technician Signature</div>
          <div className="bg-white rounded"><SignatureCanvas ref={techSig} penColor="#0B0F17" canvasProps={{ className: "signature-canvas w-full", height: 140 }} /></div>
          <Button variant="outline" size="sm" onClick={() => techSig.current?.clear()} className="mt-2"><Eraser className="w-3 h-3 mr-1" />Clear</Button>
        </Card>
        <Card className="p-5">
          <div className="text-xs font-mono uppercase text-primary mb-3">Client Signature (Acknowledgement)</div>
          <div className="bg-white rounded"><SignatureCanvas ref={clientSig} penColor="#0B0F17" canvasProps={{ className: "signature-canvas w-full", height: 140 }} /></div>
          <Button variant="outline" size="sm" onClick={() => clientSig.current?.clear()} className="mt-2"><Eraser className="w-3 h-3 mr-1" />Clear</Button>
        </Card>
      </div>

      <Button onClick={submit} disabled={submitting} className="w-full bg-primary text-primary-foreground h-12 font-semibold" data-testid="sr-submit">
        <Save className="w-4 h-4 mr-2" />{submitting ? "Submitting..." : "Submit Service Report"}
      </Button>
    </div>
  );
}
