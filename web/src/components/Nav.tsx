"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const links = [
  { href: "/", label: "Главная" },
  { href: "/chat", label: "Чат-демо" },
  { href: "/architecture", label: "Архитектура" },
  { href: "/economics", label: "Экономика" },
];

export default function Nav() {
  const pathname = usePathname();

  return (
    <nav className="fixed top-0 left-0 right-0 z-50 border-b border-[var(--color-border)] bg-[var(--color-bg)]/80 backdrop-blur-md">
      <div className="mx-auto flex max-w-5xl items-center justify-between px-6 py-4">
        <Link href="/" className="text-lg font-bold tracking-tight">
          <span className="text-[var(--color-accent)]">Бескромный</span>GPT
        </Link>
        <div className="flex gap-6 text-sm">
          {links.map((link) => (
            <Link
              key={link.href}
              href={link.href}
              className={`transition-colors hover:text-white ${
                pathname === link.href
                  ? "text-white font-medium"
                  : "text-[var(--color-muted)]"
              }`}
            >
              {link.label}
            </Link>
          ))}
        </div>
      </div>
    </nav>
  );
}
