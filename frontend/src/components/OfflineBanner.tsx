import { useEffect, useState } from "react";
import { WifiOff } from "lucide-react";

export function OfflineBanner() {
  const [offline, setOffline] = useState(!navigator.onLine);
  useEffect(() => {
    const on = () => setOffline(false);
    const off = () => setOffline(true);
    window.addEventListener("online", on);
    window.addEventListener("offline", off);
    return () => {
      window.removeEventListener("online", on);
      window.removeEventListener("offline", off);
    };
  }, []);
  if (!offline) return null;
  return (
    <div className="fixed inset-x-0 top-0 z-50 flex items-center justify-center gap-2 bg-amber-500/90 py-1.5 text-sm font-medium text-black">
      <WifiOff size={15} /> You are offline. AI requests require an Internet connection.
    </div>
  );
}
