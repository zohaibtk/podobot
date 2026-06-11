const streamlyPreset = require("./src/design-system/streamly-aesthetic/tailwind.streamly.preset.js");

/** @type {import('tailwindcss').Config} */
module.exports = {
  presets: [streamlyPreset],
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      borderRadius: {
        "streamly-card": "1.25rem"
      },
      boxShadow: {
        "streamly-elevated": "0 24px 64px rgba(63, 11, 147, 0.16)",
        "streamly-glow": "0 18px 52px rgba(134, 70, 238, 0.18)"
      }
    }
  },
  plugins: []
};
