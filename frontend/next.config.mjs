/** @type {import('next').NextConfig} */
const nextConfig = {
  distDir: process.env.BUILD_PROD === 'true' ? '.next-prod' : '.next',
  output: 'standalone',
};

export default nextConfig;
