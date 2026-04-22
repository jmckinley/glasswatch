"use client";

import { useState, useMemo, useEffect } from "react";
import { bundlesApi } from "@/lib/api";

interface MaintenanceWindow {
  id: string;
  name: string;
  description?: string;
  start_time: string;
  end_time: string;
  type: "scheduled" | "emergency" | "blackout";
  environment?: string;
  asset_group?: string;
  service_name?: string;
  priority?: number;
  duration_hours: number;
  max_assets?: number;
  max_risk_score?: number;
  scheduled_bundles: Bundle[];
}

interface Bundle {
  id: string;
  name: string;
  status: string;
  risk_score?: number;
  vulnerabilities_count?: number;
  assets_affected_count?: number;
  estimated_duration_minutes?: number;
  goal_id?: string;
  maintenance_window_id?: string;
}

interface ScheduleCalendarProps {
  windows: MaintenanceWindow[];
  onWindowUpdate: () => void;
  environments: string[];
  assetGroups: string[];
}

type ViewMode = "week" | "month";

interface WindowOverlap {
  windowId: string;
  overlappingWith: string[];
}

export default function ScheduleCalendar({
  windows,
  onWindowUpdate,
  environments,
  assetGroups,
}: ScheduleCalendarProps) {
  const [viewMode, setViewMode] = useState<ViewMode>("week");
  const [currentDate, setCurrentDate] = useState(new Date());
  const [selectedWindow, setSelectedWindow] = useState<MaintenanceWindow | null>(null);
  const [showBundlePicker, setShowBundlePicker] = useState(false);
  
  // Filters
  const [filterEnvironment, setFilterEnvironment] = useState("");
  const [filterType, setFilterType] = useState<"all" | "scheduled" | "emergency" | "blackout">("all");
  const [filterService, setFilterService] = useState("");
  const [filterAssetGroup, setFilterAssetGroup] = useState("");
  const [showOverlapsOnly, setShowOverlapsOnly] = useState(false);

  // Detect overlaps
  const overlaps = useMemo(() => {
    const result: WindowOverlap[] = [];
    
    windows.forEach((window, idx) => {
      const overlappingWith: string[] = [];
      
      windows.forEach((other, otherIdx) => {
        if (idx !== otherIdx) {
          const start1 = new Date(window.start_time).getTime();
          const end1 = new Date(window.end_time).getTime();
          const start2 = new Date(other.start_time).getTime();
          const end2 = new Date(other.end_time).getTime();
          
          // Check time overlap
          const timeOverlap = start1 < end2 && start2 < end1;
          
          // Check if same environment or service
          const sameScope =
            (window.environment && window.environment === other.environment) ||
            (window.service_name && window.service_name === other.service_name);
          
          if (timeOverlap && sameScope) {
            overlappingWith.push(other.id);
          }
        }
      });
      
      if (overlappingWith.length > 0) {
        result.push({ windowId: window.id, overlappingWith });
      }
    });
    
    return result;
  }, [windows]);

  // Filter windows
  const filteredWindows = useMemo(() => {
    let filtered = windows;
    
    if (filterEnvironment) {
      filtered = filtered.filter((w) => w.environment === filterEnvironment);
    }
    
    if (filterType !== "all") {
      filtered = filtered.filter((w) => w.type === filterType);
    }
    
    if (filterService) {
      filtered = filtered.filter((w) => w.service_name === filterService);
    }
    
    if (filterAssetGroup) {
      filtered = filtered.filter((w) => w.asset_group === filterAssetGroup);
    }
    
    if (showOverlapsOnly) {
      const overlappingIds = new Set(overlaps.map((o) => o.windowId));
      filtered = filtered.filter((w) => overlappingIds.has(w.id));
    }
    
    return filtered;
  }, [windows, filterEnvironment, filterType, filterService, filterAssetGroup, showOverlapsOnly, overlaps]);

  const handleWindowClick = (window: MaintenanceWindow) => {
    setSelectedWindow(window);
    setShowBundlePicker(false);
  };

  const handleClosePanel = () => {
    setSelectedWindow(null);
    setShowBundlePicker(false);
  };

  const handleAssignBundle = () => {
    setShowBundlePicker(true);
  };

  const serviceNames = useMemo(() => {
    const names = new Set<string>();
    windows.forEach((w) => {
      if (w.service_name) names.add(w.service_name);
    });
    return Array.from(names).sort();
  }, [windows]);

  return (
    <div className="space-y-4">
      {/* Filters */}
      <div className="card p-4">
        <div className="flex flex-wrap gap-4 items-center">
          <div className="flex items-center gap-2">
            <label className="text-sm text-neutral-400">View:</label>
            <div className="flex bg-neutral-800 rounded-lg p-1">
              <button
                onClick={() => setViewMode("week")}
                className={`px-3 py-1 text-sm rounded transition-colors ${
                  viewMode === "week"
                    ? "bg-primary text-white"
                    : "text-neutral-400 hover:text-white"
                }`}
              >
                Week
              </button>
              <button
                onClick={() => setViewMode("month")}
                className={`px-3 py-1 text-sm rounded transition-colors ${
                  viewMode === "month"
                    ? "bg-primary text-white"
                    : "text-neutral-400 hover:text-white"
                }`}
              >
                Month
              </button>
            </div>
          </div>

          <select
            value={filterEnvironment}
            onChange={(e) => setFilterEnvironment(e.target.value)}
            className="px-3 py-1.5 bg-neutral-800 border border-neutral-700 rounded text-sm"
          >
            <option value="">All Environments</option>
            {environments.map((env) => (
              <option key={env} value={env}>
                {env}
              </option>
            ))}
          </select>

          <select
            value={filterType}
            onChange={(e) => setFilterType(e.target.value as any)}
            className="px-3 py-1.5 bg-neutral-800 border border-neutral-700 rounded text-sm"
          >
            <option value="all">All Types</option>
            <option value="scheduled">Scheduled</option>
            <option value="emergency">Emergency</option>
            <option value="blackout">Blackout</option>
          </select>

          {serviceNames.length > 0 && (
            <select
              value={filterService}
              onChange={(e) => setFilterService(e.target.value)}
              className="px-3 py-1.5 bg-neutral-800 border border-neutral-700 rounded text-sm"
            >
              <option value="">All Services</option>
              {serviceNames.map((name) => (
                <option key={name} value={name}>
                  {name}
                </option>
              ))}
            </select>
          )}

          {assetGroups.length > 0 && (
            <select
              value={filterAssetGroup}
              onChange={(e) => setFilterAssetGroup(e.target.value)}
              className="px-3 py-1.5 bg-neutral-800 border border-neutral-700 rounded text-sm"
            >
              <option value="">All Asset Groups</option>
              {assetGroups.map((group) => (
                <option key={group} value={group}>
                  {group}
                </option>
              ))}
            </select>
          )}

          <label className="flex items-center gap-2 text-sm">
            <input
              type="checkbox"
              checked={showOverlapsOnly}
              onChange={(e) => setShowOverlapsOnly(e.target.checked)}
              className="rounded"
            />
            <span className="text-neutral-400">Show overlaps only</span>
          </label>
        </div>
      </div>

      {/* Calendar */}
      <div className="flex gap-4">
        <div className="flex-1">
          {viewMode === "week" ? (
            <WeekView
              windows={filteredWindows}
              currentDate={currentDate}
              onDateChange={setCurrentDate}
              onWindowClick={handleWindowClick}
              overlaps={overlaps}
            />
          ) : (
            <MonthView
              windows={filteredWindows}
              currentDate={currentDate}
              onDateChange={setCurrentDate}
              onWindowClick={handleWindowClick}
              overlaps={overlaps}
            />
          )}
        </div>

        {/* Detail Panel */}
        {selectedWindow && (
          <WindowDetailPanel
            window={selectedWindow}
            onClose={handleClosePanel}
            onUpdate={onWindowUpdate}
            onAssignBundle={handleAssignBundle}
            showBundlePicker={showBundlePicker}
            overlaps={overlaps.find((o) => o.windowId === selectedWindow.id)}
          />
        )}
      </div>
    </div>
  );
}

