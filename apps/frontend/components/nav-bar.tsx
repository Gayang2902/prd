"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/utils";

const NAV_ITEMS = [
  { href: "/projects", label: "프로젝트" },
  { href: "/queue", label: "큐" },
  { href: "/presets", label: "프리셋" },
  { href: "/settings/usage", label: "설정" },
] as const;

export function NavBar() {
  const pathname = usePathname();

  return (
    <header className="border-b bg-background">
      <div className="mx-auto flex h-12 max-w-6xl items-center gap-6 px-6">
        <Link href="/" className="font-bold text-lg tracking-tight text-primary">
          SecureScope
        </Link>
        <nav className="flex items-center gap-1">
          {NAV_ITEMS.map(({ href, label }) => (
            <Link
              key={href}
              href={href}
              className={cn(
                "rounded-md px-3 py-1.5 text-sm transition-colors hover:bg-accent hover:text-accent-foreground",
                pathname.startsWith(href) && "bg-muted font-medium",
              )}
            >
              {label}
            </Link>
          ))}
        </nav>
        <div className="ml-auto">
          <Link
            href="/profile"
            className="rounded-md px-3 py-1.5 text-sm text-muted-foreground hover:bg-accent hover:text-accent-foreground"
          >
            프로필
          </Link>
        </div>
      </div>
    </header>
  );
}
