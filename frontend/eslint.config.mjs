import { defineConfig, globalIgnores } from "eslint/config";
import nextVitals from "eslint-config-next/core-web-vitals";
import nextTs from "eslint-config-next/typescript";

const eslintConfig = defineConfig([
  ...nextVitals,
  ...nextTs,
  {
    // ESLint 10 removed context.getFilename(); eslint-plugin-react still
    // auto-detects React version via that API unless we pin it here.
    settings: {
      react: { version: "19" },
    },
  },
  // Override default ignores of eslint-config-next.
  globalIgnores([
    // Default ignores of eslint-config-next:
    ".next/**",
    "out/**",
    "build/**",
    "next-env.d.ts",
    // ESLint 10 + eslint-plugin-react crash on flat-config files (getFilename removed).
    "eslint.config.mjs",
    "postcss.config.mjs",
    "vitest.config.ts",
  ]),
]);

export default eslintConfig;
