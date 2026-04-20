"use client";

import { useState, useEffect } from "react";
import { useAuth } from "@/contexts/AuthContext";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

interface Bundle {
  id: string;
  name: string;
  patch_count: number;
  risk_score: number;
}

interface RiskAssessment {
  level: "low" | "medium" | "high" | "critical";
  score: number;
  factors: string[];
  impact_summary: string;
}

interface ApprovalRequestModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess?: () => void;
}

const RISK_COLORS = {
  low: "text-green-400 bg-green-900/20 border-green-700",
  medium: "text-yellow-400 bg-yellow-900/20 border-yellow-700",
  high: "text-orange-400 bg-orange-900/20 border-orange-700",
  critical: "text-red-400 bg-red-900/20 border-red-700",
};

export default function ApprovalRequestModal({
  isOpen,
  onClose,
  onSuccess,
}: ApprovalRequestModalProps) {
  const { token } = useAuth();
  const [bundles, setBundles] = useState<Bundle[]>([]);
  const [selectedBundleId, setSelectedBundleId] = useState("");
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [riskAssessment, setRiskAssessment] = useState<RiskAssessment | null>(null);
  const [isLoadingBundles, setIsLoadingBundles] = useState(false);
  const [isLoadingRisk, setIsLoadingRisk] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (isOpen) {
      fetchBundles();
    }
  }, [isOpen, token]);

  useEffect(() => {
    if (selectedBundleId) {
      fetchRiskAssessment();
    } else {
      setRiskAssessment(null);
    }
  }, [selectedBundleId, token]);

  const fetchBundles = async () => {
    if (!token) return;

    setIsLoadingBundles(true);
    try {
      const response = await fetch(`${API_BASE_URL}/api/v1/bundles?status=draft`, {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });

      if (response.ok) {
        const data = await response.json();
        setBundles(data.items || data);
      }
    } catch (err) {
      console.error("Failed to fetch bundles:", err);
    } finally {
      setIsLoadingBundles(false);
    }
  };

  const fetchRiskAssessment = async () => {
    if (!token || !selectedBundleId) return;

    setIsLoadingRisk(true);
    try {
      const response = await fetch(
        `${API_BASE_URL}/api/v1/bundles/${selectedBundleId}/risk-assessment`,
        {
          headers: {
            Authorization: `Bearer ${token}`,
          },
        }
      );

      if (response.ok) {
        const data = await response.json();
        setRiskAssessment(data);
      }
    } catch (err) {
      console.error("Failed to fetch risk assessment:", err);
    } finally {
      setIsLoadingRisk(false);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!token || !selectedBundleId || !title) return;

    setIsSubmitting(true);
    setError(null);

    try {
      const response = await fetch(`${API_BASE_URL}/api/v1/approvals`, {
        method: "POST",
        headers: {
          Authorization: `Bearer ${token}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          bundle_id: selectedBundleId,
          title,
          description,
        }),
      });

      if (response.ok) {
        onSuccess?.();
        handleClose();
      } else {
        const data = await response.json();
        setError(data.detail || "Failed to create approval request");
      }
    } catch (err) {
      setError("Failed to create approval request. Please try again.");
      console.error("Approval request error:", err);
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleClose = () => {
    setSelectedBundleId("");
    setTitle("");
    setDescription("");
    setRiskAssessment(null);
    setError(null);
    onClose();
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <div className="bg-gray-800 border border-gray-700 rounded-lg w-full max-w-2xl max-h-[90vh] overflow-y-auto">
        {/* Header */}
        <div className="sticky top-0 bg-gray-800 border-b border-gray-700 px-6 py-4 flex items-center justify-between">
          <h2 className="text-2xl font-semibold text-white">Request Approval</h2>
          <button
            onClick={handleClose}
            className="text-gray-400 hover:text-white transition-colors"
          >
            <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* Body */}
        <form onSubmit={handleSubmit} className="p-6 space-y-6">
          {error && (
            <div className="p-4 bg-red-900/20 border border-red-700 rounded-lg text-red-400 text-sm">
              {error}
            </div>
          )}

          {/* Bundle Selection */}
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-2">
              Patch Bundle *
            </label>
            <select
              value={selectedBundleId}
              onChange={(e) => setSelectedBundleId(e.target.value)}
              className="w-full px-4 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
              required
              disabled={isLoadingBundles}
            >
              <option value="">
                {isLoadingBundles ? "Loading bundles..." : "Select a bundle"}
              </option>
              {bundles.map((bundle) => (
                <option key={bundle.id} value={bundle.id}>
                  {bundle.name} ({bundle.patch_count} patches, risk: {bundle.risk_score})
                </option>
              ))}
            </select>
          </div>

          {/* Risk Assessment */}
          {isLoadingRisk && (
            <div className="p-4 bg-gray-700 rounded-lg">
              <p className="text-gray-400 text-sm">Loading risk assessment...</p>
            </div>
          )}

          {riskAssessment && (
            <div className={`p-4 rounded-lg border ${RISK_COLORS[riskAssessment.level]}`}>
              <div className="flex items-center gap-2 mb-2">
                <span className="text-lg font-semibold">
                  Risk Level: {riskAssessment.level.toUpperCase()}
                </span>
                <span className="text-sm opacity-75">
                  (Score: {riskAssessment.score})
                </span>
              </div>
              <p className="text-sm mb-3">{riskAssessment.impact_summary}</p>
              {riskAssessment.factors.length > 0 && (
                <div>
                  <p className="text-sm font-medium mb-1">Risk Factors:</p>
                  <ul className="text-sm space-y-1">
                    {riskAssessment.factors.map((factor, idx) => (
                      <li key={idx} className="flex items-start gap-2">
                        <span>•</span>
                        <span>{factor}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          )}

          {/* Title */}
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-2">
              Request Title *
            </label>
            <input
              type="text"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="e.g., Q2 2026 Critical Security Patches"
              className="w-full px-4 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-blue-500"
              required
            />
          </div>

          {/* Description */}
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-2">
              Description
            </label>
            <textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="Provide context for this approval request..."
              className="w-full px-4 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-blue-500"
              rows={4}
            />
          </div>

          {/* Impact Summary Preview */}
          {riskAssessment && (
            <div className="p-4 bg-gray-700 rounded-lg">
              <h4 className="text-sm font-semibold text-gray-300 mb-2">Impact Summary</h4>
              <p className="text-sm text-gray-400">{riskAssessment.impact_summary}</p>
            </div>
          )}

          {/* Actions */}
          <div className="flex gap-3 justify-end pt-4 border-t border-gray-700">
            <button
              type="button"
              onClick={handleClose}
              className="px-6 py-2 bg-gray-700 hover:bg-gray-600 text-white font-medium rounded-lg transition-colors"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={!selectedBundleId || !title || isSubmitting}
              className="px-6 py-2 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-600 disabled:cursor-not-allowed text-white font-medium rounded-lg transition-colors"
            >
              {isSubmitting ? "Creating..." : "Create Request"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
