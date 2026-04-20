"use client";

import { useState, useEffect, useRef } from "react";
import { useAuth } from "@/contexts/AuthContext";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

type ActivityType = 
  | "approval_request"
  | "approval_approved"
  | "approval_rejected"
  | "comment_added"
  | "bundle_created"
  | "bundle_deployed"
  | "goal_created"
  | "goal_completed"
  | "vulnerability_discovered";

interface Activity {
  id: string;
  type: ActivityType;
  title: string;
  description: string;
  created_at: string;
  is_read: boolean;
}

const ACTIVITY_ICONS: Record<ActivityType, string> = {
  approval_request: "📋",
  approval_approved: "✅",
  approval_rejected: "❌",
  comment_added: "💬",
  bundle_created: "📦",
  bundle_deployed: "🚀",
  goal_created: "🎯",
  goal_completed: "🏆",
  vulnerability_discovered: "🔒",
};

export default function NotificationBell() {
  const { token } = useAuth();
  const [isOpen, setIsOpen] = useState(false);
  const [unreadCount, setUnreadCount] = useState(0);
  const [activities, setActivities] = useState<Activity[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    fetchUnreadCount();
    const interval = setInterval(fetchUnreadCount, 30000); // Poll every 30s
    return () => clearInterval(interval);
  }, [token]);

  useEffect(() => {
    if (isOpen) {
      fetchRecentActivities();
    }
  }, [isOpen, token]);

  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    };

    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  const fetchUnreadCount = async () => {
    if (!token) return;

    try {
      const response = await fetch(
        `${API_BASE_URL}/api/v1/activities/unread-count`,
        {
          headers: {
            Authorization: `Bearer ${token}`,
          },
        }
      );

      if (response.ok) {
        const data = await response.json();
        setUnreadCount(data.count || 0);
      }
    } catch (error) {
      console.error("Failed to fetch unread count:", error);
    }
  };

  const fetchRecentActivities = async () => {
    if (!token) return;

    setIsLoading(true);
    try {
      const response = await fetch(
        `${API_BASE_URL}/api/v1/activities?limit=10`,
        {
          headers: {
            Authorization: `Bearer ${token}`,
          },
        }
      );

      if (response.ok) {
        const data = await response.json();
        setActivities(data.items || data);
      }
    } catch (error) {
      console.error("Failed to fetch activities:", error);
    } finally {
      setIsLoading(false);
    }
  };

  const markAsRead = async (activityId: string) => {
    if (!token) return;

    try {
      const response = await fetch(
        `${API_BASE_URL}/api/v1/activities/${activityId}/read`,
        {
          method: "POST",
          headers: {
            Authorization: `Bearer ${token}`,
          },
        }
      );

      if (response.ok) {
        setActivities((prev) =>
          prev.map((a) =>
            a.id === activityId ? { ...a, is_read: true } : a
          )
        );
        setUnreadCount((prev) => Math.max(0, prev - 1));
      }
    } catch (error) {
      console.error("Failed to mark as read:", error);
    }
  };

  const markAllAsRead = async () => {
    if (!token) return;

    try {
      const response = await fetch(
        `${API_BASE_URL}/api/v1/activities/read-all`,
        {
          method: "POST",
          headers: {
            Authorization: `Bearer ${token}`,
          },
        }
      );

      if (response.ok) {
        setActivities((prev) => prev.map((a) => ({ ...a, is_read: true })));
        setUnreadCount(0);
      }
    } catch (error) {
      console.error("Failed to mark all as read:", error);
    }
  };

  const formatTime = (dateString: string) => {
    const date = new Date(dateString);
    const now = new Date();
    const diff = now.getTime() - date.getTime();
    const minutes = Math.floor(diff / (1000 * 60));

    if (minutes < 1) return "Just now";
    if (minutes < 60) return `${minutes}m ago`;
    const hours = Math.floor(minutes / 60);
    if (hours < 24) return `${hours}h ago`;
    const days = Math.floor(hours / 24);
    if (days < 7) return `${days}d ago`;
    return date.toLocaleDateString();
  };

  const handleActivityClick = (activity: Activity) => {
    if (!activity.is_read) {
      markAsRead(activity.id);
    }
    // Could add navigation logic here
  };

  return (
    <div className="relative" ref={dropdownRef}>
      {/* Bell Button */}
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="relative p-2 text-gray-400 hover:text-white transition-colors"
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

        {/* Unread Badge */}
        {unreadCount > 0 && (
          <span className="absolute top-0 right-0 flex items-center justify-center w-5 h-5 text-xs font-bold text-white bg-red-500 rounded-full">
            {unreadCount > 9 ? "9+" : unreadCount}
          </span>
        )}
      </button>

      {/* Dropdown */}
      {isOpen && (
        <div className="absolute right-0 mt-2 w-96 bg-gray-800 border border-gray-700 rounded-lg shadow-xl z-50">
          {/* Header */}
          <div className="px-4 py-3 border-b border-gray-700 flex items-center justify-between">
            <h3 className="font-semibold text-white">Notifications</h3>
            {unreadCount > 0 && (
              <button
                onClick={markAllAsRead}
                className="text-xs text-blue-400 hover:text-blue-300"
              >
                Mark all read
              </button>
            )}
          </div>

          {/* Content */}
          <div className="max-h-[32rem] overflow-y-auto">
            {isLoading ? (
              <div className="text-center py-8">
                <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500"></div>
              </div>
            ) : activities.length === 0 ? (
              <div className="text-center py-8">
                <p className="text-gray-400 text-sm">No notifications</p>
              </div>
            ) : (
              <div className="divide-y divide-gray-700">
                {activities.map((activity) => (
                  <button
                    key={activity.id}
                    onClick={() => handleActivityClick(activity)}
                    className={`w-full text-left px-4 py-3 hover:bg-gray-700/50 transition-colors ${
                      !activity.is_read ? "bg-gray-700/30" : ""
                    }`}
                  >
                    <div className="flex items-start gap-3">
                      <span className="text-2xl flex-shrink-0">
                        {ACTIVITY_ICONS[activity.type]}
                      </span>
                      <div className="flex-1 min-w-0">
                        <p className="text-sm font-medium text-white mb-1">
                          {activity.title}
                        </p>
                        <p className="text-xs text-gray-400 line-clamp-2 mb-1">
                          {activity.description}
                        </p>
                        <p className="text-xs text-gray-500">
                          {formatTime(activity.created_at)}
                        </p>
                      </div>
                      {!activity.is_read && (
                        <div className="w-2 h-2 bg-blue-500 rounded-full flex-shrink-0 mt-1"></div>
                      )}
                    </div>
                  </button>
                ))}
              </div>
            )}
          </div>

          {/* Footer */}
          {activities.length > 0 && (
            <div className="px-4 py-3 border-t border-gray-700">
              <a
                href="/dashboard/activities"
                className="text-sm text-blue-400 hover:text-blue-300 font-medium"
                onClick={() => setIsOpen(false)}
              >
                View all activity →
              </a>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
