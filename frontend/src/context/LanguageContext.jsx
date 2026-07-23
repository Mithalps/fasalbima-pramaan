import { createContext, useContext, useState, useCallback, useMemo } from "react";
import en from "../i18n/en";
import kn from "../i18n/kn";

/**
 * LanguageContext
 *
 * Lightweight, dependency-free i18n. Holds the current interface language
 * ('en' | 'kn') and exposes a t(key, vars?) lookup function backed by two
 * plain JS dictionaries (i18n/en.js, i18n/kn.js).
 *
 * Keys are dot-paths into the dictionary, e.g. t('landing.heroTitle').
 * Values may contain {placeholders} for dynamic data, e.g.
 * t('success.messageWithClaim', { farmerName, cropType }) — placeholders
 * are the ONLY thing that gets interpolated; everything else is static
 * copy translated ahead of time in en.js / kn.js.
 *
 * If a key is missing in the active language, we fall back to English so
 * the UI never renders a blank string while kn.js is still catching up.
 */

const STORAGE_KEY = "fbp_ui_language";
const DICTIONARIES = { en, kn };

const LanguageContext = createContext(null);

function getInitialLanguage() {
  if (typeof window === "undefined") return "en";
  try {
    const stored = window.localStorage.getItem(STORAGE_KEY);
    if (stored === "en" || stored === "kn") return stored;
  } catch {
    // localStorage can be unavailable (e.g. private browsing) — default to 'en'.
  }
  return "en";
}

function resolveKey(dictionary, key) {
  return key
    .split(".")
    .reduce(
      (value, part) => (value && typeof value === "object" ? value[part] : undefined),
      dictionary
    );
}

function interpolate(template, vars) {
  if (!vars) return template;
  return template.replace(/\{(\w+)\}/g, (match, name) =>
    Object.prototype.hasOwnProperty.call(vars, name) ? String(vars[name]) : match
  );
}

export function LanguageProvider({ children }) {
  const [language, setLanguageState] = useState(getInitialLanguage);

  const setLanguage = useCallback((nextLanguage) => {
    if (nextLanguage !== "en" && nextLanguage !== "kn") return;
    setLanguageState(nextLanguage);
    try {
      window.localStorage.setItem(STORAGE_KEY, nextLanguage);
    } catch {
      // Non-fatal — the language just won't survive a full page reload.
    }
  }, []);

  const t = useCallback(
    (key, vars) => {
      const activeDictionary = DICTIONARIES[language] ?? DICTIONARIES.en;
      const value = resolveKey(activeDictionary, key) ?? resolveKey(DICTIONARIES.en, key);
      if (typeof value !== "string") return key;
      return interpolate(value, vars);
    },
    [language]
  );

  const value = useMemo(
    () => ({ language, setLanguage, t }),
    [language, setLanguage, t]
  );

  return (
    <LanguageContext.Provider value={value}>{children}</LanguageContext.Provider>
  );
}

export function useLanguage() {
  const context = useContext(LanguageContext);
  if (!context) {
    throw new Error("useLanguage must be used within a LanguageProvider");
  }
  return context;
}