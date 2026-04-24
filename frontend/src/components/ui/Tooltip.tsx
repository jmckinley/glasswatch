"use client";

import { ReactNode } from "react";

interface TooltipProps {
  content: string;
  children: ReactNode;
  /** Position relative to the trigger. Default: "top" */
  position?: "top" | "bottom";
}

/**
 * Lightweight hover tooltip. Wraps any inline element.
 * Usage:
 *   <Tooltip content="EPSS is the probability a CVE gets exploited in the next 30 days.">
 *     <span>EPSS ⓘ</span>
 *   </Tooltip>
 */
export function Tooltip({ content, children, position = "top" }: TooltipProps) {
  const above = position === "top";
  return (
    <span className="relative group inline-flex items-center cursor-default">
      {children}
      <span
        className={`
          absolute ${above ? "bottom-full mb-2" : "top-full mt-2"}
          left-1/2 -translate-x-1/2
          px-2.5 py-1.5 text-xs bg-gray-900 text-gray-200 rounded-lg
          border border-gray-700 whitespace-normal max-w-[220px] text-center
          opacity-0 group-hover:opacity-100 pointer-events-none
          transition-opacity duration-150 z-50 shadow-xl
        `}
      >
        {content}
        {/* Arrow */}
        <span
          className={`
            absolute left-1/2 -translate-x-1/2
            ${above ? "top-full border-t-gray-700" : "bottom-full border-b-gray-700"}
            border-4 border-transparent
          `}
        />
      </span>
    </span>
  );
}
