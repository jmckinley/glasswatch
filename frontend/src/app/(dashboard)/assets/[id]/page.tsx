"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { assetsApi } from "@/lib/api";

interface Asset {
  id: string;
  identifier: string;
  name: string;
  type: string;
  platform: string;
  environment: string;
  criticality: number;
  exposure: string;
  location: string;
  owner_team: string;
  risk_score: number;
  is_internet_facing: boolean;
  last_scanned_at: string | null;
  last_patched_at: string | null;
  created_at: string;
  updated_at: string;
  tags: string[];
  patch_group: string | null;
  os_family: string | null;
  fqdn: string | null;
  business_unit: string | null;
  ip_addresses: string[];
  cloud_provider: string | null;
  cloud_account_id: string | null;
  cloud_region: string | null;
  cloud_instance_type: string | null;
  cloud_tags: Record<string, string>;
  installed_packages: Array<{ name: string; version: string }>;
  running_services: string[];
  open_ports: number[];
  maintenance_window: string | null;
  compliance_frameworks: string[];
  compensating_controls: string[];
  cmdb_id: string | null;
  monitoring_id: string | null;
  uptime_days: number | null;
}

interface Vulnerability {
  id: string;
  identifier: string;
  title: string;
  severity: string;
  cvss_score: number;
  risk_score: number;
  patch_available: boolean;
  recommended_action: string;
}

const tagColors = [
  'bg-blue-500/20 text-blue-300 border-blue-500/30',
  'bg-green-500/20 text-green-300 border-green-500/30',
  'bg-purple-500/20 text-purple-300 border-purple-500/30',
  'bg-yellow-500/20 text-yellow-300 border-yellow-500/30',
  'bg-pink-500/20 text-pink-300 border-pink-500/30',
  'bg-cyan-500/20 text-cyan-300 border-cyan-500/30',
  'bg-orange-500/20 text-orange-300 border-orange-500/30',
  'bg-red-500/20 text-red-300 border-red-500/30',
];

function getTagColor(tag: string) {
  let hash = 0;
  for (let i = 0; i < tag.length; i++) {
    hash = tag.charCodeAt(i) + ((hash << 5) - hash);
  }
  return tagColors[Math.abs(hash) % tagColors.length];
}

const SEVERITY_COLORS: Record<string, string> = {
  CRITICAL: "text-red-500",
  HIGH: "text-orange-500",
  MEDIUM: "text-yellow-500",
  LOW: "text-blue-400",
};

const SEVERITY_BG: Record<string, string> = {
  CRITICAL: "bg-red-500/10",
  HIGH: "bg-orange-500/10",
  MEDIUM: "bg-yellow-500/10",
  LOW: "bg-blue-500/10",
};

