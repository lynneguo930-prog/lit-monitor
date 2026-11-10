import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  reactStrictMode: true,
  // STATIC_EXPORT=1 npm run build -> 产出纯静态 out/，可托管到任意静态服务/CDN。
  // 默认仍是标准 Next.js 构建，Vercel 部署不受影响。
  ...(process.env.STATIC_EXPORT === "1" ? { output: "export" as const } : {}),
};

export default nextConfig;
