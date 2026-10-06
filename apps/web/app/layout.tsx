import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "SeoMind — Local-first AI SEO Intelligence",
  description: "Google Search Console analysis, deterministic SEO opportunities and optional local AI.",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body>{children}</body>
    </html>
  );
}
