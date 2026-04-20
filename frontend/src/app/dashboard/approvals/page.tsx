"use client";

import { useState, useEffect } from "react";
import { useAuth } from "@/contexts/AuthContext";
import DashboardLayout from "@/components/DashboardLayout";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

type ApprovalStatus = "pending" | "approved" | "rejected" | "all";
type RiskLevel = "low" | "medium" | "high" | "critical";

interface Approval {
  id: string;
  title: string;
  description: string;
  risk_level: RiskLevel;
  requester: {
    id: string;
    full_name: string;
  };
  required_approvals: number;
  current_approvals: number;
  status: string;
  created_at: string;
  bundle_id?: string;
}

const RISK_COLORS = {
  low: "text-green-400 bg-green-900/20 border-green-700",
  medium: "text-yellow-400 bg-yellow-900/20 border-yellow-700",
  high: "text-orange-400 bg-orange-900/20 border-orange-700",
  critical: "text-red-400 bg-red-900/20 border-red-700",
};

const RISK_ICONS = {
  low: "🟢",
  medium: "🟡",
  high: "🟠",
  critical: "🔴",
};

export default function ApprovalsPage() {
  const { token } = useAuth();
  const [activeTab, setActiveTab] = useState<ApprovalStatus>("pending");
  const [approvals, setApprovals] = useState<Approval[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [commentModalOpen, setCommentModalOpen] = useState(false);
  const [selectedApproval, setSelectedApproval] = useState<Approval | null>(null);
  const [actionType, setActionType] = useState<"approve" | "reject">("approve");
  const [comment, setComment] = useState("");

  useEffect(() => {
    fetchApprovals();
  }, [activeTab, token]);

  const fetchApprovals = async () => {
    if (!token) return;

    setIsLoading(true);
    try {
      const params = new URLSearchParams();
      if (activeTab !== "all") {
        params.append("status", activeTab);
      }

      const response = await fetch(
        `${API_BASE_URL}/api/v1/approvals?${params}`,
        {
          headers: {
            Authorization: `Bearer ${token}`,
          },
        }
      );

      if (response.ok) {
        const data = await response.json();
        setApprovals(data.items || data);
      }
    } catch (error) {
      console.error("Failed to fetch approvals:", error);
    } finally {
      setIsLoading(false);
    }
  };

  const openCommentModal = (approval: Approval, action: "approve" | "reject") => {
    setSelectedApproval(approval);
    setActionType(action);
    setCommentModalOpen(true);
  };

  const handleApprovalAction = async () => {
    if (!selectedApproval || !token) return;

    try {
      const endpoint =
        actionType === "approve"
          ? `/api/v1/approvals/${selectedApproval.id}/approve`
          : `/api/v1/approvals/${selectedApproval.id}/reject`;

      const response = await fetch(`${API_BASE_URL}${endpoint}`, {
        method: "POST",
        headers: {
          Authorization: `Bearer ${token}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ comment }),
      });

      if (response.ok) {
        setCommentModalOpen(false);
        setComment("");
        setSelectedApproval(null);
        fetchApprovals();
      }
    } catch (error) {
      console.error("Failed to process approval:", error);
    }
  };

  const formatDate = (dateString: string) => {
    const date = new Date(dateString);
    const now = new Date();
    const diff = now.getTime() - date.getTime();
    const hours = Math.floor(diff / (1000 * 60 * 60));

    if (hours < 24) {
      return `${hours}h ago`;
    }
    const days = Math.floor(hours / 24);
    return `${days}d ago`;
  };

  return (
    <DashboardLayout>
      <div>
        {/* Header */}
        <div className="mb-6">
          <h1 className="text-3xl font-bold text-white mb-2">Approval Requests</h1>
          <p className="text-gray-400">Review and approve patch deployment requests</p>
        </div>

        {/* Tabs */}
        <div className="border-b border-gray-700 mb-6">
          <div className="flex gap-4">
            {(["pending", "approved", "rejected", "all"] as ApprovalStatus[]).map((tab) => (
              <button
                key={tab}
                onClick={() => setActiveTab(tab)}
                className={`px-4 py-2 text-sm font-medium capitalize transition-colors border-b-2 ${
                  activeTab === tab
                    ? "text-blue-400 border-blue-400"
                    : "text-gray-400 border-transparent hover:text-gray-300"
                }`}
              >
                {tab}
              </button>
            ))}
          </div>
        </div>

        {/* Loading State */}
        {isLoading ? (
          <div className="text-center py-12">
            <div className="inline-block animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500"></div>
            <p className="mt-4 text-gray-400">Loading approvals...</p>
          </div>
        ) : approvals.length === 0 ? (
          <div className="text-center py-12 bg-gray-800 rounded-lg border border-gray-700">
            <p className="text-gray-400 text-lg">No {activeTab === "all" ? "" : activeTab} approvals found</p>
          </div>
        ) : (
          <div className="grid gap-4">
            {approvals.map((approval) => (
              <div
                key={approval.id}
                className="bg-gray-800 border border-gray-700 rounded-lg p-6 hover:border-gray-600 transition-colors"
              >
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    {/* Risk Badge & Title */}
                    <div className="flex items-center gap-3 mb-2">
                      <span
                        className={`px-3 py-1 rounded-full text-xs font-semibold border ${
                          RISK_COLORS[approval.risk_level]
                        }`}
                      >
                        {RISK_ICONS[approval.risk_level]} {approval.risk_level.toUpperCase()}
                      </span>
                      <h3 className="text-xl font-semibold text-white">{approval.title}</h3>
                    </div>

                    {/* Description */}
                    <p className="text-gray-400 mb-4">{approval.description}</p>

                    {/* Metadata */}
                    <div className="flex items-center gap-6 text-sm text-gray-500">
                      <span className="flex items-center gap-2">
                        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
                        </svg>
                        {approval.requester.full_name}
                      </span>
                      <span className="flex items-center gap-2">
                        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                        </svg>
                        {formatDate(approval.created_at)}
                      </span>
                      <span className="flex items-center gap-2">
                        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                        </svg>
                        {approval.current_approvals} / {approval.required_approvals} approvals
                      </span>
                    </div>
                  </div>

                  {/* Action Buttons */}
                  {approval.status === "pending" && (
                    <div className="flex gap-2 ml-4">
                      <button
                        onClick={() => openCommentModal(approval, "approve")}
                        className="px-4 py-2 bg-green-600 hover:bg-green-700 text-white text-sm font-medium rounded-lg transition-colors"
                      >
                        Approve
                      </button>
                      <button
                        onClick={() => openCommentModal(approval, "reject")}
                        className="px-4 py-2 bg-red-600 hover:bg-red-700 text-white text-sm font-medium rounded-lg transition-colors"
                      >
                        Reject
                      </button>
                    </div>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}

        {/* Comment Modal */}
        {commentModalOpen && selectedApproval && (
          <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
            <div className="bg-gray-800 border border-gray-700 rounded-lg p-6 w-full max-w-md">
              <h3 className="text-xl font-semibold text-white mb-4">
                {actionType === "approve" ? "Approve" : "Reject"} Request
              </h3>
              <p className="text-gray-400 mb-4">
                {selectedApproval.title}
              </p>
              <textarea
                value={comment}
                onChange={(e) => setComment(e.target.value)}
                placeholder="Add a comment (optional)"
                className="w-full px-4 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-blue-500 mb-4"
                rows={4}
              />
              <div className="flex gap-2 justify-end">
                <button
                  onClick={() => {
                    setCommentModalOpen(false);
                    setComment("");
                    setSelectedApproval(null);
                  }}
                  className="px-4 py-2 bg-gray-700 hover:bg-gray-600 text-white text-sm font-medium rounded-lg transition-colors"
                >
                  Cancel
                </button>
                <button
                  onClick={handleApprovalAction}
                  className={`px-4 py-2 text-white text-sm font-medium rounded-lg transition-colors ${
                    actionType === "approve"
                      ? "bg-green-600 hover:bg-green-700"
                      : "bg-red-600 hover:bg-red-700"
                  }`}
                >
                  {actionType === "approve" ? "Approve" : "Reject"}
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </DashboardLayout>
  );
}
