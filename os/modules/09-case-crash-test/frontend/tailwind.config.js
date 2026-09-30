/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        brand: {
          bg: "#0B0F17",
          panel: "#111827",
          border: "#1F2937",
          accent: "#5EEAD4",
          warn: "#FBBF24",
          danger: "#F87171",
        },
      },
    },
  },
  plugins: [],
};
