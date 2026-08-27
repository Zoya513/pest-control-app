import { useEffect, useRef, useState } from "react";
import api from "@/lib/api";
import { Input } from "@/components/ui/input";
import { Loader2, MapPin } from "lucide-react";

/** Address autocomplete via backend geocode proxy. onSelect({display_name, lat, lng}) */
export default function AddressAutocomplete({ value, onChange, onSelect, placeholder = "Search address..." }) {
  const [results, setResults] = useState([]);
  const [loading, setLoading] = useState(false);
  const [open, setOpen] = useState(false);
  const timer = useRef(null);
  const boxRef = useRef(null);

  useEffect(() => {
    const outside = (e) => { if (boxRef.current && !boxRef.current.contains(e.target)) setOpen(false); };
    document.addEventListener("mousedown", outside);
    return () => document.removeEventListener("mousedown", outside);
  }, []);

  const search = (q) => {
    if (timer.current) clearTimeout(timer.current);
    if (!q || q.length < 3) { setResults([]); return; }
    timer.current = setTimeout(async () => {
      setLoading(true);
      try {
        const { data } = await api.get(`/geocode/search?q=${encodeURIComponent(q)}`);
        setResults(data); setOpen(true);
      } catch {} finally { setLoading(false); }
    }, 350);
  };

  return (
    <div ref={boxRef} className="relative">
      <div className="relative">
        <Input value={value || ""} onChange={(e) => { onChange(e.target.value); search(e.target.value); }}
               onFocus={() => results.length && setOpen(true)}
               placeholder={placeholder} className="bg-slate-950 border-slate-800 pr-8" data-testid="addr-input" />
        {loading && <Loader2 className="w-4 h-4 absolute right-2 top-3 animate-spin text-slate-500" />}
      </div>
      {open && results.length > 0 && (
        <div className="absolute z-50 mt-1 w-full bg-slate-900 border border-slate-800 rounded-md shadow-lg max-h-64 overflow-auto">
          {results.map((r, i) => (
            <button key={i} type="button" onClick={() => { onSelect(r); onChange(r.display_name); setOpen(false); }}
                    className="w-full text-left px-3 py-2 hover:bg-emerald-500/10 text-xs text-slate-300 flex items-start gap-2 border-b border-slate-800 last:border-0" data-testid={`addr-result-${i}`}>
              <MapPin className="w-3 h-3 text-emerald-400 mt-0.5 flex-shrink-0" />
              <div>
                <div className="text-white">{r.display_name}</div>
                <div className="text-[10px] text-slate-500 font-mono">{r.lat.toFixed(5)}, {r.lng.toFixed(5)}</div>
              </div>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
