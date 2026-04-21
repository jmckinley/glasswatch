"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { vulnerabilitiesApi } from "@/lib/api";

interface Vulnerability {
  id: string;
  identifier: string;
  source: string;
  title: string;
  description: string;
  severity: string;
  cvss_score: number;
  cvss_vector: string;
  epss_score: number;
  kev_listed: boolean;
  patch_available: boolean;
  patch_released_at: string | null;
  vendor_advisory_url: string | null;
  exploit_available: boolean;
  exploit_maturity: string | null;
  exploit_sources: string[];
  published_at: string;
  updated_at: string;
  affected_products: any[];
  asset_vulnerabilities: any[];
}

const SEVERITY_COLORS: Record<string, string> = {
  CRITICAL: "text-destructive",
  HIGH: "text-warning",
  MEDIUM: "text-secondary",
  LOW: "text-success",
};

const SEVERITY_BG: Record<string, string> = {
  CRITICAL: "bg-destructive/10 border-destructive/30",
  HIGH: "bg-warning/10 border-warning/30",
  MEDIUM: "bg-secondary/10 border-secondary/30",
  LOW: "bg-success/10 border-success/30",
};

export default function VulnerabilityDetailPage() {
  const params = useParams();
  const id = params.id as string;
  const [vulnerability, setVulnerability] = useState<Vulnerability | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchVulnerability();
  }, [id]);

  const fetchVulnerability = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await vulnerabilitiesApi.get(id);
      setVulnerability(data);
    } catch (err: any) {
      setError(err.message || "Failed to load vulnerability");
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <div className="text-neutral-400">Loading vulnerability details...</div>
      </div>
    );
  }

  if (error || !vulnerability) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[400px] gap-4">
        <div className="text-destructive">
          {error || "Vulnerability not found"}
        </div>
        <Link
          href="/vulnerabilities"
          className="px-4 py-2 bg-primary text-white rounded-lg hover:bg-primary/90 transition-colors"
        >
          Back to Vulnerabilities
        </Link>
      </div>
    );
  }

  const vuln = vulnerability;
  const publishedDate = new Date(vuln.published_at).toLocaleDateString();
  const updatedDate = new Date(vuln.updated_at).toLocaleDateString();

  return (
    <div className="space-y-6">
      {/* Back Navigation */}
      <Link
        href="/vulnerabilities"
        className="inline-flex items-center gap-2 text-neutral-400 hover:text-white transition-colors"
      >
        ← Back to Vulnerabilities
      </Link>

      {/* Header */}
      <div className="card p-6">
        <div className="flex items-start justify-between gap-4">
          <div className="flex-1">
            <div className="flex items-center gap-3 mb-2">
              <h1 className="text-2xl font-bold">{vuln.identifier}</h1>
              <span
                className={`px-3 py-1 rounded-lg text-sm font-medium border ${
                  SEVERITY_BG[vuln.severity]
                } ${SEVERITY_COLORS[vuln.severity]}`}
              >
                {vuln.severity}
              </span>
              {vuln.kev_listed && (
                <span className="px-3 py-1 bg-destructive/20 text-destructive rounded-lg text-sm font-medium border border-destructive/30">
                  KEV Listed
                </span>
              )}
            </div>
            <h2 className="text-xl text-neutral-300 mb-3">
              {vuln.title || "No title available"}
            </h2>
            <div className="flex items-center gap-4 text-sm text-neutral-400">
              <span>Source: {vuln.source.toUpperCase()}</span>
              <span>•</span>
              <span>Published: {publishedDate}</span>
              <span>•</span>
              <span>Updated: {updatedDate}</span>
            </div>
          </div>
        </div>
      </div>

      {/* Scores Grid */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="card p-4">
          <div className="text-sm text-neutral-400 mb-1">CVSS Score</div>
          <div className="text-3xl font-bold">
            {vuln.cvss_score ? vuln.cvss_score.toFixed(1) : "N/A"}
          </div>
          {vuln.cvss_vector && (
            <div className="text-xs text-neutral-500 mt-1 break-all">
              {vuln.cvss_vector}
            </div>
          )}
        </div>

        <div className="card p-4">
          <div className="text-sm text-neutral-400 mb-1">EPSS Score</div>
          <div className="text-3xl font-bold">
            {vuln.epss_score
              ? `${(vuln.epss_score * 100).toFixed(1)}%`
              : "N/A"}
          </div>
          <div className="text-xs text-neutral-500 mt-1">
            Exploit probability
          </div>
        </div>

        <div className="card p-4">
          <div className="text-sm text-neutral-400 mb-1">Exploit Status</div>
          <div className="text-lg font-bold">
            {vuln.exploit_available ? (
              <span className="text-warning">Available</span>
            ) : (
              <span className="text-success">None Known</span>
            )}
          </div>
          {vuln.exploit_maturity && (
            <div className="text-xs text-neutral-500 mt-1">
              {vuln.exploit_maturity}
            </div>
          )}
        </div>

        <div className="card p-4">
          <div className="text-sm text-neutral-400 mb-1">Patch Status</div>
          <div className="text-lg font-bold">
            {vuln.patch_available ? (
              <span className="text-success">Available</span>
            ) : (
              <span className="text-warning">Not Available</span>
            )}
          </div>
          {vuln.patch_released_at && (
            <div className="text-xs text-neutral-500 mt-1">
              Released {new Date(vuln.patch_released_at).toLocaleDateString()}
            </div>
          )}
        </div>
      </div>

      {/* Description */}
      {vuln.description && (
        <div className="card p-6">
          <h3 className="text-lg font-semibold mb-3">Description</h3>
          <p className="text-neutral-300 leading-relaxed whitespace-pre-wrap">
            {vuln.description}
          </p>
        </div>
      )}

      {/* Additional Details */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Exploit Information */}
        {vuln.exploit_available && vuln.exploit_sources && vuln.exploit_sources.length > 0 && (
          <div className="card p-6">
            <h3 className="text-lg font-semibold mb-3">Exploit Sources</h3>
            <ul className="space-y-2">
              {vuln.exploit_sources.map((source, idx) => (
                <li key={idx} className="text-neutral-300">
                  • {source}
                </li>
              ))}
            </ul>
          </div>
        )}

        {/* Vendor Advisory */}
        {vuln.vendor_advisory_url && (
          <div className="card p-6">
            <h3 className="text-lg font-semibold mb-3">Vendor Advisory</h3>
            <a
              href={vuln.vendor_advisory_url}
              target="_blank"
              rel="noopener noreferrer"
              className="text-primary hover:underline break-all"
            >
              {vuln.vendor_advisory_url}
            </a>
          </div>
        )}

        {/* Affected Products */}
        {vuln.affected_products && vuln.affected_products.length > 0 && (
          <div className="card p-6">
            <h3 className="text-lg font-semibold mb-3">Affected Products</h3>
            <ul className="space-y-2">
              {vuln.affected_products.map((product, idx) => (
                <li key={idx} className="text-neutral-300">
                  • {product.vendor} {product.product}
                  {product.versions && ` (${product.versions.join(", ")})`}
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>

      {/* Affected Assets */}
      {vuln.asset_vulnerabilities && vuln.asset_vulnerabilities.length > 0 && (
        <div className="card p-6">
          <h3 className="text-lg font-semibold mb-4">
            Affected Assets ({vuln.asset_vulnerabilities.length})
          </h3>
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="bg-neutral-900 border-b border-border">
                <tr>
                  <th className="text-left px-4 py-3 text-sm font-medium text-neutral-400">
                    Asset Name
                  </th>
                  <th className="text-left px-4 py-3 text-sm font-medium text-neutral-400">
                    Type
                  </th>
                  <th className="text-left px-4 py-3 text-sm font-medium text-neutral-400">
                    Environment
                  </th>
                  <th className="text-left px-4 py-3 text-sm font-medium text-neutral-400">
                    Status
                  </th>
                </tr>
              </thead>
              <tbody>
                {vuln.asset_vulnerabilities.map((av: any, idx: number) => (
                  <tr
                    key={idx}
                    className="border-b border-border hover:bg-card-hover transition-colors"
                  >
                    <td className="px-4 py-3">
                      {av.asset?.name || av.asset?.hostname || "Unknown"}
                    </td>
                    <td className="px-4 py-3 text-neutral-400">
                      {av.asset?.type || "N/A"}
                    </td>
                    <td className="px-4 py-3 text-neutral-400">
                      {av.asset?.environment || "N/A"}
                    </td>
                    <td className="px-4 py-3">
                      <span
                        className={`px-2 py-1 rounded text-xs ${
                          av.remediated
                            ? "bg-success/20 text-success"
                            : "bg-warning/20 text-warning"
                        }`}
                      >
                        {av.remediated ? "Remediated" : "Open"}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