export default function AssetDetailPage() {
  const params = useParams();
  const assetId = params?.id as string;

  const [asset, setAsset] = useState<Asset | null>(null);
  const [vulnerabilities, setVulnerabilities] = useState<Vulnerability[]>([]);
  const [vulnerabilityCount, setVulnerabilityCount] = useState(0);
  const [criticalVulnerabilityCount, setCriticalVulnerabilityCount] = useState(0);
  const [loading, setLoading] = useState(true);
  const [newTag, setNewTag] = useState("");
  const [availableTags, setAvailableTags] = useState<string[]>([]);

  useEffect(() => {
    if (assetId) {
      fetchAssetDetail();
      fetchAvailableTags();
    }
  }, [assetId]);

  const fetchAssetDetail = async () => {
    try {
      setLoading(true);
      const data = await assetsApi.get(assetId);
      setAsset(data.asset || data);
      setVulnerabilities(data.vulnerabilities || []);
      setVulnerabilityCount(data.vulnerability_count || 0);
      setCriticalVulnerabilityCount(data.critical_vulnerability_count || 0);
    } catch (error) {
      console.error("Failed to fetch asset detail:", error);
    } finally {
      setLoading(false);
    }
  };

  const fetchAvailableTags = async () => {
    try {
      const data = await assetsApi.tags();
      setAvailableTags((data.tags || []).map((t: any) => t.name));
    } catch (error) {
      console.error("Failed to fetch tags:", error);
    }
  };

  const handleAddTag = async () => {
    if (!asset || !newTag) return;
    try {
      await assetsApi.updateTags(asset.id, [newTag], []);
      setNewTag("");
      fetchAssetDetail();
      fetchAvailableTags();
    } catch (error) {
      console.error("Failed to add tag:", error);
    }
  };

  const handleRemoveTag = async (tag: string) => {
    if (!asset) return;
    try {
      await assetsApi.updateTags(asset.id, [], [tag]);
      fetchAssetDetail();
      fetchAvailableTags();
    } catch (error) {
      console.error("Failed to remove tag:", error);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-gray-400">Loading asset...</div>
      </div>
    );
  }

  if (!asset) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-gray-400">Asset not found</div>
      </div>
    );
  }

  const riskColor = asset.risk_score > 700 ? 'text-red-500' : asset.risk_score > 400 ? 'text-orange-500' : 'text-yellow-500';
  const criticalityColor = asset.criticality >= 8 ? 'text-red-500' : asset.criticality >= 5 ? 'text-orange-500' : 'text-yellow-500';

  return (
    <>
      {/* Back Link */}
      <Link href="/assets" className="text-blue-400 hover:text-blue-300 mb-4 inline-block">
        ← Back to Assets
      </Link>

      {/* Header */}
      <div className="bg-gray-800 rounded-lg p-6 mb-6">
        <div className="flex items-start justify-between mb-4">
          <div>
            <h1 className="text-3xl font-bold text-white mb-2">{asset.name}</h1>
            <div className="text-gray-400">{asset.identifier}</div>
          </div>
          <div className="flex gap-3">
            <div className="text-center">
              <div className={`text-2xl font-bold ${riskColor}`}>
                {asset.risk_score.toFixed(0)}
              </div>
              <div className="text-sm text-gray-400">Risk Score</div>
            </div>
            <div className="text-center">
              <span className={`px-3 py-1 text-sm rounded ${
                asset.environment === 'production'
                  ? 'bg-red-500/20 text-red-300'
                  : asset.environment === 'staging'
                  ? 'bg-yellow-500/20 text-yellow-300'
                  : 'bg-blue-500/20 text-blue-300'
              }`}>
                {asset.environment}
              </span>
            </div>
            <div className="text-center">
              <span className={`text-2xl font-bold ${criticalityColor}`}>
                {'★'.repeat(asset.criticality)}
              </span>
              <div className="text-sm text-gray-400">Criticality</div>
            </div>
          </div>
        </div>
      </div>

      {/* Overview Section */}
      <div className="bg-gray-800 rounded-lg p-6 mb-6">
        <h2 className="text-xl font-bold text-white mb-4">Overview</h2>
        <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
          <InfoField label="FQDN" value={asset.fqdn} />
          <InfoField label="IP Addresses" value={asset.ip_addresses?.join(", ")} />
          <InfoField label="OS" value={asset.os_family} />
          <InfoField label="Platform" value={asset.platform} />
          <InfoField label="Type" value={asset.type} />
          <InfoField label="Location" value={asset.location} />
          <InfoField label="Owner Team" value={asset.owner_team} />
          <InfoField label="Business Unit" value={asset.business_unit} />
          <InfoField label="Exposure" value={asset.exposure} />
        </div>
      </div>

      {/* Tags Section */}
      <div className="bg-gray-800 rounded-lg p-6 mb-6">
        <h2 className="text-xl font-bold text-white mb-4">Tags</h2>
        <div className="flex flex-wrap gap-2 mb-4">
          {asset.tags && asset.tags.length > 0 ? (
            asset.tags.map(tag => (
              <span
                key={tag}
                className={`px-3 py-1 text-sm rounded border ${getTagColor(tag)} flex items-center gap-2`}
              >
                {tag}
                <button
                  onClick={() => handleRemoveTag(tag)}
                  className="hover:text-white"
                >
                  ×
                </button>
              </span>
            ))
          ) : (
            <span className="text-gray-500 text-sm">No tags</span>
          )}
        </div>
        <div className="flex gap-2">
          <input
            type="text"
            value={newTag}
            onChange={(e) => setNewTag(e.target.value)}
            onKeyPress={(e) => e.key === 'Enter' && handleAddTag()}
            placeholder="Add tag..."
            className="flex-1 px-3 py-2 bg-gray-900 text-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
            list="available-tags"
          />
          <datalist id="available-tags">
            {availableTags.map(tag => (
              <option key={tag} value={tag} />
            ))}
          </datalist>
          <button
            onClick={handleAddTag}
            className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg"
          >
            Add Tag
          </button>
        </div>
      </div>

      {/* Configuration Section */}
      <div className="bg-gray-800 rounded-lg p-6 mb-6">
        <h2 className="text-xl font-bold text-white mb-4">Configuration</h2>
        <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
          <InfoField label="Patch Group" value={asset.patch_group} />
          <InfoField label="Maintenance Window" value={asset.maintenance_window} />
          <InfoField
            label="Compliance Frameworks"
            value={asset.compliance_frameworks?.join(", ")}
          />
          <InfoField
            label="Compensating Controls"
            value={asset.compensating_controls?.join(", ")}
          />
        </div>
      </div>

      {/* Cloud Metadata */}
      {asset.cloud_provider && (
        <div className="bg-gray-800 rounded-lg p-6 mb-6">
          <h2 className="text-xl font-bold text-white mb-4">Cloud Metadata</h2>
          <div className="grid grid-cols-2 md:grid-cols-3 gap-4 mb-4">
            <InfoField label="Provider" value={asset.cloud_provider} />
            <InfoField label="Account ID" value={asset.cloud_account_id} />
            <InfoField label="Region" value={asset.cloud_region} />
            <InfoField label="Instance Type" value={asset.cloud_instance_type} />
          </div>
          {asset.cloud_tags && Object.keys(asset.cloud_tags).length > 0 && (
            <div>
              <div className="text-sm text-gray-400 mb-2">Cloud Tags:</div>
              <div className="flex flex-wrap gap-2">
                {Object.entries(asset.cloud_tags).map(([key, value]) => (
                  <span
                    key={key}
                    className="px-2 py-1 text-xs rounded bg-gray-700 text-gray-300"
                  >
                    {key}: {value}
                  </span>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {/* Software Inventory */}
      {(asset.installed_packages?.length > 0 || asset.running_services?.length > 0 || asset.open_ports?.length > 0) && (
        <div className="bg-gray-800 rounded-lg p-6 mb-6">
          <h2 className="text-xl font-bold text-white mb-4">Software Inventory</h2>
          
          {asset.installed_packages && asset.installed_packages.length > 0 && (
            <div className="mb-4">
              <h3 className="text-lg font-medium text-white mb-2">Installed Packages</h3>
              <div className="bg-gray-900 rounded-lg p-4 max-h-64 overflow-y-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-gray-700">
                      <th className="text-left py-2 text-gray-400">Package</th>
                      <th className="text-left py-2 text-gray-400">Version</th>
                    </tr>
                  </thead>
                  <tbody>
                    {asset.installed_packages.map((pkg, idx) => (
                      <tr key={idx} className="border-b border-gray-800">
                        <td className="py-2 text-gray-300">{pkg.name}</td>
                        <td className="py-2 text-gray-400">{pkg.version}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {asset.running_services && asset.running_services.length > 0 && (
            <div className="mb-4">
              <h3 className="text-lg font-medium text-white mb-2">Running Services</h3>
              <div className="bg-gray-900 rounded-lg p-4">
                <div className="flex flex-wrap gap-2">
                  {asset.running_services.map((service, idx) => (
                    <span key={idx} className="px-2 py-1 text-sm bg-gray-700 text-gray-300 rounded">
                      {service}
                    </span>
                  ))}
                </div>
              </div>
            </div>
          )}

          {asset.open_ports && asset.open_ports.length > 0 && (
            <div>
              <h3 className="text-lg font-medium text-white mb-2">Open Ports</h3>
              <div className="bg-gray-900 rounded-lg p-4">
                <div className="flex flex-wrap gap-2">
                  {asset.open_ports.map((port, idx) => (
                    <span key={idx} className="px-2 py-1 text-sm bg-gray-700 text-gray-300 rounded font-mono">
                      {port}
                    </span>
                  ))}
                </div>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Vulnerabilities Section */}
      <div className="bg-gray-800 rounded-lg p-6 mb-6">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-xl font-bold text-white">
            Vulnerabilities ({vulnerabilityCount})
          </h2>
          {criticalVulnerabilityCount > 0 && (
            <span className="px-3 py-1 bg-red-500/20 text-red-300 rounded text-sm">
              {criticalVulnerabilityCount} Critical
            </span>
          )}
        </div>
        {vulnerabilities.length > 0 ? (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="bg-gray-900 border-b border-gray-700">
                <tr>
                  <th className="text-left px-4 py-3 text-sm font-medium text-gray-400">Identifier</th>
                  <th className="text-left px-4 py-3 text-sm font-medium text-gray-400">Severity</th>
                  <th className="text-left px-4 py-3 text-sm font-medium text-gray-400">CVSS</th>
                  <th className="text-left px-4 py-3 text-sm font-medium text-gray-400">Risk Score</th>
                  <th className="text-left px-4 py-3 text-sm font-medium text-gray-400">Patch</th>
                  <th className="text-left px-4 py-3 text-sm font-medium text-gray-400">Action</th>
                </tr>
              </thead>
              <tbody>
                {vulnerabilities.map((vuln) => (
                  <tr key={vuln.id} className="border-b border-gray-700 hover:bg-gray-700/30">
                    <td className="px-4 py-3">
                      <Link
                        href={`/vulnerabilities/${vuln.id}`}
                        className="text-blue-400 hover:text-blue-300"
                      >
                        {vuln.identifier}
                      </Link>
                      <div className="text-sm text-gray-400 mt-1">{vuln.title}</div>
                    </td>
                    <td className="px-4 py-3">
                      <span className={`px-2 py-1 text-xs rounded ${SEVERITY_BG[vuln.severity]} ${SEVERITY_COLORS[vuln.severity]}`}>
                        {vuln.severity}
                      </span>
                    </td>
                    <td className="px-4 py-3 font-mono text-gray-300">{vuln.cvss_score.toFixed(1)}</td>
                    <td className="px-4 py-3 font-mono text-gray-300">{vuln.risk_score.toFixed(0)}</td>
                    <td className="px-4 py-3">
                      {vuln.patch_available ? (
                        <span className="text-xs px-2 py-1 bg-green-500/20 text-green-300 rounded">Available</span>
                      ) : (
                        <span className="text-xs text-gray-500">None</span>
                      )}
                    </td>
                    <td className="px-4 py-3 text-sm text-gray-400">{vuln.recommended_action}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="text-center py-8 text-gray-400">
            No vulnerabilities detected
          </div>
        )}
      </div>

      {/* Integration Section */}
      {(asset.cmdb_id || asset.monitoring_id) && (
        <div className="bg-gray-800 rounded-lg p-6 mb-6">
          <h2 className="text-xl font-bold text-white mb-4">Integration</h2>
          <div className="grid grid-cols-2 gap-4">
            <InfoField label="CMDB ID" value={asset.cmdb_id} />
            <InfoField label="Monitoring ID" value={asset.monitoring_id} />
          </div>
        </div>
      )}

      {/* Operational Section */}
      <div className="bg-gray-800 rounded-lg p-6">
        <h2 className="text-xl font-bold text-white mb-4">Operational</h2>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <InfoField
            label="Last Scanned"
            value={asset.last_scanned_at ? new Date(asset.last_scanned_at).toLocaleString() : "Never"}
          />
          <InfoField
            label="Last Patched"
            value={asset.last_patched_at ? new Date(asset.last_patched_at).toLocaleString() : "Unknown"}
          />
          <InfoField
            label="Uptime"
            value={asset.uptime_days !== null ? `${asset.uptime_days} days` : "Unknown"}
          />
          <InfoField
            label="Created"
            value={new Date(asset.created_at).toLocaleDateString()}
          />
        </div>
      </div>
    </>
  );
}

function InfoField({ label, value }: { label: string; value?: string | null }) {
  return (
    <div>
      <div className="text-sm text-gray-400 mb-1">{label}</div>
      <div className="text-white">{value || "-"}</div>
    </div>
  );
}
