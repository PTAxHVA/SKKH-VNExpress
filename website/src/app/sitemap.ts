import type { MetadataRoute } from "next";
import { SITE } from "@/lib/constants";

export default function sitemap(): MetadataRoute.Sitemap {
  return [
    { url: SITE.url, lastModified: new Date("2026-04-28") },
    { url: `${SITE.url}/phuong-phap`, lastModified: new Date("2026-04-28") },
    { url: `${SITE.url}/doi-ngu`, lastModified: new Date("2026-04-28") }
  ];
}
