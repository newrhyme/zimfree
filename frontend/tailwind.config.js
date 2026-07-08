/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        navy: {
          900: "#0d1533",
          800: "#141d42",
          700: "#1e2a5a",
        },
        line1: "#f06a00",
        line2: "#00a84d",
        line3: "#bb8c00",
        line4: "#2c7cd8",
      },
    },
  },
  plugins: [],
};