// Week View Component
function WeekView({
  windows,
  currentDate,
  onDateChange,
  onWindowClick,
  overlaps,
}: {
  windows: MaintenanceWindow[];
  currentDate: Date;
  onDateChange: (date: Date) => void;
  onWindowClick: (window: MaintenanceWindow) => void;
  overlaps: WindowOverlap[];
}) {
  const startOfWeek = useMemo(() => {
    const date = new Date(currentDate);
    const day = date.getDay();
    const diff = date.getDate() - day + (day === 0 ? -6 : 1); // Monday
    return new Date(date.setDate(diff));
  }, [currentDate]);

  const weekDays = useMemo(() => {
    const days = [];
    for (let i = 0; i < 7; i++) {
      const day = new Date(startOfWeek);
      day.setDate(day.getDate() + i);
      days.push(day);
    }
    return days;
  }, [startOfWeek]);

  const goToPrevWeek = () => {
    const newDate = new Date(currentDate);
    newDate.setDate(newDate.getDate() - 7);
    onDateChange(newDate);
  };

  const goToNextWeek = () => {
    const newDate = new Date(currentDate);
    newDate.setDate(newDate.getDate() + 7);
    onDateChange(newDate);
  };

  const goToThisWeek = () => {
    onDateChange(new Date());
  };

  // Position windows on the calendar
  const positionedWindows = useMemo(() => {
    const now = new Date();
    
    return windows.map((window) => {
      const start = new Date(window.start_time);
      const end = new Date(window.end_time);
      
      // Find which day(s) this window appears on
      const dayIndex = weekDays.findIndex(
        (day) =>
          day.toDateString() === start.toDateString() ||
          (start < day && end > day)
      );
      
      if (dayIndex === -1) return null;
      
      // Calculate position within the day
      const dayStart = new Date(weekDays[dayIndex]);
      dayStart.setHours(0, 0, 0, 0);
      
      const startMinutes = (start.getTime() - dayStart.getTime()) / (1000 * 60);
      const durationMinutes = (end.getTime() - start.getTime()) / (1000 * 60);
      
      const topPercent = (startMinutes / (24 * 60)) * 100;
      const heightPercent = (durationMinutes / (24 * 60)) * 100;
      
      const hasOverlap = overlaps.some((o) => o.windowId === window.id);
      
      return {
        window,
        dayIndex,
        topPercent,
        heightPercent,
        hasOverlap,
      };
    }).filter(Boolean);
  }, [windows, weekDays, overlaps]);

  const currentTimePosition = useMemo(() => {
    const now = new Date();
    const todayIndex = weekDays.findIndex(
      (day) => day.toDateString() === now.toDateString()
    );
    
    if (todayIndex === -1) return null;
    
    const dayStart = new Date(weekDays[todayIndex]);
    dayStart.setHours(0, 0, 0, 0);
    const minutes = (now.getTime() - dayStart.getTime()) / (1000 * 60);
    const topPercent = (minutes / (24 * 60)) * 100;
    
    return { dayIndex: todayIndex, topPercent };
  }, [weekDays]);

  return (
    <div className="card p-4">
      {/* Header */}
      <div className="flex justify-between items-center mb-4">
        <div className="flex items-center gap-4">
          <button
            onClick={goToPrevWeek}
            className="px-3 py-1 bg-neutral-800 hover:bg-neutral-700 rounded transition-colors"
          >
            ← Previous Week
          </button>
          <button
            onClick={goToThisWeek}
            className="px-3 py-1 bg-neutral-800 hover:bg-neutral-700 rounded transition-colors"
          >
            This Week
          </button>
          <button
            onClick={goToNextWeek}
            className="px-3 py-1 bg-neutral-800 hover:bg-neutral-700 rounded transition-colors"
          >
            Next Week →
          </button>
        </div>
        <div className="text-lg font-medium">
          {startOfWeek.toLocaleDateString("en-US", {
            month: "long",
            day: "numeric",
            year: "numeric",
          })}
          {" - "}
          {weekDays[6].toLocaleDateString("en-US", {
            month: "long",
            day: "numeric",
            year: "numeric",
          })}
        </div>
      </div>

      {/* Calendar Grid */}
      <div className="grid grid-cols-8 border-t border-l border-neutral-700">
        {/* Time column header */}
        <div className="border-r border-b border-neutral-700 bg-neutral-800 p-2 text-sm font-medium">
          Time
        </div>
        
        {/* Day headers */}
        {weekDays.map((day, idx) => (
          <div
            key={idx}
            className="border-r border-b border-neutral-700 bg-neutral-800 p-2 text-sm text-center"
          >
            <div className="font-medium">
              {day.toLocaleDateString("en-US", { weekday: "short" })}
            </div>
            <div className="text-neutral-400">
              {day.toLocaleDateString("en-US", { month: "short", day: "numeric" })}
            </div>
          </div>
        ))}

        {/* Time slots */}
        {Array.from({ length: 24 }, (_, hour) => (
          <div key={hour} className="contents">
            {/* Hour label */}
            <div className="border-r border-b border-neutral-700 bg-neutral-800/50 p-2 text-xs text-neutral-400 text-right">
              {hour.toString().padStart(2, "0")}:00
            </div>
            
            {/* Day cells */}
            {weekDays.map((day, dayIdx) => (
              <div
                key={dayIdx}
                className="border-r border-b border-neutral-700 bg-neutral-900 relative min-h-[60px]"
              >
                {/* Current time indicator */}
                {currentTimePosition &&
                  currentTimePosition.dayIndex === dayIdx &&
                  currentTimePosition.topPercent >= (hour / 24) * 100 &&
                  currentTimePosition.topPercent < ((hour + 1) / 24) * 100 && (
                    <div
                      className="absolute left-0 right-0 h-0.5 bg-red-500 z-10"
                      style={{
                        top: `${((currentTimePosition.topPercent - (hour / 24) * 100) / (1 / 24) / 100) * 100}%`,
                      }}
                    >
                      <div className="absolute -left-2 -top-1 w-2 h-2 bg-red-500 rounded-full" />
                    </div>
                  )}
              </div>
            ))}
          </div>
        ))}

        {/* Positioned windows overlay */}
        <div className="col-start-2 col-span-7 row-start-2 row-span-24 relative pointer-events-none">
          <div className="grid grid-cols-7 h-full">
            {weekDays.map((_, dayIdx) => (
              <div key={dayIdx} className="relative">
                {positionedWindows
                  ?.filter((pw: any) => pw.dayIndex === dayIdx)
                  .map((pw: any, idx: number) => (
                    <WindowBlock
                      key={pw.window.id}
                      window={pw.window}
                      topPercent={pw.topPercent}
                      heightPercent={pw.heightPercent}
                      hasOverlap={pw.hasOverlap}
                      onClick={() => onWindowClick(pw.window)}
                    />
                  ))}
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}

// Month View Component
function MonthView({
  windows,
  currentDate,
  onDateChange,
  onWindowClick,
  overlaps,
}: {
  windows: MaintenanceWindow[];
  currentDate: Date;
  onDateChange: (date: Date) => void;
  onWindowClick: (window: MaintenanceWindow) => void;
  overlaps: WindowOverlap[];
}) {
  const startOfMonth = useMemo(() => {
    const date = new Date(currentDate);
    date.setDate(1);
    return date;
  }, [currentDate]);

  const daysInMonth = useMemo(() => {
    const year = startOfMonth.getFullYear();
    const month = startOfMonth.getMonth();
    const firstDay = new Date(year, month, 1);
    const lastDay = new Date(year, month + 1, 0);
    
    const days = [];
    const startDay = firstDay.getDay();
    
    // Pad start with previous month days
    for (let i = startDay - 1; i >= 0; i--) {
      const day = new Date(firstDay);
      day.setDate(day.getDate() - (i + 1));
      days.push({ date: day, isCurrentMonth: false });
    }
    
    // Current month days
    for (let i = 1; i <= lastDay.getDate(); i++) {
      days.push({ date: new Date(year, month, i), isCurrentMonth: true });
    }
    
    // Pad end with next month days
    const remaining = 7 - (days.length % 7);
    if (remaining < 7) {
      for (let i = 1; i <= remaining; i++) {
        const day = new Date(lastDay);
        day.setDate(day.getDate() + i);
        days.push({ date: day, isCurrentMonth: false });
      }
    }
    
    return days;
  }, [startOfMonth]);

  const goToPrevMonth = () => {
    const newDate = new Date(currentDate);
    newDate.setMonth(newDate.getMonth() - 1);
    onDateChange(newDate);
  };

  const goToNextMonth = () => {
    const newDate = new Date(currentDate);
    newDate.setMonth(newDate.getMonth() + 1);
    onDateChange(newDate);
  };

  const goToThisMonth = () => {
    onDateChange(new Date());
  };

  const windowsByDay = useMemo(() => {
    const byDay = new Map<string, MaintenanceWindow[]>();
    
    windows.forEach((window) => {
      const start = new Date(window.start_time);
      const end = new Date(window.end_time);
      
      daysInMonth.forEach(({ date }) => {
        const dateKey = date.toDateString();
        const dayStart = new Date(date);
        dayStart.setHours(0, 0, 0, 0);
        const dayEnd = new Date(date);
        dayEnd.setHours(23, 59, 59, 999);
        
        if (start < dayEnd && end > dayStart) {
          if (!byDay.has(dateKey)) {
            byDay.set(dateKey, []);
          }
          byDay.get(dateKey)!.push(window);
        }
      });
    });
    
    return byDay;
  }, [windows, daysInMonth]);

  return (
    <div className="card p-4">
      {/* Header */}
      <div className="flex justify-between items-center mb-4">
        <div className="flex items-center gap-4">
          <button
            onClick={goToPrevMonth}
            className="px-3 py-1 bg-neutral-800 hover:bg-neutral-700 rounded transition-colors"
          >
            ← Previous Month
          </button>
          <button
            onClick={goToThisMonth}
            className="px-3 py-1 bg-neutral-800 hover:bg-neutral-700 rounded transition-colors"
          >
            This Month
          </button>
          <button
            onClick={goToNextMonth}
            className="px-3 py-1 bg-neutral-800 hover:bg-neutral-700 rounded transition-colors"
          >
            Next Month →
          </button>
        </div>
        <div className="text-lg font-medium">
          {startOfMonth.toLocaleDateString("en-US", {
            month: "long",
            year: "numeric",
          })}
        </div>
      </div>

      {/* Calendar Grid */}
      <div className="grid grid-cols-7 gap-px bg-neutral-700">
        {/* Day headers */}
        {["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"].map((day) => (
          <div key={day} className="bg-neutral-800 p-2 text-center text-sm font-medium">
            {day}
          </div>
        ))}

        {/* Days */}
        {daysInMonth.map(({ date, isCurrentMonth }, idx) => {
          const dateKey = date.toDateString();
          const dayWindows = windowsByDay.get(dateKey) || [];
          const isToday = date.toDateString() === new Date().toDateString();
          
          return (
            <div
              key={idx}
              className={`bg-neutral-900 p-2 min-h-[100px] ${
                !isCurrentMonth ? "opacity-50" : ""
              } ${isToday ? "ring-2 ring-primary" : ""}`}
            >
              <div className="text-sm mb-1 text-neutral-400">
                {date.getDate()}
              </div>
              <div className="space-y-1">
                {dayWindows.slice(0, 3).map((window) => {
                  const hasOverlap = overlaps.some((o) => o.windowId === window.id);
                  const typeColor =
                    window.type === "emergency"
                      ? "bg-red-600"
                      : window.type === "blackout"
                      ? "bg-neutral-600"
                      : "bg-primary";
                  
                  return (
                    <button
                      key={window.id}
                      onClick={() => onWindowClick(window)}
                      className={`w-full text-left px-2 py-1 rounded text-xs ${typeColor} hover:opacity-80 transition-opacity ${
                        hasOverlap ? "ring-2 ring-red-500 ring-dashed" : ""
                      }`}
                    >
                      <div className="truncate font-medium">{window.name}</div>
                      <div className="text-neutral-200">
                        {new Date(window.start_time).toLocaleTimeString("en-US", {
                          hour: "2-digit",
                          minute: "2-digit",
                        })}
                      </div>
                    </button>
                  );
                })}
                {dayWindows.length > 3 && (
                  <div className="text-xs text-neutral-400 text-center">
                    +{dayWindows.length - 3} more
                  </div>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

// Window Block Component (for Week View)
function WindowBlock({
  window,
  topPercent,
  heightPercent,
  hasOverlap,
  onClick,
}: {
  window: MaintenanceWindow;
  topPercent: number;
  heightPercent: number;
  hasOverlap: boolean;
  onClick: () => void;
}) {
  const typeColor =
    window.type === "emergency"
      ? "bg-red-600 hover:bg-red-700"
      : window.type === "blackout"
      ? "bg-neutral-600 hover:bg-neutral-700 bg-[repeating-linear-gradient(45deg,transparent,transparent_10px,rgba(255,255,255,0.1)_10px,rgba(255,255,255,0.1)_20px)]"
      : "bg-primary hover:bg-primary/90";

  const utilizationPercent = useMemo(() => {
    const totalDuration = window.scheduled_bundles.reduce(
      (sum, b) => sum + (b.estimated_duration_minutes || 0),
      0
    );
    const capacity = window.duration_hours * 60;
    return capacity > 0 ? (totalDuration / capacity) * 100 : 0;
  }, [window]);

  return (
    <button
      onClick={onClick}
      className={`absolute left-1 right-1 rounded px-2 py-1 text-xs text-white shadow-lg pointer-events-auto transition-all ${typeColor} ${
        hasOverlap ? "ring-2 ring-red-500 ring-dashed" : ""
      }`}
      style={{
        top: `${topPercent}%`,
        height: `${Math.max(heightPercent, 2)}%`,
      }}
    >
      <div className="font-medium truncate">{window.name}</div>
      <div className="text-neutral-200 text-[10px]">
        {new Date(window.start_time).toLocaleTimeString("en-US", {
          hour: "2-digit",
          minute: "2-digit",
        })}{" "}
        -{" "}
        {new Date(window.end_time).toLocaleTimeString("en-US", {
          hour: "2-digit",
          minute: "2-digit",
        })}
      </div>
      {window.environment && (
        <div className="inline-block px-1 py-0.5 bg-black/30 rounded text-[10px] mt-1">
          {window.environment}
        </div>
      )}
      {window.scheduled_bundles.length > 0 && (
        <div className="mt-1">
          <div className="w-full bg-black/30 rounded-full h-1 overflow-hidden">
            <div
              className="bg-white h-full transition-all"
              style={{ width: `${Math.min(utilizationPercent, 100)}%` }}
            />
          </div>
          <div className="text-[10px] mt-0.5">
            {window.scheduled_bundles.length} bundle{window.scheduled_bundles.length !== 1 ? "s" : ""}
          </div>
        </div>
      )}
    </button>
  );
}

// Window Detail Panel Component
function WindowDetailPanel({
  window,
  onClose,
  onUpdate,
  onAssignBundle,
  showBundlePicker,
  overlaps,
}: {
  window: MaintenanceWindow;
  onClose: () => void;
  onUpdate: () => void;
  onAssignBundle: () => void;
  showBundlePicker: boolean;
  overlaps?: WindowOverlap;
}) {
  const [unassigning, setUnassigning] = useState<string | null>(null);

  const utilizationMinutes = useMemo(() => {
    return window.scheduled_bundles.reduce(
      (sum, b) => sum + (b.estimated_duration_minutes || 0),
      0
    );
  }, [window.scheduled_bundles]);

  const capacityMinutes = window.duration_hours * 60;
  const utilizationPercent = (utilizationMinutes / capacityMinutes) * 100;

  const handleUnassign = async (bundleId: string) => {
    setUnassigning(bundleId);
    try {
      await bundlesApi.assignToWindow(bundleId, null);
      onUpdate();
    } catch (error) {
      console.error("Failed to unassign bundle:", error);
      alert("Failed to unassign bundle");
    } finally {
      setUnassigning(null);
    }
  };

  return (
    <div className="w-96 card p-4 space-y-4 max-h-[calc(100vh-200px)] overflow-y-auto">
      {/* Header */}
      <div className="flex justify-between items-start">
        <div>
          <h3 className="text-lg font-semibold">{window.name}</h3>
          <div className="text-sm text-neutral-400 mt-1">
            {new Date(window.start_time).toLocaleString("en-US", {
              month: "short",
              day: "numeric",
              hour: "2-digit",
              minute: "2-digit",
            })}{" "}
            -{" "}
            {new Date(window.end_time).toLocaleString("en-US", {
              month: "short",
              day: "numeric",
              hour: "2-digit",
              minute: "2-digit",
            })}
          </div>
        </div>
        <button
          onClick={onClose}
          className="text-neutral-400 hover:text-white transition-colors"
        >
          ✕
        </button>
      </div>

      {/* Window Details */}
      <div className="space-y-2 text-sm">
        <div className="flex justify-between">
          <span className="text-neutral-400">Type:</span>
          <span
            className={`px-2 py-0.5 rounded text-xs ${
              window.type === "emergency"
                ? "bg-red-600/20 text-red-400"
                : window.type === "blackout"
                ? "bg-neutral-700 text-neutral-300"
                : "bg-primary/20 text-primary"
            }`}
          >
            {window.type}
          </span>
        </div>
        {window.environment && (
          <div className="flex justify-between">
            <span className="text-neutral-400">Environment:</span>
            <span>{window.environment}</span>
          </div>
        )}
        {window.service_name && (
          <div className="flex justify-between">
            <span className="text-neutral-400">Service:</span>
            <span>{window.service_name}</span>
          </div>
        )}
        {window.asset_group && (
          <div className="flex justify-between">
            <span className="text-neutral-400">Asset Group:</span>
            <span>{window.asset_group}</span>
          </div>
        )}
      </div>

      {/* Overlap Warning */}
      {overlaps && overlaps.overlappingWith.length > 0 && (
        <div className="bg-red-900/20 border border-red-500 rounded p-3">
          <div className="text-sm text-red-400 font-medium">⚠️ Overlap Detected</div>
          <div className="text-xs text-red-300 mt-1">
            This window overlaps with {overlaps.overlappingWith.length} other window
            {overlaps.overlappingWith.length !== 1 ? "s" : ""} in the same environment/service.
          </div>
        </div>
      )}

      {/* Capacity Gauge */}
      <div>
        <div className="flex justify-between text-sm mb-2">
          <span className="text-neutral-400">Capacity:</span>
          <span>
            {(utilizationMinutes / 60).toFixed(1)}h / {window.duration_hours}h
          </span>
        </div>
        <div className="w-full bg-neutral-700 rounded-full h-3 overflow-hidden">
          <div
            className={`h-full transition-all ${
              utilizationPercent > 90
                ? "bg-red-500"
                : utilizationPercent > 80
                ? "bg-yellow-500"
                : "bg-green-500"
            }`}
            style={{ width: `${Math.min(utilizationPercent, 100)}%` }}
          />
        </div>
        <div className="text-xs text-neutral-400 mt-1">
          {utilizationPercent.toFixed(0)}% utilized
        </div>
      </div>

      {/* Assigned Bundles */}
      <div>
        <div className="flex justify-between items-center mb-2">
          <h4 className="font-medium">Assigned Bundles</h4>
          <span className="text-sm text-neutral-400">
            {window.scheduled_bundles.length}
          </span>
        </div>
        {window.scheduled_bundles.length === 0 ? (
          <div className="text-sm text-neutral-400 text-center py-4">
            No bundles assigned
          </div>
        ) : (
          <div className="space-y-2">
            {window.scheduled_bundles.map((bundle) => (
              <div
                key={bundle.id}
                className="bg-neutral-800 rounded p-3 space-y-1"
              >
                <div className="flex justify-between items-start">
                  <div className="flex-1">
                    <div className="text-sm font-medium">{bundle.name}</div>
                    <div className="text-xs text-neutral-400 mt-1">
                      {bundle.estimated_duration_minutes} min • Risk:{" "}
                      {bundle.risk_score?.toFixed(1) || "N/A"} •{" "}
                      {bundle.assets_affected_count} assets
                    </div>
                  </div>
                  <button
                    onClick={() => handleUnassign(bundle.id)}
                    disabled={unassigning === bundle.id}
                    className="text-xs text-red-400 hover:text-red-300 transition-colors disabled:opacity-50"
                  >
                    {unassigning === bundle.id ? "..." : "Unassign"}
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Assign Bundle Button */}
      <button
        onClick={onAssignBundle}
        className="w-full px-4 py-2 bg-primary hover:bg-primary/90 rounded transition-colors"
      >
        Assign Bundle
      </button>

      {/* Bundle Picker */}
      {showBundlePicker && (
        <BundlePicker
          window={window}
          onAssign={onUpdate}
          onClose={() => {}}
        />
      )}
    </div>
  );
}

// Bundle Picker Component
function BundlePicker({
  window,
  onAssign,
  onClose,
}: {
  window: MaintenanceWindow;
  onAssign: () => void;
  onClose: () => void;
}) {
  const [bundles, setBundles] = useState<Bundle[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [assigning, setAssigning] = useState<string | null>(null);

  useEffect(() => {
    loadUnassignedBundles();
  }, []);

  const loadUnassignedBundles = async () => {
    try {
      setLoading(true);
      const response = await bundlesApi.list({
        maintenance_window_id: "unassigned",
        limit: 200,
      });
      setBundles(response.items || []);
    } catch (error) {
      console.error("Failed to load bundles:", error);
    } finally {
      setLoading(false);
    }
  };

  const filteredBundles = useMemo(() => {
    if (!search) return bundles;
    const lower = search.toLowerCase();
    return bundles.filter((b) => b.name.toLowerCase().includes(lower));
  }, [bundles, search]);

  const handleAssign = async (bundleId: string) => {
    setAssigning(bundleId);
    try {
      await bundlesApi.assignToWindow(bundleId, window.id);
      onAssign();
    } catch (error: any) {
      console.error("Failed to assign bundle:", error);
      alert(error.data?.detail || "Failed to assign bundle");
    } finally {
      setAssigning(null);
    }
  };

  const calculateFit = (bundle: Bundle) => {
    const currentUtilization = window.scheduled_bundles.reduce(
      (sum, b) => sum + (b.estimated_duration_minutes || 0),
      0
    );
    const capacity = window.duration_hours * 60;
    const remaining = capacity - currentUtilization;
    const bundleDuration = bundle.estimated_duration_minutes || 0;

    if (bundleDuration > remaining) {
      return { status: "exceeds", message: "Exceeds capacity" };
    }

    if (window.max_risk_score && bundle.risk_score && bundle.risk_score > window.max_risk_score) {
      return { status: "exceeds", message: "Risk too high" };
    }

    const currentAssets = window.scheduled_bundles.reduce(
      (sum, b) => sum + (b.assets_affected_count || 0),
      0
    );
    if (window.max_assets) {
      const newTotal = currentAssets + (bundle.assets_affected_count || 0);
      if (newTotal > window.max_assets) {
        return { status: "exceeds", message: "Too many assets" };
      }
    }

    const utilizationPercent = ((currentUtilization + bundleDuration) / capacity) * 100;
    if (utilizationPercent > 80) {
      return { status: "tight", message: "Tight fit" };
    }

    return { status: "fits", message: "Fits well" };
  };

  return (
    <div className="border-t border-neutral-700 pt-4 mt-4">
      <h4 className="font-medium mb-3">Select Bundle to Assign</h4>

      <input
        type="text"
        placeholder="Search bundles..."
        value={search}
        onChange={(e) => setSearch(e.target.value)}
        className="w-full px-3 py-2 bg-neutral-800 border border-neutral-700 rounded mb-3"
      />

      {loading ? (
        <div className="text-center text-neutral-400 py-8">Loading bundles...</div>
      ) : filteredBundles.length === 0 ? (
        <div className="text-center text-neutral-400 py-8">
          {search ? "No bundles match your search" : "No unassigned bundles available"}
        </div>
      ) : (
        <div className="space-y-2 max-h-[400px] overflow-y-auto">
          {filteredBundles.map((bundle) => {
            const fit = calculateFit(bundle);
            const fitIcon =
              fit.status === "fits" ? "✅" : fit.status === "tight" ? "⚠️" : "❌";

            return (
              <div
                key={bundle.id}
                className="bg-neutral-800 rounded p-3 space-y-2"
              >
                <div className="flex justify-between items-start">
                  <div className="flex-1">
                    <div className="text-sm font-medium">{bundle.name}</div>
                    <div className="text-xs text-neutral-400 mt-1">
                      {bundle.estimated_duration_minutes} min • Risk:{" "}
                      {bundle.risk_score?.toFixed(1) || "N/A"} •{" "}
                      {bundle.assets_affected_count} assets
                    </div>
                  </div>
                  <div className="text-lg">{fitIcon}</div>
                </div>
                <div className="flex justify-between items-center">
                  <div
                    className={`text-xs ${
                      fit.status === "fits"
                        ? "text-green-400"
                        : fit.status === "tight"
                        ? "text-yellow-400"
                        : "text-red-400"
                    }`}
                  >
                    {fit.message}
                  </div>
                  <button
                    onClick={() => handleAssign(bundle.id)}
                    disabled={fit.status === "exceeds" || assigning === bundle.id}
                    className="px-3 py-1 bg-primary hover:bg-primary/90 rounded text-xs transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    {assigning === bundle.id ? "Assigning..." : "Assign"}
                  </button>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
