/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        primary: '#10a37f',
        'primary-hover': '#0d8c6d',
      },
    },
  },
  plugins: [],
}
