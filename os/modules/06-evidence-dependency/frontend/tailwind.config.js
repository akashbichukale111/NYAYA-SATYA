/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        ink: {
          950: "#0b0e14",
          900: "#111520",
          800: "#191f2e",
          700: "#232a3d",
          600: "#333c54",
          500: "#4a5570",
        },
        parchment: {
          50: "#faf8f4",
          100: "#f3efe6",
          200: "#e6ddc9",
        },
        signal: {
          verified: "#2e7d5b",
          review: "#b8862b",
          conflict: "#a13d3d",
          unknown: "#6b7280",
        },
      },
      fontFamily: {
        serif: ["'Source Serif 4'", "Georgia", "serif"],
        sans: ["'Inter'", "system-ui", "sans-serif"],
        mono: ["'IBM Plex Mono'", "monospace"],
      },
    },
  },
  plugins: [],
}
