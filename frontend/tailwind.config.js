/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,jsx,ts,tsx}"],
  theme: {
    extend: {
      fontFamily: {
        display: ["Arial", "Helvetica", "sans-serif"],
        body:    ["Arial", "Helvetica", "sans-serif"],
        mono:    ["Consolas", "monospace"],
      },
      colors: {
        ink:   "#0D0D0D",
        paper: "#F5F2EB",
        lead:  "#1A1A2E",
        pulse: "#00FF94",
        dim:   "#FFFFFF",
        card:  "#16213E",
        border:"#2A2A4A",
      },
      animation: {
        "fade-up":   "fadeUp 0.5s ease forwards",
        "pulse-dot": "pulseDot 1.5s ease-in-out infinite",
        "scan":      "scan 2s linear infinite",
      },
      keyframes: {
        fadeUp: {
          "0%":   { opacity: 0, transform: "translateY(16px)" },
          "100%": { opacity: 1, transform: "translateY(0)" },
        },
        pulseDot: {
          "0%, 100%": { opacity: 1,   transform: "scale(1)"   },
          "50%":      { opacity: 0.4, transform: "scale(0.7)" },
        },
        scan: {
          "0%":   { transform: "translateY(-100%)" },
          "100%": { transform: "translateY(400%)"  },
        },
      },
    },
  },
  plugins: [],
};