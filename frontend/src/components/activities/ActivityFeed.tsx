"use client";

import { useState, useEffect } from "react";
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
  actor: {
    id: string;
    full_name: string;
  };
  created_at: string;
  is_read: boolean;
  entity_type?: string;
  entity_id?: string;
}

interface ActivityFeedProps {
  mode?: "sidebar" | "page";
  limit?: number;
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

const ACTIVITY_COLORS: Record<ActivityType, string> = {
  approval_request: "text-blue-400",
  approval_approved: "text-green-400",
  approval_rejected: "text-red-400",
  comment_added: "text-purple-400",
  bundle_created: "text-yellow-400",
  bundle_deployed: "text-cyan-400",
  goal_created: "text-indigo-400",
  goal_completed: "text-green-400",
  vulnerability_discovered: "text-orange-400",
};

export default function ActivityFeed({ mode = "page", limit = 50 }: ActivityFeedProps) {
  const { token } = useAuth();
  const [activities, setActivities] = useState<Activity[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [unreadCount, setUnreadCount] = useState(0);

  useEffect(() => {
    fetchActivities();
  }, [token, limit]);

  const fetchActivities = async () => {
    if (!token) return;

    setIsLoading(true);
    try {
      const response = await fetch(
        `${API_BASE_URL}/api/v1/activities?limit=${limit}`,
        {
          headers: {
            Authorization: `Bearer ${token}`,
          },
        }
      );

      if (response.ok) {
        const data = await response.json();
        const items = data.items || data;
        setActivities(items);
        setUnreadCount(items.filter((a: Activity) => !a.is_read).length);
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
      console.error("Failed to mark activity as read:", error);
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
    // Could add navigation logic here based on entity_type and entity_id
  };

  if (isLoading) {
    return (
      <div className="text-center py-8">
        <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500"></div>
      </div>
    );
  }

  if (mode === "sidebar") {
    return (
      <div className="bg-gray-800 border border-gray-700 rounded-lg">
        {/* Header */}
        <div className="px-4 py-3 border-b border-gray-700 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <h3 className="font-semibold text-white">Activity</h3>
            {unreadCount > 0 && (
              <span className="px-2 py-0.5 bg-blue-600 text-white text-xs rounded-full">
                {unreadCount}
              </span>
            )}
          </div>
          {unreadCount > 0 && (
            <button
              onClick={markAllAsRead}
              className="text-xs text-blue-400 hover:text-blue-300"
            >
              Mark all read
            </button>
          )}
        </div>

        {/* Activities */}
        <div className="max-h-96 overflow-y-auto">
          {activities.length === 0 ? (
            <p className="text-center text-gray-500 py-8 text-sm">No recent activity</p>
          ) : (
            <div className="divide-y divide-gray-700">
              {activities.slice(0, 10).map((activity) => (
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
                      <p className={`text-sm font-medium mb-1 ${ACTIVITY_COLORS[activity.type]}`}>
                        {activity.title}
                      </p>
                      <p className="text-xs text-gray-400 line-clamp-2">
                        {activity.description}
                      </p>
                      <p className="text-xs text-gray-500 mt-1">
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
      </div>
    );
  }

  // Page mode
  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <h2 className="text-2xl font-bold text-white">Activity Feed</h2>
          {unreadCount > 0 && (
            <span className="px-3 py-1 bg-blue-600 text-white text-sm rounded-full">
              {unreadCount} unread
            </span>
          )}
        </div>
        {unreadCount > 0 && (
          <button
            onClick={markAllAsRead}
            className="px-4 py-2 bg-gray-700 hover:bg-gray-600 text-white text-sm font-medium rounded-lg transition-colors"
          >
            Mark all as read
          </button>
        )}
      </div>

      {/* Activities List */}
      {activities.length === 0 ? (
        <div className="text-center py-12 bg-gray-800 rounded-lg border border-gray-700">
          <p className="text-gray-400 text-lg">No activity to display</p>
        </div>
      ) : (
        <div className="space-y-3">
          {activities.map((activity) => (
            <button
              key={activity.id}
              onClick={() => handleActivityClick(activity)}
              className={`w-full text-left bg-gray-800 border border-gray-700 rounded-lg p-4 hover:border-gray-600 transition-colors ${
                !activity.is_read ? "ring-2 ring-blue-500/20" : ""
              }`}
            >
              <div className="flex items-start gap-4">
                <span className="text-3xl flex-shrink-0">
                  {ACTIVITY_ICONS[activity.type]}
                </span>
                <div className="flex-1 min-w-0">
                  <div className="flex items-start justify-between gap-4 mb-2">
                    <h3 className={`font-semibold ${ACTIVITY_COLORS[activity.type]}`}>
                      {activity.title}
                    </h3>
                    <span className="text-sm text-gray-500 flex-shrink-0">
                      {formatTime(activity.created_at)}
                    </span>
                  </div>
                  <p className="text-gray-400 text-sm mb-2">{activity.description}</p>
                  <p className="text-gray-500 text-xs">
                    by {activity.actor.full_name}
                  </p>
                </div>
                {!activity.is_read && (
                  <div className="w-3 h-3 bg-blue-500 rounded-full flex-shrink-0 mt-1"></div>
                )}
              </div>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
