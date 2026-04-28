import type { Metadata, Viewport } from "next";
import type { ReactNode } from "react";
import { Instrument_Serif, Inter, JetBrains_Mono } from "next/font/google";
import "./globals.css";
import { SiteHeader } from "@/components/layout/site-header";
import { SITE } from "@/lib/constants";
import { cn } from "@/lib/utils";

const inter = Inter({
  variable: "--font-inter",
  subsets: ["latin", "vietnamese"],
  display: "swap"
});

const instrument = Instrument_Serif({
  variable: "--font-instrument",
  subsets: ["latin"],
  weight: "400",
  display: "swap"
});

const jetbrains = JetBrains_Mono({
  variable: "--font-jetbrains",
  subsets: ["latin", "vietnamese"],
  display: "swap"
});

export const metadata: Metadata = {
  metadataBase: new URL(SITE.url),
  title: {
    default: SITE.title,
    template: `%s · ${SITE.name}`
  },
  description: SITE.description,
  openGraph: {
    title: SITE.title,
    description: SITE.description,
    type: "website",
    locale: "vi_VN",
    images: ["/opengraph-image"]
  },
  icons: {
    icon: "/favicon.svg",
    apple: "/icon.svg"
  }
};

export const viewport: Viewport = {
  themeColor: "#071216",
  colorScheme: "dark light"
};

export default function RootLayout({ children }: Readonly<{ children: ReactNode }>) {
  return (
    <html lang="vi" className={cn(inter.variable, instrument.variable, jetbrains.variable)}>
      <body className="grain-overlay">
        <a className="skip-link" href="#main-content">
          Bỏ qua điều hướng
        </a>
        <SiteHeader />
        {children}
      </body>
    </html>
  );
}
