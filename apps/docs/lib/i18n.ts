import { defineI18n } from "fumadocs-core/i18n";

// English only.
export const i18n = defineI18n({
  languages: ["en"],
  defaultLanguage: "en",
  hideLocale: "default-locale",
});

export type Lang = (typeof i18n.languages)[number];
