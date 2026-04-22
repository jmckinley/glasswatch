"use client";

import { useEffect, useState } from "react";
import { useRouter, usePathname } from "next/navigation";
import Navigation from "@/components/Navigation";
import { AIAssistant } from "@/components/AIAssistant";
import { apiCall } from "@/lib/api";

export default function DashboardGroupLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const router = useRouter();
  const pathname = usePathname();
  const [isCheckingOnboarding, setIsCheckingOnboarding] = useState(true);
  const [onboardingComplete, setOnboardingComplete] = useState(false);

  useEffect(() => {
    // Check onboarding status on mount
    const checkOnboarding = async () => {
      try {
        const status = await apiCall<any>("/onboarding/status");
        
        // If onboarding not complete, redirect to /onboarding
        if (!status.onboarding_completed && pathname !== "/onboarding") {
          router.push("/onboarding");
          return;
        }
        
        setOnboardingComplete(status.onboarding_completed);
      } catch (error) {
        console.error("Failed to check onboarding status:", error);
        // On error, assume completed to avoid blocking access
        setOnboardingComplete(true);
      } finally {
        setIsCheckingOnboarding(false);
      }
    };

    checkOnboarding();
  }, [router, pathname]);

  // Show loading state while checking
  if (isCheckingOnboarding) {
    return (
      <div className="min-h-screen bg-gray-900 flex items-center justify-center">
        <div className="text-white">Loading...</div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-900">
      <Navigation />
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {children}
      </main>
      <AIAssistant />
    </div>
  );
}
