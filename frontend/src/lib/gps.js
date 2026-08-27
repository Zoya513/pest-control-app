import { useEffect, useRef, useState } from "react";
import api from "./api";

/** GPS tracker: watches position, sends pings & heartbeats */
export function useGPS(enabled = true) {
  const [status, setStatus] = useState("searching"); // active|searching|limited|denied|error|disabled
  const [pos, setPos] = useState(null);
  const watchId = useRef(null);
  const lastPing = useRef(0);
  const lastHeartbeat = useRef(0);

  useEffect(() => {
    if (!enabled) return;
    if (!("geolocation" in navigator)) {
      setStatus("disabled");
      return;
    }
    setStatus("searching");
    watchId.current = navigator.geolocation.watchPosition(
      (p) => {
        setStatus("active");
        const cur = {
          latitude: p.coords.latitude,
          longitude: p.coords.longitude,
          accuracy: p.coords.accuracy,
          speed: p.coords.speed,
          heading: p.coords.heading,
          timestamp: p.timestamp,
        };
        setPos(cur);
        const now = Date.now();
        // ping every 4s
        if (now - lastPing.current > 4000) {
          lastPing.current = now;
          api.post("/gps/ping", cur).catch(() => {});
        }
      },
      (err) => {
        if (err.code === 1) setStatus("denied");
        else if (err.code === 2) setStatus("limited");
        else setStatus("error");
      },
      { enableHighAccuracy: true, maximumAge: 3000, timeout: 20000 }
    );

    // heartbeat every 30s
    const hb = setInterval(() => {
      const now = Date.now();
      lastHeartbeat.current = now;
      api.post("/heartbeat", {
        gps_status: status,
        latitude: pos?.latitude,
        longitude: pos?.longitude,
      }).catch(() => {});
    }, 30000);

    return () => {
      if (watchId.current != null) navigator.geolocation.clearWatch(watchId.current);
      clearInterval(hb);
    };
    // eslint-disable-next-line
  }, [enabled]);

  return { status, position: pos };
}
