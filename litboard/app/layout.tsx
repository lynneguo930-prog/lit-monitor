import type { Metadata, Viewport } from "next";
import type { ReactNode } from "react";
import "./globals.css";

export const metadata: Metadata = {
  title: "文献看板 · 番茄抗病基因结构变异",
  description:
    "基于 OpenAlex 的学术主题文献看板，追踪植物结构变异附近的抗病基因研究（以番茄为主）。",
  applicationName: "文献看板",
  manifest: "/manifest.json",
  // 生成 apple-mobile-web-app-capable / -status-bar-style / -title
  appleWebApp: {
    capable: true,
    title: "文献看板",
    statusBarStyle: "black-translucent",
  },
  icons: {
    icon: "/icon-192.png",
    // 生成 <link rel="apple-touch-icon" href="/apple-touch-icon.png">
    apple: "/apple-touch-icon.png",
  },
  formatDetection: { telephone: false },
};

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  // 沉浸式全屏：内容延伸到刘海与状态栏下方，配合 .pt-safe 使用
  viewportFit: "cover",
  themeColor: [
    { media: "(prefers-color-scheme: light)", color: "#f8fafc" },
    { media: "(prefers-color-scheme: dark)", color: "#020617" },
  ],
};

export default function RootLayout({ children }: Readonly<{ children: ReactNode }>) {
  return (
    <html lang="zh-CN">
      <head>
        {/* Next 的 appleWebApp.capable 只输出标准 mobile-web-app-capable，
            iOS Safari 全屏 standalone 仍要求这条 apple- 前缀的 meta */}
        <meta name="apple-mobile-web-app-capable" content="yes" />
      </head>
      <body className="min-h-dvh bg-slate-50 text-slate-900 antialiased dark:bg-slate-950 dark:text-slate-100">
        {children}
      </body>
    </html>
  );
}
