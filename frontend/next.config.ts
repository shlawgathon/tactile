import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  output: 'standalone',
  async rewrites() {
    const isProduction = process.env.NODE_ENV === 'production';
    const apiDestination = isProduction
      ? 'https://api.tactile3d.dev/api/:path*'
      : 'http://localhost:8080/api/:path*';

    return [
      {
        source: '/api/:path*',
        destination: apiDestination,
      },
    ];
  },
};

export default nextConfig;
