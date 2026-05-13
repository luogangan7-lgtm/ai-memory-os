/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        "bg-deep": "#030A15",
        "bg-base": "#050D1A",
        cyan: "#00E5FF",
        violet: "#7C3AED",
        emerald: "#00C897",
        amber: "#F59E0B",
        red: "#FF4560",
        text: "#E8F0FE",
        muted: "#4A6080",
        dim: "#1E2D45",
      },
      fontFamily: {
        display: ["Orbitron", "sans-serif"],
        body: ["Sora", "sans-serif"],
        mono: ["JetBrains Mono", "monospace"],
      },
    },
  },
  plugins: [],
};
