import type { Metadata } from "next";
import { Inter, JetBrains_Mono } from "next/font/google";
import "./globals.css";

const inter = Inter({
  variable: "--font-inter",
  subsets: ["latin"],
  display: "swap",
});

const jetbrainsMono = JetBrains_Mono({
  variable: "--font-jetbrains",
  subsets: ["latin"],
  display: "swap",
});

export const metadata: Metadata = {
  title: "AI Start-up Incubator | Transform Ideas into Investor-Ready Businesses",
  description:
    "AI-powered startup accelerator where autonomous agents research, validate, and pitch your startup ideas. Get market analysis, tech architecture, financial projections, and investor simulations — all powered by AI.",
  keywords: ["AI", "startup", "incubator", "accelerator", "pitch", "investor", "market research"],
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className={`${inter.variable} ${jetbrainsMono.variable}`}>
      <body>{children}</body>
    </html>
  );
}
