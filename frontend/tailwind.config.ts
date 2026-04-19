import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./app/**/*.{ts,tsx}",
    "./components/**/*.{ts,tsx}",
    "./lib/**/*.{ts,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        risk: {
          high: "#dc2626",
          medium: "#d97706",
          low: "#16a34a",
        },
      },
    },
  },
  plugins: [],
};

export default config;
