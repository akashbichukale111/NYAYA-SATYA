import { createContext, useContext, useEffect, useState, type ReactNode } from "react";

interface Ctx {
  lowBandwidth: boolean;
  setLowBandwidth: (v: boolean) => void;
}

const LowBandwidthContext = createContext<Ctx | null>(null);

const STORAGE_KEY = "hre.low_bandwidth";

export function LowBandwidthProvider({ children }: { children: ReactNode }) {
  const [lowBandwidth, setLowBandwidth] = useState<boolean>(() => {
    try {
      return localStorage.getItem(STORAGE_KEY) === "1";
    } catch {
      return false;
    }
  });

  useEffect(() => {
    document.body.classList.toggle("low-bandwidth", lowBandwidth);
    try {
      localStorage.setItem(STORAGE_KEY, lowBandwidth ? "1" : "0");
    } catch {
      /* ignore storage errors (e.g. private browsing) */
    }
  }, [lowBandwidth]);

  return (
    <LowBandwidthContext.Provider value={{ lowBandwidth, setLowBandwidth }}>
      {children}
    </LowBandwidthContext.Provider>
  );
}

export function useLowBandwidth() {
  const ctx = useContext(LowBandwidthContext);
  if (!ctx) throw new Error("useLowBandwidth must be used within LowBandwidthProvider");
  return ctx;
}
