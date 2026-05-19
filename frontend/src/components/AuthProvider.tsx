"use client";

import React, { createContext, useContext, useEffect, useState } from "react";
import { useRouter, usePathname } from "next/navigation";
import { User, Session } from "@supabase/supabase-js";
import { createClient } from "@/lib/supabase/client";

interface AuthContextType {
  user: User | null;
  session: Session | null;
  isLoading: boolean;
  /** Whether the user has MFA enrolled but current session is only aal1 */
  mfaRequired: boolean;
  /** Whether the user has MFA fully verified (aal2) */
  mfaVerified: boolean;
  signOut: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType>({
  user: null,
  session: null,
  isLoading: true,
  mfaRequired: false,
  mfaVerified: false,
  signOut: async () => {},
});

export const useAuth = () => useContext(AuthContext);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [session, setSession] = useState<Session | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [mfaRequired, setMfaRequired] = useState(false);
  const [mfaVerified, setMfaVerified] = useState(false);
  
  const router = useRouter();
  const pathname = usePathname();
  const supabase = createClient();

  /**
   * Check the user's MFA assurance level.
   * If they have TOTP enrolled but are at aal1, they need to step up.
   */
  const checkMfaStatus = async () => {
    if (!supabase) return;
    try {
      const { data, error } = await supabase.auth.mfa.getAuthenticatorAssuranceLevel();
      if (error || !data) return;

      const { currentLevel, nextLevel } = data;
      
      if (currentLevel === "aal1" && nextLevel === "aal2") {
        // User has MFA enrolled but hasn't verified this session
        setMfaRequired(true);
        setMfaVerified(false);
      } else if (currentLevel === "aal2") {
        setMfaRequired(false);
        setMfaVerified(true);
      } else {
        // No MFA enrolled
        setMfaRequired(false);
        setMfaVerified(false);
      }
    } catch {
      // MFA check failed — don't block
    }
  };

  useEffect(() => {
    let mounted = true;

    async function checkSession() {
      if (!supabase) {
        if (mounted) {
          // Mock mode: bypass auth
          setSession({} as unknown as Session);
          setUser({ id: "demo-user", email: "demo@incubator.ai", user_metadata: { role: "founder_product_lead", full_name: "Demo Founder" } } as unknown as User);
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
          
          // Check MFA status after session is established
          if (data.session?.user) {
            await checkMfaStatus();
          }
        }
      } catch (error) {
        console.error("Error checking session:", error);
        if (mounted) setIsLoading(false);
      }
    }

    checkSession();

    if (!supabase) return;

    const { data: { subscription } } = supabase.auth.onAuthStateChange(
      async (event, currentSession) => {
        if (mounted) {
          setSession(currentSession);
          setUser(currentSession?.user ?? null);
          setIsLoading(false);
          
          if (event === "SIGNED_OUT") {
            setMfaRequired(false);
            setMfaVerified(false);
            router.push("/login");
          } else if (event === "SIGNED_IN" && (pathname === "/login" || pathname === "/signup")) {
            // Check if MFA is needed before redirecting to dashboard
            await checkMfaStatus();
          } else if (event === "TOKEN_REFRESHED" && currentSession?.user) {
            // Re-check MFA on token refresh
            await checkMfaStatus();
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
    } else if (isProtectedRoute && mfaRequired) {
      // User has MFA enrolled but hasn't verified yet — send to login with MFA flag
      router.push("/login?mfa=required");
    } else if (isAuthRoute && user && !mfaRequired) {
      router.push("/dashboard");
    }
  }, [user, isLoading, pathname, router, mfaRequired]);

  const signOut = async () => {
    if (supabase) await supabase.auth.signOut();
    setMfaRequired(false);
    setMfaVerified(false);
    router.push("/login");
  };

  return (
    <AuthContext.Provider value={{ user, session, isLoading, mfaRequired, mfaVerified, signOut }}>
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
