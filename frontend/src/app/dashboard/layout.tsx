"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import Image from "next/image";
import styles from "./layout.module.css";
import {
  authApi,
  notificationsApi,
  analyticsApi,
  organizationsApi,
  setActiveOrg,
  type Notification as AppNotification,
  type Organization,
} from "@/lib/api";
import { useAuth } from "@/components/AuthProvider";

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
  { href: "/dashboard/compare", icon: "⚖️", label: "Compare Ideas" },
];

const NAV_SETTINGS = [
  { href: "/dashboard/team", icon: "👥", label: "Team & Org" },
  { href: "/dashboard/settings", icon: "⚙️", label: "Settings" },
];

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const pathname = usePathname();
  const router = useRouter();
  const { user, signOut } = useAuth();
  const [unreadCount, setUnreadCount] = useState(0);
  const [credits, setCredits] = useState<number | null>(null);
  const [showNotifDropdown, setShowNotifDropdown] = useState(false);
  const [notifications, setNotifications] = useState<AppNotification[]>([]);
  const [organizations, setOrganizations] = useState<Organization[]>([]);
  const [activeOrgId, setActiveOrgId] = useState<string | null>(null);
  const [orgReady, setOrgReady] = useState(false);
  const [platformRole, setPlatformRole] = useState<string>("user");

  useEffect(() => {
    const stored = typeof window !== "undefined" ? localStorage.getItem("activeOrgId") : null;
    if (stored) {
      queueMicrotask(() => setActiveOrgId(stored));
    }
  }, []);

  const switchOrganization = (orgId: string) => {
    setActiveOrg(orgId);
    setActiveOrgId(orgId);
    window.location.reload();
  };

  useEffect(() => {
    async function loadHeader() {
      try {
        const [meData, notifData, creditsData, orgsData] = await Promise.allSettled([
          authApi.me(),
          notificationsApi.getUnreadCount(),
          analyticsApi.getCredits(),
          organizationsApi.list(),
        ]);

        if (meData.status === "fulfilled") {
          setPlatformRole(meData.value.platform_role || "user");
        }
        if (notifData.status === "fulfilled") setUnreadCount(notifData.value.unread_count);
        if (creditsData.status === "fulfilled") setCredits(creditsData.value.credits);
        if (orgsData.status === "fulfilled" && orgsData.value.organizations?.length > 0) {
          setOrganizations(orgsData.value.organizations);
          if (!activeOrgId && typeof window !== "undefined") {
            const firstOrgId = orgsData.value.organizations[0].id;
            setActiveOrgId(firstOrgId);
            setActiveOrg(firstOrgId);
          }
          queueMicrotask(() => setOrgReady(true));
        } else if (orgsData.status === "fulfilled") {
          queueMicrotask(() => setOrgReady(true));
        }
      } catch {
        /* backend may not be connected */
      }
    }
    loadHeader();

    const interval = setInterval(loadHeader, 30000);
    return () => clearInterval(interval);
  }, [user, activeOrgId]);

  const handleBellClick = async () => {
    setShowNotifDropdown((prev) => !prev);
    if (!showNotifDropdown) {
      try {
        const data = await notificationsApi.list();
        setNotifications(data.notifications.slice(0, 5));
      } catch {
        /* empty */
      }
    }
  };

  const handleMarkAllRead = async () => {
    try {
      await notificationsApi.markAllRead();
      setUnreadCount(0);
      setNotifications((prev) => prev.map((n) => ({ ...n, is_read: true })));
    } catch {
      /* empty */
    }
  };

  const handleNotifClick = async (notif: AppNotification) => {
    if (!notif.is_read) {
      await notificationsApi.markRead(notif.id).catch(() => {});
      setUnreadCount((c) => Math.max(0, c - 1));
    }
    setShowNotifDropdown(false);
    if (notif.action_url) router.push(notif.action_url);
  };

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

        {(platformRole === "super_admin" || organizations.length > 0) && (
          <div className={styles.workspaceSelector}>
            <div className={styles.sidebarSection}>
              {platformRole === "super_admin" ? "Platform Context" : "Workspace"}
            </div>
            <select
              value={activeOrgId || ""}
              onChange={(e) => switchOrganization(e.target.value)}
              className={styles.orgSelect}
              aria-label="Workspace"
            >
              {platformRole === "super_admin" && <option value="">Global Overview</option>}
              {organizations.map((org) => (
                <option key={org.id} value={org.id}>
                  {org.name}
                </option>
              ))}
            </select>
          </div>
        )}

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

          {platformRole === "super_admin" && (
            <>
              <div className={`${styles.sidebarSection} ${styles.adminSection}`}>
                Admin Control
              </div>
              <Link
                href="/dashboard/admin"
                className={`${styles.navLink} ${styles.adminLink} ${
                  pathname === "/dashboard/admin" ? styles.navLinkActive : ""
                }`}
              >
                <span className={styles.navIcon}>👑</span>
                Admin Panel
              </Link>
            </>
          )}

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
          <div className={`${styles.userCard} ${styles.userCardRow}`}>
            <div className={styles.userRow}>
              <div className={styles.userAvatar}>
                {user?.user_metadata?.avatar_url ? (
                  <Image
                    src={user.user_metadata.avatar_url}
                    alt="Avatar"
                    width={40}
                    height={40}
                    className={styles.userAvatarImg}
                  />
                ) : (
                  "👤"
                )}
              </div>
              <div>
                <div
                  className={`${styles.userName} ${styles.userNameClamp}`}
                >
                  {user?.user_metadata?.full_name || user?.email || "Founder"}
                </div>
                <div className={styles.userRole}>
                  {platformRole === "super_admin" ? (
                    <span className={styles.superAdminLabel}>
                      Platform Admin · {activeOrgId ? (organizations.find(o => o.id === activeOrgId)?.name || 'Viewing Org') : 'Global'}
                    </span>
                  ) : (
                    <>
                      {organizations.find(o => o.id === activeOrgId)?.my_role?.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase()) || "Member"} · {user?.user_metadata?.tier || "Free"} 
                      <br /> {credits !== null ? credits : "—"} credits
                    </>
                  )}
                </div>
              </div>
            </div>
            <button
              onClick={signOut}
              className={`btn btn-ghost btn-sm ${styles.signOutButton}`}
              title="Sign Out"
            >
              🚪
            </button>
          </div>
        </div>
      </aside>

      {/* Main Content */}
      <main className={styles.mainContent}>
        {!orgReady && platformRole !== "super_admin" ? (
          <div className="flex items-center justify-center min-h-[60vh]">
            <div className="animate-spin text-3xl">🚀</div>
          </div>
        ) : (
          <>
            <header className={styles.header}>
              <div className={styles.headerTitle}>{getPageTitle(pathname)}</div>
              <div className={styles.headerActions}>
                {/* Notification Bell */}
                <div className={styles.notifWrapper}>
                  <button
                    className={styles.notifBell}
                    onClick={handleBellClick}
                    id="notification-bell"
                    aria-label="Notifications"
                  >
                    🔔
                    {unreadCount > 0 && (
                      <span className={styles.notifBadge}>{unreadCount > 9 ? "9+" : unreadCount}</span>
                    )}
                  </button>

                  {showNotifDropdown && (
                    <div className={`${styles.notifDropdown} glass-card`}>
                      <div className={styles.notifDropdownHeader}>
                        <span>Notifications</span>
                        {unreadCount > 0 && (
                          <button className="btn btn-ghost btn-sm" onClick={handleMarkAllRead}>
                            Mark all read
                          </button>
                        )}
                      </div>
                      {notifications.length === 0 ? (
                        <div className={styles.notifEmpty}>No notifications yet</div>
                      ) : (
                        notifications.map((n) => (
                          <button
                            key={n.id}
                            className={`${styles.notifItem} ${!n.is_read ? styles.notifUnread : ""}`}
                            onClick={() => handleNotifClick(n)}
                          >
                            <div className={styles.notifTitle}>{n.title}</div>
                            {n.body && <div className={styles.notifBody}>{n.body}</div>}
                            <div className={styles.notifTime}>
                              {new Date(n.created_at).toLocaleDateString()}
                            </div>
                          </button>
                        ))
                      )}
                    </div>
                  )}
                </div>

                <Link href="/dashboard/ideas/new" className="btn btn-primary btn-sm" id="header-new-idea">
                  ✨ New Idea
                </Link>
              </div>
            </header>

            <div className={styles.pageContent}>{children}</div>
          </>
        )}
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
    "/dashboard/compare": "Compare Ideas",
    "/dashboard/team": "Team & Organization",
    "/dashboard/settings": "Settings",
    "/dashboard/admin": "Super Admin Control Panel",
  };
  return titles[pathname] || "Dashboard";
}
