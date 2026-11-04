/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      // APEX Element Group brand palette (see brand/BRAND_INTEGRATION.md).
      colors: {
        'apex-navy': '#0B2545',
        'apex-deep': '#1F4F8F',
        'apex-blue': '#2B7BE4',
        'apex-sky': '#5FA2F5',
        'apex-mist': '#B9D3F5',
        // Re-point Tailwind's blues at the brand so existing buttons, links and
        // badges pick up the palette. 600 is apex-deep (not apex-blue) so white
        // text on small buttons and blue link text stay above 4.5:1 contrast.
        blue: {
          400: '#5FA2F5', // apex-sky
          500: '#2B7BE4', // apex-blue (focus rings, accents)
          600: '#1F4F8F', // apex-deep (buttons, links)
          700: '#0B2545', // apex-navy (hover, public-site buttons)
          800: '#071A33', // darker navy, for hover on navy buttons
        },
      },
      fontFamily: {
        brand: ['Montserrat', 'system-ui', 'sans-serif'],
      },
    },
  },
  plugins: [],
}
