"use client";

import { useEffect, useRef } from "react";

interface PrintReportProps {
  data: any;
  onClose: () => void;
}

export function PrintReport({ data, onClose }: PrintReportProps) {
  const ref = useRef<HTMLDivElement>(null);

  const handlePrint = () => {
    const content = ref.current?.innerHTML || "";
    const printWindow = window.open("", "_blank");
    if (!printWindow) return;

    printWindow.document.write(`
      <!DOCTYPE html>
      <html>
        <head>
          <title>Glasswatch Executive Report</title>
          <style>
            * { box-sizing: border-box; }
            body { font-family: Arial, sans-serif; color: #111; margin: 0; padding: 20px; }
            h1 { font-size: 24px; border-bottom: 2px solid #333; padding-bottom: 8px; }
            h2 { font-size: 18px; margin-top: 24px; color: #1a56db; }
            h3 { font-size: 14px; margin-top: 16px; }
            table { width: 100%; border-collapse: collapse; margin-top: 8px; font-size: 13px; }
            th { background: #f3f4f6; text-align: left; padding: 6px 10px; border: 1px solid #ddd; }
            td { padding: 6px 10px; border: 1px solid #ddd; }
            tr:nth-child(even) td { background: #f9fafb; }
            .badge { display: inline-block; padding: 2px 8px; border-radius: 4px; font-size: 12px; font-weight: bold; }
            .badge-critical { background: #fde8e8; color: #c81e1e; }
            .badge-high { background: #feecdc; color: #c35000; }
            .metric-row { display: flex; gap: 16px; flex-wrap: wrap; margin-top: 8px; }
            .metric-box { border: 1px solid #ddd; border-radius: 6px; padding: 12px 16px; min-width: 140px; }
            .metric-value { font-size: 28px; font-weight: bold; }
            .metric-label { font-size: 12px; color: #666; margin-top: 4px; }
            .footer { margin-top: 40px; font-size: 11px; color: #999; border-top: 1px solid #eee; padding-top: 8px; }
            @media print {
              body { padding: 0; }
              button { display: none; }
            }
          </style>
        </head>
        <body>${content}</body>
      </html>
    `);
    printWindow.document.close();
    printWindow.focus();
    printWindow.print();
  };

  if (!data) return null;

  const { vulnerability_summary, top_riskiest_assets, bundles_this_month, goals, generated_at, tenant_name } = data;

  return (
    <div className="fixed inset-0 bg-black/60 z-50 flex items-center justify-center p-4">
      <div className="bg-white rounded-lg shadow-2xl max-w-4xl w-full max-h-[90vh] overflow-y-auto">
        <div className="flex items-center justify-between p-4 border-b border-gray-200 sticky top-0 bg-white z-10">
          <h2 className="text-lg font-semibold text-gray-900">Executive Report Preview</h2>
          <div className="flex gap-2">
            <button
              onClick={handlePrint}
              className="px-4 py-2 bg-blue-600 text-white text-sm font-medium rounded-md hover:bg-blue-700"
            >
              Print / Save PDF
            </button>
            <button
              onClick={onClose}
              className="px-4 py-2 bg-gray-100 text-gray-700 text-sm font-medium rounded-md hover:bg-gray-200"
            >
              Close
            </button>
          </div>
        </div>

        <div ref={ref} className="p-6 text-gray-900">
          {/* Header */}
          <h1 className="text-2xl font-bold border-b-2 border-gray-800 pb-2 mb-4">
            Glasswatch Executive Security Report
          </h1>
          <p className="text-sm text-gray-500 mb-6">
            {tenant_name} &nbsp;·&nbsp; Generated {new Date(generated_at).toLocaleString()}
          </p>

          {/* Vulnerability Summary */}
          <h2 className="text-lg font-semibold text-blue-700 mt-6 mb-3">Vulnerability Summary</h2>
          <div className="flex gap-4 flex-wrap">
            {[
              { label: "Total Active", value: vulnerability_summary?.total_active ?? "—" },
              { label: "Critical", value: vulnerability_summary?.critical ?? "—" },
              { label: "KEV Listed", value: vulnerability_summary?.kev_listed ?? "—" },
            ].map((m) => (
              <div key={m.label} className="border border-gray-200 rounded-lg p-3 min-w-[120px]">
                <div className="text-3xl font-bold text-gray-800">{m.value}</div>
                <div className="text-xs text-gray-500 mt-1">{m.label}</div>
              </div>
            ))}
          </div>

          {/* Bundles This Month */}
          <h2 className="text-lg font-semibold text-blue-700 mt-8 mb-3">Patch Operations (Last 30 Days)</h2>
          <table>
            <thead>
              <tr>
                <th>Scheduled</th>
                <th>Completed</th>
                <th>Failed</th>
                <th>Total</th>
              </tr>
            </thead>
            <tbody>
              <tr>
                <td>{bundles_this_month?.scheduled ?? 0}</td>
                <td>{bundles_this_month?.completed ?? 0}</td>
                <td>{bundles_this_month?.failed ?? 0}</td>
                <td>{bundles_this_month?.total ?? 0}</td>
              </tr>
            </tbody>
          </table>

          {/* Top Riskiest Assets */}
          <h2 className="text-lg font-semibold text-blue-700 mt-8 mb-3">Top 5 Riskiest Assets</h2>
          <table>
            <thead>
              <tr>
                <th>Asset</th>
                <th>Environment</th>
                <th>Criticality</th>
                <th>Exposure</th>
                <th>Active Vulns</th>
                <th>Owner Team</th>
              </tr>
            </thead>
            <tbody>
              {(top_riskiest_assets || []).map((a: any) => (
                <tr key={a.id}>
                  <td>{a.name}</td>
                  <td>{a.environment || "—"}</td>
                  <td>{a.criticality}/5</td>
                  <td>{a.exposure || "—"}</td>
                  <td>{a.active_vuln_count}</td>
                  <td>{a.owner_team || "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>

          {/* Goals */}
          {goals && goals.length > 0 && (
            <>
              <h2 className="text-lg font-semibold text-blue-700 mt-8 mb-3">Active Goals</h2>
              <table>
                <thead>
                  <tr>
                    <th>Goal</th>
                    <th>Type</th>
                    <th>Progress</th>
                  </tr>
                </thead>
                <tbody>
                  {goals.map((g: any) => (
                    <tr key={g.id}>
                      <td>{g.name}</td>
                      <td>{g.type}</td>
                      <td>{g.progress_pct !== null ? `${g.progress_pct}%` : "—"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </>
          )}

          <div className="mt-10 pt-4 border-t border-gray-200 text-xs text-gray-400">
            Confidential — Glasswatch by McKinley Labs · {new Date().getFullYear()}
          </div>
        </div>
      </div>
    </div>
  );
}
