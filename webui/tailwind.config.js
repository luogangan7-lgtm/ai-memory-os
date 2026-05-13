/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        "bg-deep": "#040810",
        "bg-base": "#0A1224",
        cyan: "#00f0d4",
        violet: "#9d50ff",
        emerald: "#00e676",
        amber: "#ffb347",
        red: "#ff4d6d",
        text: "#e4eeff",
        muted: "#6a7fa8",
        dim: "#3d4f6e",
      },
      fontFamily: {
        display: ["Syne", "sans-serif"],
        body: ["Syne", "sans-serif"],
        mono: ["Fira Code", "monospace"],
      },
    },
  },
  plugins: [],
};
