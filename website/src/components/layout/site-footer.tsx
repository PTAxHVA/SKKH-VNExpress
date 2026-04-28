import { REFERENCES } from "@/content/references";
import { VOTE_URL } from "@/lib/constants";

export function SiteFooter() {
  return (
    <footer className="border-t border-line-subtle bg-bg-base/80 py-12">
      <div className="mx-auto max-w-[1280px] px-6 md:px-10 lg:px-16">
        <div className="flex flex-col gap-6 md:flex-row md:items-start md:justify-between">
          <div>
            <p className="font-semibold text-ink-primary">© 2026 · Nhóm Giao Thông DHBK</p>
            <p className="mt-2 max-w-xl text-sm leading-6 text-ink-muted">
              Showcase phục vụ hồ sơ Sáng kiến Khoa học 2026, lĩnh vực Môi trường / Sáng kiến Xanh.
            </p>
          </div>
          <div className="flex flex-wrap gap-3 text-sm font-semibold text-ink-secondary">
            <a href={VOTE_URL} target="_blank" rel="noreferrer" className="hover:text-bio">Cuộc thi</a>
            <a href="/phuong-phap" className="hover:text-bio">Báo cáo phương pháp</a>
            <a href="#demo" className="hover:text-bio">Video demo</a>
          </div>
        </div>
        <div className="mt-10 grid gap-2 text-xs leading-5 text-ink-muted md:grid-cols-2">
          {REFERENCES.map((ref) => (
            <p key={ref.id}>
              [{ref.id}] {ref.url ? <a href={ref.url} target="_blank" rel="noreferrer" className="hover:text-bio">{ref.title}</a> : ref.title}
            </p>
          ))}
        </div>
      </div>
    </footer>
  );
}
