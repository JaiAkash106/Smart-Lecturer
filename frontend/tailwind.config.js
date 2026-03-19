/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,jsx}"],
  theme: {
    extend: {
      colors: {
        ink: "#08111f",
        coral: "#ff785a",
        aqua: "#70f6ff",
        sand: "#f8e8c8",
      },
      boxShadow: {
        panel: "0 20px 45px rgba(4, 14, 32, 0.35)",
      },
    },
  },
  plugins: [],
};
