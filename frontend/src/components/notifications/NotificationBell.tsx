"use client";

import { useState, useEffect, useRef } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/contexts/AuthContext";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

interface Notification {
  id: string;
  title: string;
  message: string;
  data?: { link?: string; action_url?: string; [key: string]: unknown };
  priority: string;
  read: boolean;
  read_at?: string | null;
  created_at: string;
}

interface NotificationsResponse {
  items: Notification[];
  total: number;
  unread_count: number;
}

export default function NotificationBell() {
  const { token } = useAuth();
  const router = useRouter();
  const [isOpen, setIsOpen] = useState(false);
  const [unreadCount, setUnreadCount] = useState(0);
  const [notifications, setNotifications] = useState<Notification[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

  // Poll unread count every 30 seconds
  useEffect(() => {
    fetchUnreadCount();
    const interval = setInterval(fetchUnreadCount, 30000);
    return () => clearInterval(interval);
  }, [token]);

  // Fetch recent notifications when dropdown opens
  useEffect(() => {
    if (isOpen) {
      fetchNotifications();
    }
  }, [isOpen, token]);

  // Close on outside click
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    };
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  const authHeaders = () => ({
    Authorization: `Bearer ${token}`,
    "Content-Type": "application/json",
  });

  const fetchUnreadCount = async () => {
    if (!token) return;
    try {
      const res = await fetch(`${API_BASE_URL}/api/v1/notifications/unread-count`, {
        headers: authHeaders(),
      });
      if (res.ok) {
        const data = await res.json();
        setUnreadCount(data.count ?? 0);
      }
    } catch (e) {
      console.error("Failed to fetch unread count:", e);
    }
  };

  const fetchNotifications = async () => {
    if (!token) return;
    setIsLoading(true);
    try {
      const res = await fetch(
        `${API_BASE_URL}/api/v1/notifications?unread=true&limit=5`,
        { headers: authHeaders() }
      );
      if (res.ok) {
        const data: NotificationsResponse = await res.json();
        setNotifications(data.items ?? []);
        setUnreadCount(data.unread_count ?? 0);
      }
    } catch (e) {
      console.error("Failed to fetch notifications:", e);
    } finally {
      setIsLoading(false);
    }
  };

  const markAsRead = async (id: string) => {
    if (!token) return;
    try {
      const res = await fetch(`${API_BASE_URL}/api/v1/notifications/${id}/read`, {
        method: "POST",
        headers: authHeaders(),
      });
      if (res.ok) {
        setNotifications((prev) =>
          prev.map((n) => (n.id === id ? { ...n, read: true } : n))
        );
        setUnreadCount((prev) => Math.max(0, prev - 1));
      }
    } catch (e) {
      console.error("Failed to mark as read:", e);
    }
  };

  const markAllRead = async () => {
    if (!token) return;
    try {
      const res = await fetch(`${API_BASE_URL}/api/v1/notifications/mark-all-read`, {
        method: "POST",
        headers: authHeaders(),
      });
      if (res.ok) {
        setNotifications((prev) => prev.map((n) => ({ ...n, read: true })));
        setUnreadCount(0);
      }
    } catch (e) {
      console.error("Failed to mark all read:", e);
    }
  };

  const handleNotificationClick = async (notification: Notification) => {
    if (!notification.read) {
      await markAsRead(notification.id);
    }
    const link = notification.data?.link ?? notification.data?.action_url;
    if (link) {
      setIsOpen(false);
      // Internal links start with /; external open in new tab
      if (link.startsWith("/")) {
        router.push(link);
      } else {
        window.open(link, "_blank", "noopener,noreferrer");
      }
    }
  };

  const formatTime = (dateString: string) => {
    const date = new Date(dateString);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const minutes = Math.floor(diffMs / 60000);
    if (minutes < 1) return "Just now";
    if (minutes < 60) return `${minutes}m ago`;
    const hours = Math.floor(minutes / 60);
    if (hours < 24) return `${hours}h ago`;
    const days = Math.floor(hours / 24);
    if (days < 7) return `${days}d ago`;
    return date.toLocaleDateString();
  };

  const priorityDot: Record<string, string> = {
    critical: "bg-red-500",
    high: "bg-orange-500",
    normal: "bg-blue-500",
    low: "bg-gray-500",
  };

  return (
    <div className="relative" ref={dropdownRef}>
      {/* Bell button */}
      <button
        onClick={() => setIsOpen((v) => !v)}
        className="relative p-2 text-gray-400 hover:text-white transition-colors rounded-md hover:bg-gray-700"
        aria-label="Notifications"
      >
        <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9"
          />
        </svg>
        {unreadCount > 0 && (
          <span className="absolute top-0 right-0 flex items-center justify-center min-w-[18px] h-[18px] px-1 text-[10px] font-bold text-white bg-red-500 rounded-full">
            {unreadCount > 99 ? "99+" : unreadCount}
          </span>
        )}
      </button>

      {/* Dropdown */}
      {isOpen && (
        <div className="absolute right-0 mt-2 w-96 bg-gray-800 border border-gray-700 rounded-lg shadow-2xl z-50">
          {/* Header */}
          <div className="flex items-center justify-between px-4 py-3 border-b border-gray-700">
            <h3 className="font-semibold text-white">
              Notifications
              {unreadCount > 0 && (
                <span className="ml-2 text-xs bg-red-500 text-white px-1.5 py-0.5 rounded-full">
                  {unreadCount}
                </span>
              )}
            </h3>
            {unreadCount > 0 && (
              <button
                onClick={markAllRead}
                className="text-xs text-blue-400 hover:text-blue-300 transition-colors"
              >
                Mark all read
              </button>
            )}
          </div>

          {/* Body */}
          <div className="max-h-[28rem] overflow-y-auto">
            {isLoading ? (
              <div className="flex items-center justify-center py-10">
                <div className="w-6 h-6 border-2 border-blue-500 border-t-transparent rounded-full animate-spin" />
              </div>
            ) : notifications.length === 0 ? (
              <div className="text-center py-10">
                <div className="text-4xl mb-2">🔔</div>
                <p className="text-gray-400 text-sm">No unread notifications</p>
              </div>
            ) : (
              <div className="divide-y divide-gray-700">
                {notifications.map((n) => (
                  <button
                    key={n.id}
                    onClick={() => handleNotificationClick(n)}
                    className={`w-full text-left px-4 py-3 hover:bg-gray-700/60 transition-colors ${
                      !n.read ? "bg-gray-700/20" : ""
                    }`}
                  >
                    <div className="flex items-start gap-3">
                      <div
                        className={`w-2 h-2 rounded-full mt-1.5 flex-shrink-0 ${
                          n.read ? "bg-transparent" : (priorityDot[n.priority] ?? "bg-blue-500")
                        }`}
                      />
                      <div className="flex-1 min-w-0">
                        <p className={`text-sm font-medium truncate ${n.read ? "text-gray-300" : "text-white"}`}>
                          {n.title}
                        </p>
                        <p className="text-xs text-gray-400 line-clamp-2 mt-0.5">
                          {n.message}
                        </p>
                        <p className="text-xs text-gray-500 mt-1">{formatTime(n.created_at)}</p>
                      </div>
                    </div>
                  </button>
                ))}
              </div>
            )}
          </div>

          {/* Footer */}
          <div className="px-4 py-2 border-t border-gray-700 text-center">
            <button
              onClick={() => { setIsOpen(false); router.push("/settings/notifications"); }}
              className="text-sm text-blue-400 hover:text-blue-300 transition-colors"
            >
              Notification settings →
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
