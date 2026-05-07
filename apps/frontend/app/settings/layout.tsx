"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/utils";

const NAV_ITEMS = [
  { href: "/settings/usage", label: "비용 대시보드" },
  { href: "/settings/users", label: "사용자/권한" },
  { href: "/settings/audit", label: "감사 로그" },
  { href: "/settings/integrations", label: "연동 설정" },
] as const;

export default function SettingsLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const pathname = usePathname();

  return (
    <div className="mx-auto max-w-6xl p-6">
      <h1 className="text-3xl font-bold mb-6">설정</h1>
      <div className="flex gap-6">
        <nav className="flex flex-col gap-1 w-48 shrink-0">
          {NAV_ITEMS.map(({ href, label }) => (
            <Link
              key={href}
              href={href}
              className={cn(
                "inline-flex items-center justify-start rounded-md px-3 py-2 text-sm hover:bg-accent hover:text-accent-foreground",
                pathname === href && "bg-muted font-semibold",
              )}
            >
              {label}
            </Link>
          ))}
        </nav>
        <main className="flex-1 min-w-0">{children}</main>
      </div>
    </div>
  );
}
