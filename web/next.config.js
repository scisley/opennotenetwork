/** @type {import('next').NextConfig} */
const nextConfig = {
  turbopack: {
    root: __dirname,
  },
  eslint: {
    // Disable ESLint during builds to ignore these rules
    ignoreDuringBuilds: false,
  },
};

module.exports = nextConfig;