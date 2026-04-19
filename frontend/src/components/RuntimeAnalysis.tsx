"use client";

import { useState } from "react";
import { Activity, AlertCircle, CheckCircle, XCircle, Info } from "lucide-react";

interface RuntimeData {
  vulnerability_id: string;
  code_executed: boolean;
  library_loaded: boolean;
  function_called: boolean;
  execution_frequency: number;
  last_seen: string;
  confidence: number;
  impact_score: number;
}

interface RuntimeAnalysisProps {
  vulnerabilityId: string;
  runtimeData?: RuntimeData;
  showDetails?: boolean;
}

export function RuntimeAnalysis({ vulnerabilityId, runtimeData, showDetails = true }: RuntimeAnalysisProps) {
  const [isExpanded, setIsExpanded] = useState(false);

  // Mock data if not provided
  const data = runtimeData || {
    vulnerability_id: vulnerabilityId,
    code_executed: Math.random() > 0.5,
    library_loaded: Math.random() > 0.3,
    function_called: Math.random() > 0.7,
    execution_frequency: Math.floor(Math.random() * 1000),
    last_seen: new Date(Date.now() - Math.random() * 86400000 * 30).toISOString(),
    confidence: Math.floor(Math.random() * 40) + 60,
    impact_score: Math.floor(Math.random() * 25) - 10,
  };

  const getStatusIcon = () => {
    if (data.code_executed) {
      return <AlertCircle className="w-5 h-5 text-destructive" />;
    } else if (data.library_loaded) {
      return <Info className="w-5 h-5 text-warning" />;
    } else {
      return <CheckCircle className="w-5 h-5 text-success" />;
    }
  };

  const getStatusText = () => {
    if (data.code_executed) {
      return "Code Actively Executed";
    } else if (data.library_loaded) {
      return "Library Loaded";
    } else {
      return "Not in Runtime Path";
    }
  };

  const getImpactBadge = () => {
    const impact = data.impact_score;
    if (impact > 10) {
      return (
        <span className="px-2 py-1 text-xs rounded bg-destructive/20 text-destructive">
          +{impact} pts
        </span>
      );
    } else if (impact < -5) {
      return (
        <span className="px-2 py-1 text-xs rounded bg-success/20 text-success">
          {impact} pts
        </span>
      );
    } else {
      return (
        <span className="px-2 py-1 text-xs rounded bg-neutral-700 text-neutral-300">
          {impact > 0 ? "+" : ""}{impact} pts
        </span>
      );
    }
  };

  return (
    <div className="bg-neutral-900 rounded-lg p-4">
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2">
          <Activity className="w-4 h-4 text-primary" />
          <span className="text-sm font-medium">Snapper Runtime Analysis</span>
        </div>
        {getImpactBadge()}
      </div>

      <div className="flex items-center gap-2 mb-3">
        {getStatusIcon()}
        <span className="text-sm font-medium">{getStatusText()}</span>
        <span className="text-xs text-neutral-400">
          ({data.confidence}% confidence)
        </span>
      </div>

      {showDetails && (
        <button
          onClick={() => setIsExpanded(!isExpanded)}
          className="text-xs text-primary hover:underline"
        >
          {isExpanded ? "Hide details" : "Show details"}
        </button>
      )}

      {isExpanded && (
        <div className="mt-4 space-y-3 text-sm">
          <div className="grid grid-cols-2 gap-4">
            <div>
              <span className="text-neutral-400">Code Executed:</span>
              <div className="flex items-center gap-1 mt-1">
                {data.code_executed ? (
                  <XCircle className="w-4 h-4 text-destructive" />
                ) : (
                  <CheckCircle className="w-4 h-4 text-success" />
                )}
                <span>{data.code_executed ? "Yes" : "No"}</span>
              </div>
            </div>
            
            <div>
              <span className="text-neutral-400">Library Loaded:</span>
              <div className="flex items-center gap-1 mt-1">
                {data.library_loaded ? (
                  <AlertCircle className="w-4 h-4 text-warning" />
                ) : (
                  <CheckCircle className="w-4 h-4 text-success" />
                )}
                <span>{data.library_loaded ? "Yes" : "No"}</span>
              </div>
            </div>

            <div>
              <span className="text-neutral-400">Function Called:</span>
              <div className="flex items-center gap-1 mt-1">
                {data.function_called ? (
                  <AlertCircle className="w-4 h-4 text-warning" />
                ) : (
                  <CheckCircle className="w-4 h-4 text-success" />
                )}
                <span>{data.function_called ? "Yes" : "No"}</span>
              </div>
            </div>

            <div>
              <span className="text-neutral-400">Execution Frequency:</span>
              <div className="mt-1">
                {data.execution_frequency > 0 ? (
                  <span className="text-warning">{data.execution_frequency} times/day</span>
                ) : (
                  <span className="text-success">Never</span>
                )}
              </div>
            </div>
          </div>

          <div>
            <span className="text-neutral-400">Last Seen:</span>
            <div className="mt-1">
              {data.execution_frequency > 0 ? (
                <span>{new Date(data.last_seen).toLocaleDateString()}</span>
              ) : (
                <span className="text-neutral-500">N/A</span>
              )}
            </div>
          </div>

          <div className="mt-4 p-3 bg-neutral-800 rounded-lg">
            <h4 className="text-sm font-medium mb-2">Impact on Score</h4>
            <div className="space-y-1 text-xs">
              {data.code_executed && (
                <div className="text-destructive">
                  • Code actively running: +15 points
                </div>
              )}
              {!data.code_executed && data.library_loaded && (
                <div className="text-neutral-400">
                  • Library present but unused: +0 points
                </div>
              )}
              {!data.library_loaded && (
                <div className="text-success">
                  • Not in runtime path: -10 points
                </div>
              )}
            </div>
            <div className="mt-2 pt-2 border-t border-neutral-700">
              <span className="text-xs text-neutral-400">Total adjustment: </span>
              <span className="text-xs font-medium">
                {data.impact_score > 0 ? "+" : ""}{data.impact_score} points
              </span>
            </div>
          </div>

          <div className="text-xs text-neutral-400 italic">
            Data provided by Snapper runtime analysis engine
          </div>
        </div>
      )}
    </div>
  );
}