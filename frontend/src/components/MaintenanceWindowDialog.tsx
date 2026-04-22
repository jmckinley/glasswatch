"use client";

import { useState, useEffect } from "react";
import { maintenanceWindowsApi } from "@/lib/api";

interface MaintenanceWindowDialogProps {
  isOpen: boolean;
  onClose: () => void;
  onSave: () => void;
  windowData?: any; // If editing existing window
}

const COMMON_TIMEZONES = [
  "UTC",
  "America/New_York",
  "America/Chicago",
  "America/Denver",
  "America/Los_Angeles",
  "Europe/London",
  "Europe/Paris",
  "Asia/Tokyo",
  "Asia/Shanghai",
  "Australia/Sydney",
];

const APPROVED_ACTIVITIES = [
  { value: "patching", label: "Patching" },
  { value: "updates", label: "Updates" },
  { value: "restarts", label: "Restarts" },
  { value: "migrations", label: "Migrations" },
  { value: "deployments", label: "Deployments" },
  { value: "config_changes", label: "Config Changes" },
];

export default function MaintenanceWindowDialog({
  isOpen,
  onClose,
  onSave,
  windowData,
}: MaintenanceWindowDialogProps) {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  
  // Form state
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [type, setType] = useState<"scheduled" | "emergency" | "blackout">("scheduled");
  const [startDate, setStartDate] = useState("");
  const [startTime, setStartTime] = useState("");
  const [endDate, setEndDate] = useState("");
  const [endTime, setEndTime] = useState("");
  const [timezone, setTimezone] = useState("UTC");
  const [environment, setEnvironment] = useState("");
  const [assetGroup, setAssetGroup] = useState("");
  const [serviceName, setServiceName] = useState("");
  const [isDefault, setIsDefault] = useState(false);
  const [priority, setPriority] = useState(5);
  const [maxAssets, setMaxAssets] = useState<number | "">("");
  const [maxRiskScore, setMaxRiskScore] = useState<number | "">("");
  const [maxDurationHours, setMaxDurationHours] = useState<number | "">("");
  const [approvedActivities, setApprovedActivities] = useState<string[]>(["patching"]);
  const [changeFreeze, setChangeFreeze] = useState(false);
  const [changeFreezeReason, setChangeFreezeReason] = useState("");
  const [active, setActive] = useState(true);
  
  // Load window data if editing
  useEffect(() => {
    if (windowData) {
      setName(windowData.name || "");
      setDescription(windowData.description || "");
      setType(windowData.type || "scheduled");
      
      // Parse start/end times
      if (windowData.start_time) {
        const start = new Date(windowData.start_time);
        setStartDate(start.toISOString().split("T")[0]);
        setStartTime(start.toTimeString().slice(0, 5));
      }
      if (windowData.end_time) {
        const end = new Date(windowData.end_time);
        setEndDate(end.toISOString().split("T")[0]);
        setEndTime(end.toTimeString().slice(0, 5));
      }
      
      setTimezone(windowData.timezone || "UTC");
      setEnvironment(windowData.environment || "");
      setAssetGroup(windowData.asset_group || "");
      setServiceName(windowData.service_name || "");
      setIsDefault(windowData.is_default || false);
      setPriority(windowData.priority ?? 5);
      setMaxAssets(windowData.max_assets ?? "");
      setMaxRiskScore(windowData.max_risk_score ?? "");
      setMaxDurationHours(windowData.max_duration_hours ?? "");
      setApprovedActivities(windowData.approved_activities || ["patching"]);
      setChangeFreeze(windowData.change_freeze || false);
      setChangeFreezeReason(windowData.change_freeze_reason || "");
      setActive(windowData.active ?? true);
    } else {
      // Reset form for new window
      resetForm();
    }
  }, [windowData, isOpen]);
  
  const resetForm = () => {
    setName("");
    setDescription("");
    setType("scheduled");
    setStartDate("");
    setStartTime("");
    setEndDate("");
    setEndTime("");
    setTimezone("UTC");
    setEnvironment("");
    setAssetGroup("");
    setServiceName("");
    setIsDefault(false);
    setPriority(5);
    setMaxAssets("");
    setMaxRiskScore("");
    setMaxDurationHours("");
    setApprovedActivities(["patching"]);
    setChangeFreeze(false);
    setChangeFreezeReason("");
    setActive(true);
    setError(null);
  };
  
  const calculateDuration = () => {
    if (!startDate || !startTime || !endDate || !endTime) return null;
    
    const start = new Date(`${startDate}T${startTime}`);
    const end = new Date(`${endDate}T${endTime}`);
    
    if (end <= start) return null;
    
    const durationMs = end.getTime() - start.getTime();
    const hours = Math.floor(durationMs / (1000 * 60 * 60));
    const minutes = Math.floor((durationMs % (1000 * 60 * 60)) / (1000 * 60));
    
    return { hours, minutes, total: durationMs / (1000 * 60 * 60) };
  };
  
  const getScopePreview = () => {
    const parts: string[] = [];
    
    if (isDefault) {
      return "This is the **default** fallback window (applies when no specific match exists)";
    }
    
    if (environment) parts.push(`**${environment}**`);
    if (assetGroup) parts.push(`**${assetGroup}**`);
    if (serviceName) parts.push(`**${serviceName}**`);
    
    if (parts.length === 0) {
      return "This window applies to: **all environments** (no specific scope)";
    }
    
    return `This window applies to: ${parts.join(" / ")}`;
  };
  
  const handleActivityToggle = (activity: string) => {
    setApprovedActivities(prev => 
      prev.includes(activity)
        ? prev.filter(a => a !== activity)
        : [...prev, activity]
    );
  };
  
  const handleSubmit = async () => {
    setError(null);
    
    // Validation
    if (!name.trim()) {
      setError("Name is required");
      return;
    }
    
    if (!startDate || !startTime || !endDate || !endTime) {
      setError("Start and end date/time are required");
      return;
    }
    
    const duration = calculateDuration();
    if (!duration) {
      setError("End time must be after start time");
      return;
    }
    
    if (approvedActivities.length === 0) {
      setError("At least one approved activity is required");
      return;
    }
    
    setLoading(true);
    
    try {
      const payload = {
        name,
        description: description || undefined,
        type,
        start_time: new Date(`${startDate}T${startTime}`).toISOString(),
        end_time: new Date(`${endDate}T${endTime}`).toISOString(),
        timezone,
        environment: environment || undefined,
        asset_group: assetGroup || undefined,
        service_name: serviceName || undefined,
        is_default: isDefault,
        priority,
        max_assets: maxAssets || undefined,
        max_risk_score: maxRiskScore || undefined,
        max_duration_hours: maxDurationHours || duration.total,
        approved_activities: approvedActivities,
        change_freeze: changeFreeze,
        change_freeze_reason: changeFreeze ? changeFreezeReason : undefined,
        active,
      };
      
      if (windowData) {
        // Update existing
        await maintenanceWindowsApi.update(windowData.id, payload);
      } else {
        // Create new
        await maintenanceWindowsApi.create(payload);
      }
      
      onSave();
      onClose();
      resetForm();
    } catch (err: any) {
      setError(err.message || "Failed to save maintenance window");
    } finally {
      setLoading(false);
    }
  };
  
  if (!isOpen) return null;
  
  const duration = calculateDuration();
  
  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <div className="bg-gray-800 rounded-lg shadow-xl max-w-4xl w-full max-h-[90vh] overflow-y-auto border border-gray-600">
        {/* Header */}
        <div className="sticky top-0 bg-gray-800 border-b border-gray-700 p-6 flex justify-between items-center">
          <h2 className="text-2xl font-bold">
            {windowData ? "Edit Maintenance Window" : "New Maintenance Window"}
          </h2>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-white transition-colors text-2xl"
          >
            ✕
          </button>
        </div>
        
        {/* Error Banner */}
        {error && (
          <div className="mx-6 mt-4 p-4 bg-red-500/20 border border-red-500 text-red-300 rounded-lg">
            {error}
          </div>
        )}
        
        {/* Form */}
        <div className="p-6 space-y-6">
          {/* Basic Info Section */}
          <section className="border border-gray-600 rounded-lg p-4">
            <h3 className="text-lg font-semibold mb-4 text-gray-300">Basic Information</h3>
            
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium mb-1">Name *</label>
                <input
                  type="text"
                  value={name}
                  onChange={e => setName(e.target.value)}
                  className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white focus:outline-none focus:border-primary"
                  placeholder="e.g., Weekly Production Patching"
                />
              </div>
              
              <div>
                <label className="block text-sm font-medium mb-1">Description</label>
                <textarea
                  value={description}
                  onChange={e => setDescription(e.target.value)}
                  className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white focus:outline-none focus:border-primary"
                  rows={3}
                  placeholder="Optional description..."
                />
              </div>
              
              <div>
                <label className="block text-sm font-medium mb-2">Type *</label>
                <div className="flex gap-3">
                  {[
                    { value: "scheduled", label: "Scheduled", color: "bg-blue-500/20 border-blue-500 text-blue-300" },
                    { value: "emergency", label: "Emergency", color: "bg-red-500/20 border-red-500 text-red-300" },
                    { value: "blackout", label: "Blackout", color: "bg-gray-600/20 border-gray-500 text-gray-300" },
                  ].map(({ value, label, color }) => (
                    <button
                      key={value}
                      type="button"
                      onClick={() => setType(value as any)}
                      className={`flex-1 px-4 py-2 rounded-lg border-2 transition-all ${
                        type === value
                          ? color
                          : "bg-gray-700 border-gray-600 text-gray-400 hover:border-gray-500"
                      }`}
                    >
                      {label}
                    </button>
                  ))}
                </div>
              </div>
            </div>
          </section>
          
          {/* Time Window Section */}
          <section className="border border-gray-600 rounded-lg p-4">
            <h3 className="text-lg font-semibold mb-4 text-gray-300">Time Window</h3>
            
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium mb-1">Start Date *</label>
                <input
                  type="date"
                  value={startDate}
                  onChange={e => setStartDate(e.target.value)}
                  className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white focus:outline-none focus:border-primary"
                />
              </div>
              
              <div>
                <label className="block text-sm font-medium mb-1">Start Time *</label>
                <input
                  type="time"
                  value={startTime}
                  onChange={e => setStartTime(e.target.value)}
                  className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white focus:outline-none focus:border-primary"
                />
              </div>
              
              <div>
                <label className="block text-sm font-medium mb-1">End Date *</label>
                <input
                  type="date"
                  value={endDate}
                  onChange={e => setEndDate(e.target.value)}
                  className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white focus:outline-none focus:border-primary"
                />
              </div>
              
              <div>
                <label className="block text-sm font-medium mb-1">End Time *</label>
                <input
                  type="time"
                  value={endTime}
                  onChange={e => setEndTime(e.target.value)}
                  className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white focus:outline-none focus:border-primary"
                />
              </div>
              
              <div>
                <label className="block text-sm font-medium mb-1">Timezone</label>
                <select
                  value={timezone}
                  onChange={e => setTimezone(e.target.value)}
                  className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white focus:outline-none focus:border-primary"
                >
                  {COMMON_TIMEZONES.map(tz => (
                    <option key={tz} value={tz}>{tz}</option>
                  ))}
                </select>
              </div>
              
              <div>
                <label className="block text-sm font-medium mb-1">Calculated Duration</label>
                <div className="px-3 py-2 bg-gray-700 border border-gray-600 rounded-lg text-gray-300">
                  {duration ? `${duration.hours}h ${duration.minutes}m` : "—"}
                </div>
              </div>
            </div>
          </section>
          
          {/* Scope Section */}
          <section className="border border-gray-600 rounded-lg p-4 bg-gray-750">
            <h3 className="text-lg font-semibold mb-2 text-gray-300">Scope</h3>
            <p className="text-sm text-gray-400 mb-4">
              Define what this window applies to. Higher specificity = higher priority.
            </p>
            
            <div className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium mb-1">Environment</label>
                  <input
                    type="text"
                    value={environment}
                    onChange={e => setEnvironment(e.target.value)}
                    className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white focus:outline-none focus:border-primary"
                    placeholder="e.g., production, staging"
                    disabled={isDefault}
                  />
                </div>
                
                <div>
                  <label className="block text-sm font-medium mb-1">Asset Group</label>
                  <input
                    type="text"
                    value={assetGroup}
                    onChange={e => setAssetGroup(e.target.value)}
                    className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white focus:outline-none focus:border-primary"
                    placeholder="e.g., web-servers, databases"
                    disabled={isDefault}
                  />
                </div>
              </div>
              
              <div>
                <label className="block text-sm font-medium mb-1">Service Name</label>
                <input
                  type="text"
                  value={serviceName}
                  onChange={e => setServiceName(e.target.value)}
                  className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white focus:outline-none focus:border-primary"
                  placeholder="e.g., api-gateway, payment-service"
                  disabled={isDefault}
                />
              </div>
              
              <div className="flex items-center gap-2">
                <input
                  type="checkbox"
                  id="isDefault"
                  checked={isDefault}
                  onChange={e => setIsDefault(e.target.checked)}
                  className="w-4 h-4"
                />
                <label htmlFor="isDefault" className="text-sm font-medium">
                  Default Fallback Window
                </label>
                <span className="text-xs text-gray-400">(applies when no specific match exists)</span>
              </div>
              
              <div>
                <label className="block text-sm font-medium mb-1">
                  Priority (1-10)
                  <span className="text-xs text-gray-400 ml-2">Higher priority windows override lower ones for the same scope</span>
                </label>
                <input
                  type="range"
                  min="1"
                  max="10"
                  value={priority}
                  onChange={e => setPriority(parseInt(e.target.value))}
                  className="w-full"
                />
                <div className="flex justify-between text-xs text-gray-400 mt-1">
                  <span>Low (1)</span>
                  <span className="text-primary font-semibold">{priority}</span>
                  <span>High (10)</span>
                </div>
              </div>
              
              {/* Scope Preview */}
              <div className="p-3 bg-gray-700 rounded-lg border border-gray-600">
                <div className="text-xs text-gray-400 mb-1">Scope Preview:</div>
                <div 
                  className="text-sm text-white"
                  dangerouslySetInnerHTML={{ __html: getScopePreview() }}
                />
              </div>
            </div>
          </section>
          
          {/* Constraints Section */}
          <section className="border border-gray-600 rounded-lg p-4">
            <h3 className="text-lg font-semibold mb-4 text-gray-300">Constraints</h3>
            
            <div className="grid grid-cols-3 gap-4 mb-4">
              <div>
                <label className="block text-sm font-medium mb-1">Max Assets</label>
                <input
                  type="number"
                  value={maxAssets}
                  onChange={e => setMaxAssets(e.target.value ? parseInt(e.target.value) : "")}
                  className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white focus:outline-none focus:border-primary"
                  placeholder="Unlimited"
                  min="1"
                />
              </div>
              
              <div>
                <label className="block text-sm font-medium mb-1">Max Risk Score</label>
                <input
                  type="number"
                  value={maxRiskScore}
                  onChange={e => setMaxRiskScore(e.target.value ? parseFloat(e.target.value) : "")}
                  className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white focus:outline-none focus:border-primary"
                  placeholder="Unlimited"
                  min="0"
                  step="0.1"
                />
              </div>
              
              <div>
                <label className="block text-sm font-medium mb-1">Max Duration (hours)</label>
                <input
                  type="number"
                  value={maxDurationHours}
                  onChange={e => setMaxDurationHours(e.target.value ? parseFloat(e.target.value) : "")}
                  className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white focus:outline-none focus:border-primary"
                  placeholder="Auto"
                  min="0.5"
                  step="0.5"
                />
              </div>
            </div>
            
            <div>
              <label className="block text-sm font-medium mb-2">Approved Activities *</label>
              <div className="grid grid-cols-3 gap-2">
                {APPROVED_ACTIVITIES.map(({ value, label }) => (
                  <button
                    key={value}
                    type="button"
                    onClick={() => handleActivityToggle(value)}
                    className={`px-3 py-2 rounded-lg border transition-all text-sm ${
                      approvedActivities.includes(value)
                        ? "bg-primary/20 border-primary text-primary"
                        : "bg-gray-700 border-gray-600 text-gray-400 hover:border-gray-500"
                    }`}
                  >
                    {label}
                  </button>
                ))}
              </div>
            </div>
          </section>
          
          {/* Status Section */}
          <section className="border border-gray-600 rounded-lg p-4">
            <h3 className="text-lg font-semibold mb-4 text-gray-300">Status</h3>
            
            <div className="space-y-4">
              <div className="flex items-center gap-2">
                <input
                  type="checkbox"
                  id="changeFreeze"
                  checked={changeFreeze}
                  onChange={e => setChangeFreeze(e.target.checked)}
                  className="w-4 h-4"
                />
                <label htmlFor="changeFreeze" className="text-sm font-medium">
                  Change Freeze
                </label>
                <span className="text-xs text-gray-400">(prevent new bundles from being scheduled)</span>
              </div>
              
              {changeFreeze && (
                <div>
                  <label className="block text-sm font-medium mb-1">Freeze Reason</label>
                  <textarea
                    value={changeFreezeReason}
                    onChange={e => setChangeFreezeReason(e.target.value)}
                    className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white focus:outline-none focus:border-primary"
                    rows={2}
                    placeholder="Reason for change freeze..."
                  />
                </div>
              )}
              
              <div className="flex items-center gap-2">
                <input
                  type="checkbox"
                  id="active"
                  checked={active}
                  onChange={e => setActive(e.target.checked)}
                  className="w-4 h-4"
                />
                <label htmlFor="active" className="text-sm font-medium">
                  Active
                </label>
                <span className="text-xs text-gray-400">(deactivate to hide from scheduling)</span>
              </div>
            </div>
          </section>
        </div>
        
        {/* Footer */}
        <div className="sticky bottom-0 bg-gray-800 border-t border-gray-700 p-6 flex justify-end gap-3">
          <button
            onClick={onClose}
            className="px-6 py-2 bg-gray-700 text-white rounded-lg hover:bg-gray-600 transition-colors"
            disabled={loading}
          >
            Cancel
          </button>
          <button
            onClick={handleSubmit}
            className="px-6 py-2 bg-primary text-white rounded-lg hover:bg-primary/90 transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
            disabled={loading}
          >
            {loading ? (
              <>
                <span className="inline-block animate-spin rounded-full h-4 w-4 border-b-2 border-white"></span>
                Saving...
              </>
            ) : (
              windowData ? "Update Window" : "Create Window"
            )}
          </button>
        </div>
      </div>
    </div>
  );
}
