/** @type {import('tailwindcss').Config} */
module.exports = {
  theme: {
    extend: {
      colors: {
        streamly: {
          pastel: "#a59dde",
          pastelPurple: "#a59dde",
          electric: "#8646ee",
          electricPurple: "#8646ee",
          violet: "#3f0b93",
          darkViolet: "#3f0b93",
          purpleBlue: "#4a3a8b",
          coal: "#0d000d",
          coalBlack: "#0d000d",
          paper: "#f8f6fb",
          white: "#ffffff",
          lavender: "#efe7ff",
          lavenderStrong: "#d9c8ff",
          wash: "#f3eeff"
        }
      },
      fontFamily: {
        "streamly-platform": ["Montserrat", "Inter", "ui-sans-serif", "system-ui", "sans-serif"],
        "streamly-body": ["Anybody", "Inter", "ui-sans-serif", "system-ui", "sans-serif"],
        "streamly-logo": ["Red Rose", "Georgia", "serif"]
      },
      borderRadius: {
        "streamly-sm": "0.5rem",
        "streamly-md": "0.75rem",
        "streamly-lg": "1rem",
        "streamly-xl": "1.5rem",
        "streamly-panel": "2rem",
        "streamly-pill": "999px"
      },
      boxShadow: {
        "streamly-soft": "0 18px 45px rgba(63, 11, 147, 0.12)",
        "streamly-card": "0 10px 28px rgba(13, 0, 13, 0.08)",
        "streamly-button": "0 10px 18px rgba(134, 70, 238, 0.26)"
      },
      backgroundImage: {
        "streamly-soft": "linear-gradient(180deg, #8646ee 0%, #d9c8ff 46%, #ffffff 100%)",
        "streamly-hero": "linear-gradient(135deg, #8646ee 0%, #a59dde 44%, #f8f6fb 100%)",
        "streamly-button": "linear-gradient(135deg, #8646ee 0%, #3f0b93 100%)"
      }
    }
  }
};
