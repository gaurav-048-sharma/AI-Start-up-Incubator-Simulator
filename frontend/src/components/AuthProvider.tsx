"use client";

import React, { createContext, useContext, useEffect, useState } from "react";
import { useRouter, usePathname } from "next/navigation";
import { User, Session } from "@supabase/supabase-js";
import { createClient } from "@/lib/supabase/client";

interface AuthContextType {
  user: User | null;
  session: Session | null;
  isLoading: boolean;
  signOut: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType>({
  user: null,
  session: null,
  isLoading: true,
  signOut: async () => {},
});

export const useAuth = () => useContext(AuthContext);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [session, setSession] = useState<Session | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  
  const router = useRouter();
  const pathname = usePathname();
  const supabase = createClient();

  useEffect(() => {
    let mounted = true;

    async function checkSession() {
      if (!supabase) {
        if (mounted) {
          // Mock mode: bypass auth
          import("@supabase/supabase-js").then(({ Session, User }) => {
            setSession({} as unknown as typeof Session);
            setUser({ id: "demo-user", email: "demo@incubator.ai", user_metadata: { role: "founder_product_lead", full_name: "Demo Founder" } } as unknown as typeof User);
          });
          setIsLoading(false);
        }
        return;
      }

      try {
        const { data, error } = await supabase.auth.getSession();
        if (error) throw error;
        
        if (mounted) {
          setSession(data.session);
          setUser(data.session?.user ?? null);
          setIsLoading(false);
        }
      } catch (error) {
        console.error("Error checking session:", error);
        if (mounted) setIsLoading(false);
      }
    }

    checkSession();

    if (!supabase) return;

    const { data: { subscription } } = supabase.auth.onAuthStateChange(
      (event, currentSession) => {
        if (mounted) {
          setSession(currentSession);
          setUser(currentSession?.user ?? null);
          setIsLoading(false);
          
          if (event === "SIGNED_OUT") {
            router.push("/login");
          } else if (event === "SIGNED_IN" && (pathname === "/login" || pathname === "/signup")) {
            router.push("/dashboard");
          }
        }
      }
    );

    return () => {
      mounted = false;
      subscription?.unsubscribe();
    };
  }, [supabase, router, pathname]);

  useEffect(() => {
    // Route protection logic
    if (isLoading) return;

    const isAuthRoute = pathname === "/login" || pathname === "/signup" || pathname === "/reset-password";
    const isProtectedRoute = pathname.startsWith("/dashboard");

    // Skip protection if no supabase URL is configured (fallback mode)
    if (!process.env.NEXT_PUBLIC_SUPABASE_URL) return;

    if (isProtectedRoute && !user) {
      router.push("/login");
    } else if (isAuthRoute && user) {
      router.push("/dashboard");
    }
  }, [user, isLoading, pathname, router]);

  const signOut = async () => {
    if (supabase) await supabase.auth.signOut();
    router.push("/login");
  };

  return (
    <AuthContext.Provider value={{ user, session, isLoading, signOut }}>
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
