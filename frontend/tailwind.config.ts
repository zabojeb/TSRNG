import type { Config } from "tailwindcss";

export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        brand: {
          yellow: "#FFB400",
          dark: "#1C1E25",
          light: "#F5F7FA",
        },
      },
    },
  },
  plugins: [],
} satisfies Config;
