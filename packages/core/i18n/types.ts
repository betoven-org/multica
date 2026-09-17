// Keep type union broad for compile compat with upstream locales.
export type SupportedLocale = "en" | "pt-BR" | "zh-Hans" | "ko" | "ja" | "fr";

export const SUPPORTED_LOCALES: SupportedLocale[] = ["en", "pt-BR"];
export const DEFAULT_LOCALE: SupportedLocale = "en";

export type LocaleResources = Record<string, Record<string, unknown>>;

export interface LocaleAdapter {
  getUserChoice(): string | null;
  getSystemPreferences(): string[];
  persist(locale: SupportedLocale): void;
}
