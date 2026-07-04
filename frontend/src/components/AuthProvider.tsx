"use client";

import React, { createContext, useContext, useEffect, useState } from "react";
import { useRouter, usePathname } from "next/navigation";
import { authApi } from "@/lib/api";

interface User {
  id: string;
  email: string;
  role: string;
  full_name?: string;
  avatar_url?: string;
  tier?: string;
}

interface AuthContextType {
  user: User | null;
  isLoading: boolean;
  signOut: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType>({
  user: null,
  isLoading: true,
  signOut: async () => {},
});

export const useAuth = () => useContext(AuthContext);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  
  const router = useRouter();
  const pathname = usePathname();

  useEffect(() => {
    let mounted = true;

    async function checkSession() {
      const token = localStorage.getItem("access_token");
      if (!token) {
        if (mounted) {
          setUser(null);
          setIsLoading(false);
        }
        return;
      }

      try {
        const userData = await authApi.me();
        if (mounted) {
          setUser({
            id: userData.id,
            email: userData.email || "",
            role: userData.role,
            full_name: userData.full_name ?? undefined,
            tier: userData.tier,
          });
          setIsLoading(false);
        }
      } catch (error) {
        console.error("Session check failed:", error);
        localStorage.removeItem("access_token");
        if (mounted) {
          setUser(null);
          setIsLoading(false);
        }
      }
    }

    checkSession();

    return () => {
      mounted = false;
    };
  }, []);

  useEffect(() => {
    if (isLoading) return;

    const isAuthRoute = pathname === "/login" || pathname === "/signup" || pathname === "/reset-password";
    const isProtectedRoute = pathname.startsWith("/dashboard");

    if (isProtectedRoute && !user) {
      router.push("/login");
    } else if (isAuthRoute && user) {
      router.push("/dashboard");
    }
  }, [user, isLoading, pathname, router]);

  const signOut = async () => {
    try {
      await authApi.logout();
    } catch {
      // Ignore network errors on logout
    }
    localStorage.removeItem("access_token");
    setUser(null);
    router.push("/login");
  };

  return (
    <AuthContext.Provider value={{ user, isLoading, signOut }}>
      {isLoading && pathname.startsWith("/dashboard") ? (
        <div className="flex items-center justify-center min-h-screen bg-black">
          <div className="animate-spin text-4xl">🚀</div>
        </div>
      ) : (
        children
      )}
    </AuthContext.Provider>
  );
}
