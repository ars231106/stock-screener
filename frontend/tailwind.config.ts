import type { Config } from "tailwindcss";

const config: Config = {
  darkMode: "class",
  content: ["./src/**/*.{js,ts,jsx,tsx,mdx}"],
  theme: {
    extend: {
      colors: {
        // Carried over from the original stylesheet
        brand: {
          DEFAULT: "#625bff",
          light: "#7b5eff",
          dark: "#4d46d3",
        },
        ticker: {
          up: "#00b300",
          down: "#e5484d",
        },
        canvas: {
          light: "#f4f7fb",
          dark: "#0f1117",
        },
        surface: {
          light: "#ffffff",
          dark: "#171a23",
        },
      },
      fontFamily: {
        sans: ["Inter", "system-ui", "-apple-system", "Segoe UI", "sans-serif"],
      },
    },
  },
  plugins: [],
};

export default config;
