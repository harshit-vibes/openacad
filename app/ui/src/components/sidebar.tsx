"use client";

import {
  Atom,
  Bot,
  ClipboardCheck,
  FileText,
  GraduationCap,
  Library,
  LineChart,
  Pencil,
  PenSquare,
  Sparkles,
} from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";

import { cn } from "@/lib/utils";

type SidebarItem = {
  href: string;
  label: string;
  icon: React.ComponentType<{ className?: string }>;
};

type SidebarSection = {
  title: string;
  items: SidebarItem[];
};

const SECTIONS: SidebarSection[] = [
  {
    title: "Overview",
    items: [{ href: "/", label: "Welcome", icon: Sparkles }],
  },
  {
    title: "Vault",
    items: [
      { href: "/vault", label: "Atoms", icon: Atom },
      { href: "/ingest", label: "Ingest", icon: Library },
      { href: "/curate", label: "Curate", icon: ClipboardCheck },
    ],
  },
  {
    title: "Agents",
    items: [{ href: "/agents", label: "Agent editor", icon: Bot }],
  },
  {
    title: "Workflows",
    items: [
      { href: "/compose", label: "Compose", icon: PenSquare },
      { href: "/assess", label: "Assess", icon: Pencil },
    ],
  },
  {
    title: "Operations",
    items: [{ href: "/observability", label: "Observability", icon: LineChart }],
  },
  {
    title: "Museum",
    items: [{ href: "/museum", label: "Thesis tour", icon: GraduationCap }],
  },
];

export function Sidebar() {
  const pathname = usePathname();
  return (
    <aside className="hidden md:flex w-64 flex-col border-r border-border bg-card/30">
      <div className="px-6 py-5 border-b border-border">
        <Link href="/" className="flex items-center gap-2">
          <FileText className="h-5 w-5 text-primary" />
          <span className="font-semibold text-sm tracking-tight">openacad</span>
        </Link>
        <p className="text-[11px] text-muted-foreground mt-1">
          AI-first notes for scholars
        </p>
      </div>

      <nav className="flex-1 overflow-y-auto py-4">
        {SECTIONS.map((section) => (
          <div key={section.title} className="px-3 mb-4">
            <div className="px-3 mb-1.5 text-[10px] uppercase tracking-wider text-muted-foreground font-medium">
              {section.title}
            </div>
            <ul className="space-y-0.5">
              {section.items.map((item) => {
                const Icon = item.icon;
                const active =
                  pathname === item.href ||
                  (item.href !== "/" && pathname.startsWith(item.href));
                return (
                  <li key={item.href}>
                    <Link
                      href={item.href}
                      className={cn(
                        "flex items-center gap-2 px-3 py-1.5 rounded-md text-sm transition-colors",
                        active
                          ? "bg-accent text-accent-foreground font-medium"
                          : "text-muted-foreground hover:bg-accent/50 hover:text-foreground",
                      )}
                    >
                      <Icon className="h-4 w-4" />
                      <span>{item.label}</span>
                    </Link>
                  </li>
                );
              })}
            </ul>
          </div>
        ))}
      </nav>

      <div className="px-6 py-4 border-t border-border text-[11px] text-muted-foreground">
        <p>Local • Obsidian-compatible</p>
      </div>
    </aside>
  );
}
