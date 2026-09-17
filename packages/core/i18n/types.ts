// Keep type union broad for compile compat; runtime only uses "en".
export type SupportedLocale = "en" | "zh-Hans" | "ko" | "ja" | "fr";

export const SUPPORTED_LOCALES: SupportedLocale[] = ["en"];
export const DEFAULT_LOCALE: SupportedLocale = "en";

export type LocaleResources = Record<string, Record<string, unknown>>;

export interface LocaleAdapter {
  getUserChoice(): string | null;
  getSystemPreferences(): string[];
  persist(locale: SupportedLocale): void;
}
