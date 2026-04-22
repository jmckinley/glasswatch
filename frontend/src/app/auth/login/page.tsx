"use client";

import { useState, useEffect, Suspense } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { useAuth } from "@/contexts/AuthContext";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

function LoginContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { login, isAuthenticated } = useAuth();
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [providers, setProviders] = useState<Record<string, boolean>>({});

  // Fetch available providers
  useEffect(() => {
    const fetchProviders = async () => {
      try {
        const response = await fetch(`${API_BASE_URL}/api/v1/auth/providers`);
        if (response.ok) {
          const data = await response.json();
          setProviders(data.providers || {});
        }
      } catch (err) {
        console.error("Failed to fetch auth providers:", err);
      }
    };
    fetchProviders();
  }, []);

  // Redirect if already authenticated
  useEffect(() => {
    if (isAuthenticated) {
      router.push("/");
    }
  }, [isAuthenticated, router]);

  // Handle OAuth callback
  useEffect(() => {
    const token = searchParams?.get("token");
    if (token) {
      handleLoginCallback(token);
    }
  }, [searchParams]);

  const handleLoginCallback = async (token: string) => {
    try {
      setIsLoading(true);
      await login(token);
      router.push("/");
    } catch (err) {
      setError("Authentication failed. Please try again.");
      console.error("Login callback error:", err);
    } finally {
      setIsLoading(false);
    }
  };

  const handleSSOLogin = async () => {
    try {
      setIsLoading(true);
      setError(null);

      const response = await fetch(`${API_BASE_URL}/api/v1/auth/login`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          provider: "sso",
          redirect_uri: `${window.location.origin}/auth/login`,
        }),
      });

      if (!response.ok) {
        throw new Error("Failed to initiate SSO login");
      }

      const data = await response.json();
      if (data.authorization_url) {
        window.location.href = data.authorization_url;
      }
    } catch (err) {
      setError("Failed to initiate SSO login. Please try again.");
      console.error("SSO login error:", err);
      setIsLoading(false);
    }
  };

  const handleDemoLogin = async () => {
    try {
      setIsLoading(true);
      setError(null);

      const response = await fetch(`${API_BASE_URL}/api/v1/auth/demo-login`, {
        method: "GET",
      });

      if (!response.ok) {
        throw new Error("Failed to login with demo account");
      }

      const data = await response.json();
      if (data.access_token) {
        await login(data.access_token);
        router.push("/");
      }
    } catch (err) {
      setError("Failed to login with demo account. Please try again.");
      console.error("Demo login error:", err);
    } finally {
      setIsLoading(false);
    }
  };

  const handleGoogleLogin = async () => {
    try {
      setIsLoading(true);
      setError(null);

      const response = await fetch(`${API_BASE_URL}/api/v1/auth/google`, {
        method: "GET",
      });

      if (!response.ok) {
        throw new Error("Failed to initiate Google login");
      }

      const data = await response.json();
      if (data.authorization_url) {
        window.location.href = data.authorization_url;
      }
    } catch (err) {
      setError("Failed to initiate Google login. Please try again.");
      console.error("Google login error:", err);
      setIsLoading(false);
    }
  };

  const handleGitHubLogin = async () => {
    try {
      setIsLoading(true);
      setError(null);

      const response = await fetch(`${API_BASE_URL}/api/v1/auth/github`, {
        method: "GET",
      });

      if (!response.ok) {
        throw new Error("Failed to initiate GitHub login");
      }

      const data = await response.json();
      if (data.authorization_url) {
        window.location.href = data.authorization_url;
      }
    } catch (err) {
      setError("Failed to initiate GitHub login. Please try again.");
      console.error("GitHub login error:", err);
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-gray-900 via-gray-800 to-gray-900">
      <div className="w-full max-w-md">
        <div className="text-center mb-8">
          <h1 className="text-4xl font-bold text-white mb-2">Glasswatch</h1>
          <p className="text-gray-400">Intelligent Patch Decision Platform</p>
        </div>

        <div className="bg-gray-800 border border-gray-700 rounded-lg shadow-xl p-8">
          <h2 className="text-2xl font-semibold text-white mb-6 text-center">
            Sign In
          </h2>

          {error && (
            <div className="mb-6 p-4 bg-red-900/20 border border-red-700 rounded-lg text-red-400 text-sm">
              {error}
            </div>
          )}

          <div className="space-y-4">
            {providers.google && (
              <button
                onClick={handleGoogleLogin}
                disabled={isLoading}
                className="w-full py-3 px-4 bg-white hover:bg-gray-100 disabled:bg-gray-600 disabled:cursor-not-allowed text-gray-900 font-medium rounded-lg transition-colors duration-200 flex items-center justify-center gap-2"
              >
                <svg className="w-5 h-5" viewBox="0 0 24 24">
                  <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z" />
                  <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" />
                  <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z" />
                  <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" />
                </svg>
                <span>Sign in with Google</span>
              </button>
            )}

            {providers.github && (
              <button
                onClick={handleGitHubLogin}
                disabled={isLoading}
                className="w-full py-3 px-4 bg-gray-900 hover:bg-gray-800 disabled:bg-gray-600 disabled:cursor-not-allowed text-white font-medium rounded-lg transition-colors duration-200 flex items-center justify-center gap-2 border border-gray-700"
              >
                <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 24 24">
                  <path fillRule="evenodd" d="M12 2C6.477 2 2 6.484 2 12.017c0 4.425 2.865 8.18 6.839 9.504.5.092.682-.217.682-.483 0-.237-.008-.868-.013-1.703-2.782.605-3.369-1.343-3.369-1.343-.454-1.158-1.11-1.466-1.11-1.466-.908-.62.069-.608.069-.608 1.003.07 1.531 1.032 1.531 1.032.892 1.53 2.341 1.088 2.91.832.092-.647.35-1.088.636-1.338-2.22-.253-4.555-1.113-4.555-4.951 0-1.093.39-1.988 1.029-2.688-.103-.253-.446-1.272.098-2.65 0 0 .84-.27 2.75 1.026A9.564 9.564 0 0112 6.844c.85.004 1.705.115 2.504.337 1.909-1.296 2.747-1.027 2.747-1.027.546 1.379.202 2.398.1 2.651.64.7 1.028 1.595 1.028 2.688 0 3.848-2.339 4.695-4.566 4.943.359.309.678.92.678 1.855 0 1.338-.012 2.419-.012 2.747 0 .268.18.58.688.482A10.019 10.019 0 0022 12.017C22 6.484 17.522 2 12 2z" clipRule="evenodd" />
                </svg>
                <span>Sign in with GitHub</span>
              </button>
            )}

            {providers.workos && (
              <button
                onClick={handleSSOLogin}
                disabled={isLoading}
                className="w-full py-3 px-4 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-600 disabled:cursor-not-allowed text-white font-medium rounded-lg transition-colors duration-200 flex items-center justify-center gap-2"
              >
                {isLoading ? (
                  <>
                    <svg className="animate-spin h-5 w-5" viewBox="0 0 24 24">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                    </svg>
                    <span>Signing in...</span>
                  </>
                ) : (
                  <>
                    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 7a2 2 0 012 2m4 0a6 6 0 01-7.743 5.743L11 17H9v2H7v2H4a1 1 0 01-1-1v-2.586a1 1 0 01.293-.707l5.964-5.964A6 6 0 1121 9z" />
                  </svg>
                  <span>Sign in with SSO</span>
                </>
                )}
              </button>
            )}

            {providers.demo && (
              <>
                <div className="relative">
                  <div className="absolute inset-0 flex items-center">
                    <div className="w-full border-t border-gray-600"></div>
                  </div>
                  <div className="relative flex justify-center text-sm">
                    <span className="px-2 bg-gray-800 text-gray-400">Or</span>
                  </div>
                </div>

                <button
                  onClick={handleDemoLogin}
                  disabled={isLoading}
                  className="w-full py-3 px-4 bg-gray-700 hover:bg-gray-600 disabled:bg-gray-600 disabled:cursor-not-allowed text-white font-medium rounded-lg transition-colors duration-200 flex items-center justify-center gap-2"
                >
                  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5.121 17.804A13.937 13.937 0 0112 16c2.5 0 4.847.655 6.879 1.804M15 10a3 3 0 11-6 0 3 3 0 016 0zm6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                  </svg>
                  <span>Demo Login</span>
                </button>
              </>
            )}
          </div>

          <div className="mt-6 text-center text-sm text-gray-500">
            <p>Secure authentication powered by Glasswatch</p>
          </div>
        </div>

        <div className="mt-6 text-center text-sm text-gray-500">
          <p>Need help? Contact your administrator</p>
        </div>
      </div>
    </div>
  );
}

export default function LoginPage() {
  return (
    <Suspense fallback={
      <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-gray-900 via-gray-800 to-gray-900">
        <div className="text-white">Loading...</div>
      </div>
    }>
      <LoginContent />
    </Suspense>
  );
}
