import { createContext, useCallback, useContext, useEffect, useState, type ReactNode } from "react";

export type Theme = "light" | "dark" | "amoled" | "system";

interface ThemeState {
  theme: Theme;
  setTheme: (t: Theme) => void;
}

const ThemeContext = createContext<ThemeState | null>(null);
const STORAGE_KEY = "nvai-theme";

function apply(theme: Theme) {
  const root = document.documentElement;
  const prefersDark = window.matchMedia("(prefers-color-scheme: dark)").matches;
  const effective = theme === "system" ? (prefersDark ? "dark" : "light") : theme;
  root.classList.toggle("dark", effective === "dark" || effective === "amoled");
  root.classList.toggle("amoled", effective === "amoled");
}

export function ThemeProvider({ children }: { children: ReactNode }) {
  const [theme, setThemeState] = useState<Theme>(
    () => (localStorage.getItem(STORAGE_KEY) as Theme) || "amoled",
  );

  useEffect(() => {
    apply(theme);
    const mq = window.matchMedia("(prefers-color-scheme: dark)");
    const handler = () => theme === "system" && apply("system");
    mq.addEventListener("change", handler);
    return () => mq.removeEventListener("change", handler);
  }, [theme]);

  const setTheme = useCallback((t: Theme) => {
    setThemeState(t);
    localStorage.setItem(STORAGE_KEY, t);
  }, []);

  return <ThemeContext.Provider value={{ theme, setTheme }}>{children}</ThemeContext.Provider>;
}

export function useTheme(): ThemeState {
  const ctx = useContext(ThemeContext);
  if (!ctx) throw new Error("useTheme must be used within ThemeProvider");
  return ctx;
}
