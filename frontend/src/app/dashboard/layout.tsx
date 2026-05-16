"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import styles from "./layout.module.css";

const NAV_ITEMS = [
  { href: "/dashboard", icon: "📊", label: "Overview" },
  { href: "/dashboard/ideas", icon: "💡", label: "My Ideas" },
  { href: "/dashboard/ideas/new", icon: "✨", label: "New Idea" },
];

const NAV_TOOLS = [
  { href: "/dashboard/agents", icon: "🤖", label: "Agent Monitor" },
  { href: "/dashboard/workflows", icon: "🔄", label: "Workflows" },
  { href: "/dashboard/reports", icon: "📄", label: "Reports" },
  { href: "/dashboard/simulation", icon: "🎯", label: "Pitch Simulation" },
];

const NAV_SETTINGS = [
  { href: "/dashboard/settings", icon: "⚙️", label: "Settings" },
];

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const pathname = usePathname();

  return (
    <div className={styles.dashboardLayout}>
      {/* Sidebar */}
      <aside className={styles.sidebar}>
        <div className={styles.sidebarHeader}>
          <div className={styles.sidebarLogo}>🚀</div>
          <div>
            <div className={styles.sidebarBrand}>AI Incubator</div>
            <div className={styles.sidebarBrandSub}>Startup Simulator</div>
          </div>
        </div>

        <nav className={styles.sidebarNav}>
          <div className={styles.sidebarSection}>Main</div>
          {NAV_ITEMS.map((item) => (
            <Link
              key={item.href}
              href={item.href}
              className={`${styles.navLink} ${
                pathname === item.href ? styles.navLinkActive : ""
              }`}
            >
              <span className={styles.navIcon}>{item.icon}</span>
              {item.label}
            </Link>
          ))}

          <div className={styles.sidebarSection}>AI Tools</div>
          {NAV_TOOLS.map((item) => (
            <Link
              key={item.href}
              href={item.href}
              className={`${styles.navLink} ${
                pathname === item.href ? styles.navLinkActive : ""
              }`}
            >
              <span className={styles.navIcon}>{item.icon}</span>
              {item.label}
            </Link>
          ))}

          <div className={styles.sidebarSection}>System</div>
          {NAV_SETTINGS.map((item) => (
            <Link
              key={item.href}
              href={item.href}
              className={`${styles.navLink} ${
                pathname === item.href ? styles.navLinkActive : ""
              }`}
            >
              <span className={styles.navIcon}>{item.icon}</span>
              {item.label}
            </Link>
          ))}
        </nav>

        <div className={styles.sidebarFooter}>
          <div className={styles.userCard}>
            <div className={styles.userAvatar}>👤</div>
            <div>
              <div className={styles.userName}>Founder</div>
              <div className={styles.userRole}>Free Plan · 10 credits</div>
            </div>
          </div>
        </div>
      </aside>

      {/* Main Content */}
      <main className={styles.mainContent}>
        <header className={styles.header}>
          <div className={styles.headerTitle}>
            {getPageTitle(pathname)}
          </div>
          <div className={styles.headerActions}>
            <Link href="/dashboard/ideas/new" className="btn btn-primary btn-sm" id="header-new-idea">
              ✨ New Idea
            </Link>
          </div>
        </header>

        <div className={styles.pageContent}>{children}</div>
      </main>
    </div>
  );
}

function getPageTitle(pathname: string): string {
  const titles: Record<string, string> = {
    "/dashboard": "Dashboard Overview",
    "/dashboard/ideas": "My Ideas",
    "/dashboard/ideas/new": "Submit New Idea",
    "/dashboard/agents": "Agent Monitor",
    "/dashboard/workflows": "Workflow Visualizer",
    "/dashboard/reports": "Reports",
    "/dashboard/simulation": "Investor Pitch Simulation",
    "/dashboard/settings": "Settings",
  };
  return titles[pathname] || "Dashboard";
}
