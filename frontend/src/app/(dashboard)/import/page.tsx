"use client";

import { useCallback, useRef, useState } from "react";
import { apiCall } from "@/lib/api";

type ImportType = "vulnerabilities" | "assets";

interface PreviewRow {
  [key: string]: string;
}

interface ImportResult {
  imported: number;
  skipped: number;
  errors: string[];
}

function parseCSV(text: string): { headers: string[]; rows: PreviewRow[] } {
  const lines = text.trim().split(/\r?\n/);
  if (lines.length === 0) return { headers: [], rows: [] };

  const headers = lines[0].split(",").map((h) => h.trim().replace(/^"|"$/g, ""));

  const rows = lines.slice(1, 6).map((line) => {
    const values = line.split(",").map((v) => v.trim().replace(/^"|"$/g, ""));
    const row: PreviewRow = {};
    headers.forEach((h, i) => {
      row[h] = values[i] ?? "";
    });
    return row;
  });

  return { headers, rows };
}

export default function ImportPage() {
  const [importType, setImportType] = useState<ImportType>("vulnerabilities");
  const [file, setFile] = useState<File | null>(null);
  const [preview, setPreview] = useState<{ headers: string[]; rows: PreviewRow[] } | null>(null);
  const [dragging, setDragging] = useState(false);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<ImportResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const handleFile = useCallback((f: File) => {
    setFile(f);
    setResult(null);
    setError(null);
    const reader = new FileReader();
    reader.onload = (e) => {
      const text = e.target?.result as string;
      setPreview(parseCSV(text));
    };
    reader.readAsText(f);
  }, []);

  const onFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const f = e.target.files?.[0];
    if (f) handleFile(f);
  };

  const onDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setDragging(false);
    const f = e.dataTransfer.files?.[0];
    if (f && f.name.endsWith(".csv")) handleFile(f);
  };

  const onDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setDragging(true);
  };

  const onDragLeave = () => setDragging(false);

  const handleImport = async () => {
    if (!file) return;
    setLoading(true);
    setError(null);
    setResult(null);

    try {
      const formData = new FormData();
      formData.append("file", file);

      const endpoint =
        importType === "vulnerabilities"
          ? "/import/vulnerabilities/csv"
          : "/import/assets/csv";

      const data = await apiCall<ImportResult>(endpoint, {
        method: "POST",
        body: formData,
        // Let browser set multipart content-type with boundary
        headers: {},
      });
      setResult(data);
    } catch (err: any) {
      setError(err?.message ?? "Import failed. Check the file format and try again.");
    } finally {
      setLoading(false);
    }
  };

  const reset = () => {
    setFile(null);
    setPreview(null);
    setResult(null);
    setError(null);
    if (inputRef.current) inputRef.current.value = "";
  };

  return (
    <div className="max-w-3xl mx-auto space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-white">CSV Import</h1>
        <p className="mt-1 text-sm text-gray-400">
          Bulk-import vulnerabilities or assets from a CSV file.
        </p>
      </div>

      {/* Type selector */}
      <div className="bg-gray-800 border border-gray-700 rounded-lg p-4">
        <label className="block text-sm font-medium text-gray-300 mb-3">
          Import type
        </label>
        <div className="flex gap-3">
          {(["vulnerabilities", "assets"] as ImportType[]).map((t) => (
            <button
              key={t}
              onClick={() => setImportType(t)}
              className={`flex-1 py-2 px-4 rounded-md text-sm font-medium transition-colors border ${
                importType === t
                  ? "bg-blue-600 border-blue-500 text-white"
                  : "bg-gray-700 border-gray-600 text-gray-300 hover:bg-gray-600"
              }`}
            >
              {t.charAt(0).toUpperCase() + t.slice(1)}
            </button>
          ))}
        </div>
      </div>

      {/* Drop zone */}
      {!file && (
        <div
          onDrop={onDrop}
          onDragOver={onDragOver}
          onDragLeave={onDragLeave}
          onClick={() => inputRef.current?.click()}
          className={`border-2 border-dashed rounded-lg p-10 text-center cursor-pointer transition-colors ${
            dragging
              ? "border-blue-500 bg-blue-900/20"
              : "border-gray-600 hover:border-gray-500 hover:bg-gray-800/50"
          }`}
        >
          <div className="text-4xl mb-3">📂</div>
          <p className="text-gray-300 font-medium">
            Drop your CSV here or{" "}
            <span className="text-blue-400 underline">browse</span>
          </p>
          <p className="text-xs text-gray-500 mt-1">
            Only .csv files are supported
          </p>
          <input
            ref={inputRef}
            type="file"
            accept=".csv"
            className="hidden"
            onChange={onFileChange}
          />
        </div>
      )}

      {/* File selected + preview */}
      {file && preview && !result && (
        <div className="bg-gray-800 border border-gray-700 rounded-lg overflow-hidden">
          <div className="flex items-center justify-between px-4 py-3 border-b border-gray-700">
            <div className="flex items-center gap-2">
              <span className="text-green-400">✓</span>
              <span className="text-sm text-gray-200 font-medium">{file.name}</span>
              <span className="text-xs text-gray-500">
                ({(file.size / 1024).toFixed(1)} KB)
              </span>
            </div>
            <button
              onClick={reset}
              className="text-xs text-gray-400 hover:text-white"
            >
              Change file
            </button>
          </div>

          {/* Preview table */}
          <div className="p-4">
            <p className="text-xs text-gray-400 mb-2">
              Preview (first 5 rows)
            </p>
            {preview.rows.length === 0 ? (
              <p className="text-xs text-yellow-400">
                File appears empty or has no data rows.
              </p>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-xs text-left">
                  <thead>
                    <tr>
                      {preview.headers.map((h) => (
                        <th
                          key={h}
                          className="px-3 py-2 bg-gray-700 text-gray-300 font-medium uppercase tracking-wide border-b border-gray-600"
                        >
                          {h}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {preview.rows.map((row, i) => (
                      <tr key={i} className="border-b border-gray-700/50">
                        {preview.headers.map((h) => (
                          <td
                            key={h}
                            className="px-3 py-2 text-gray-400 truncate max-w-[180px]"
                            title={row[h]}
                          >
                            {row[h] || (
                              <span className="text-gray-600 italic">—</span>
                            )}
                          </td>
                        ))}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>

          {/* Import button */}
          <div className="px-4 pb-4">
            <button
              onClick={handleImport}
              disabled={loading || preview.rows.length === 0}
              className="w-full py-2.5 rounded-md bg-blue-600 hover:bg-blue-500 disabled:bg-gray-700 disabled:text-gray-500 text-white text-sm font-medium transition-colors"
            >
              {loading ? "Importing…" : `Import ${importType}`}
            </button>
          </div>
        </div>
      )}

      {/* Error */}
      {error && (
        <div className="bg-red-900/30 border border-red-700 rounded-lg p-4">
          <p className="text-red-300 text-sm font-medium">Import failed</p>
          <p className="text-red-400 text-xs mt-1">{error}</p>
          <button
            onClick={reset}
            className="mt-3 text-xs text-red-300 hover:text-white underline"
          >
            Try again
          </button>
        </div>
      )}

      {/* Result */}
      {result && (
        <div className="bg-gray-800 border border-gray-700 rounded-lg p-5 space-y-4">
          <h2 className="text-white font-semibold">Import complete</h2>
          <div className="grid grid-cols-3 gap-4">
            <div className="bg-green-900/30 border border-green-700 rounded-md p-3 text-center">
              <div className="text-2xl font-bold text-green-400">
                {result.imported}
              </div>
              <div className="text-xs text-green-300 mt-1">Imported</div>
            </div>
            <div className="bg-yellow-900/30 border border-yellow-700 rounded-md p-3 text-center">
              <div className="text-2xl font-bold text-yellow-400">
                {result.skipped}
              </div>
              <div className="text-xs text-yellow-300 mt-1">Skipped</div>
            </div>
            <div className="bg-red-900/30 border border-red-700 rounded-md p-3 text-center">
              <div className="text-2xl font-bold text-red-400">
                {result.errors?.length ?? 0}
              </div>
              <div className="text-xs text-red-300 mt-1">Errors</div>
            </div>
          </div>

          {result.errors && result.errors.length > 0 && (
            <div className="bg-gray-700/50 rounded-md p-3">
              <p className="text-xs text-gray-300 font-medium mb-2">
                Error details
              </p>
              <ul className="space-y-1">
                {result.errors.slice(0, 10).map((e, i) => (
                  <li key={i} className="text-xs text-red-400">
                    {e}
                  </li>
                ))}
                {result.errors.length > 10 && (
                  <li className="text-xs text-gray-500">
                    +{result.errors.length - 10} more…
                  </li>
                )}
              </ul>
            </div>
          )}

          <button
            onClick={reset}
            className="w-full py-2 rounded-md bg-gray-700 hover:bg-gray-600 text-gray-300 text-sm transition-colors"
          >
            Import another file
          </button>
        </div>
      )}

      {/* Format guide */}
      <div className="bg-gray-800/50 border border-gray-700/50 rounded-lg p-4 text-xs text-gray-500 space-y-2">
        <p className="text-gray-400 font-medium">Expected CSV columns</p>
        <div className="grid grid-cols-2 gap-4">
          <div>
            <p className="text-gray-400 mb-1">Vulnerabilities</p>
            <code className="block text-gray-600">
              identifier, title, severity, cvss_score, epss_score, kev_listed,
              patch_available, published_at, description
            </code>
          </div>
          <div>
            <p className="text-gray-400 mb-1">Assets</p>
            <code className="block text-gray-600">
              identifier, name, type, criticality, exposure, environment,
              os_family, os_version, ip_addresses, tags
            </code>
          </div>
        </div>
      </div>
    </div>
  );
}
