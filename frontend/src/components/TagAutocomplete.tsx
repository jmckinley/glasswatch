"use client";

import { useState, useEffect, useCallback } from "react";
import { tagsApi } from "@/lib/api";

interface Tag {
  id: string;
  name: string;
  namespace: string;
  display_name: string;
  color: string | null;
  description: string | null;
}

interface TagAutocompleteProps {
  value: string[];
  onChange: (tags: string[]) => void;
  namespace?: string;
  placeholder?: string;
  className?: string;
}

export default function TagAutocomplete({
  value,
  onChange,
  namespace,
  placeholder = "Add tags...",
  className = "",
}: TagAutocompleteProps) {
  const [inputValue, setInputValue] = useState("");
  const [suggestions, setSuggestions] = useState<Tag[]>([]);
  const [showSuggestions, setShowSuggestions] = useState(false);
  const [loading, setLoading] = useState(false);
  const [createDialogOpen, setCreateDialogOpen] = useState(false);
  const [newTagNamespace, setNewTagNamespace] = useState("system");
  const [newTagColor, setNewTagColor] = useState("#3B82F6");

  // Debounced search
  useEffect(() => {
    if (!inputValue.trim()) {
      setSuggestions([]);
      setShowSuggestions(false);
      return;
    }

    const timer = setTimeout(async () => {
      try {
        setLoading(true);
        const params: any = { q: inputValue, limit: 10 };
        if (namespace) {
          params.namespace = namespace;
        }
        const results = await tagsApi.suggest(params);
        setSuggestions(results);
        setShowSuggestions(true);
      } catch (error) {
        console.error("Failed to fetch tag suggestions:", error);
      } finally {
        setLoading(false);
      }
    }, 300);

    return () => clearTimeout(timer);
  }, [inputValue, namespace]);

  const handleAddTag = (tag: string) => {
    if (!value.includes(tag)) {
      onChange([...value, tag]);
    }
    setInputValue("");
    setShowSuggestions(false);
  };

  const handleRemoveTag = (tag: string) => {
    onChange(value.filter((t) => t !== tag));
  };

  const handleCreateNew = async () => {
    try {
      const newTag = await tagsApi.create({
        name: inputValue,
        namespace: newTagNamespace,
        color: newTagColor,
      });
      handleAddTag(newTag.display_name);
      setCreateDialogOpen(false);
      setInputValue("");
    } catch (error) {
      console.error("Failed to create tag:", error);
      alert("Failed to create tag");
    }
  };

  const getTagColor = (tag: string) => {
    // Simple hash function to get consistent colors
    let hash = 0;
    for (let i = 0; i < tag.length; i++) {
      hash = tag.charCodeAt(i) + ((hash << 5) - hash);
    }
    const colors = [
      "bg-blue-500/20 text-blue-300 border-blue-500/30",
      "bg-green-500/20 text-green-300 border-green-500/30",
      "bg-purple-500/20 text-purple-300 border-purple-500/30",
      "bg-yellow-500/20 text-yellow-300 border-yellow-500/30",
      "bg-pink-500/20 text-pink-300 border-pink-500/30",
      "bg-cyan-500/20 text-cyan-300 border-cyan-500/30",
      "bg-orange-500/20 text-orange-300 border-orange-500/30",
      "bg-red-500/20 text-red-300 border-red-500/30",
    ];
    return colors[Math.abs(hash) % colors.length];
  };

  return (
    <div className={`relative ${className}`}>
      {/* Selected tags */}
      <div className="flex flex-wrap gap-2 mb-2">
        {value.map((tag) => (
          <span
            key={tag}
            className={`inline-flex items-center gap-1 px-2 py-1 rounded-md text-xs border ${getTagColor(tag)}`}
          >
            {tag}
            <button
              type="button"
              onClick={() => handleRemoveTag(tag)}
              className="hover:text-white"
            >
              ×
            </button>
          </span>
        ))}
      </div>

      {/* Input */}
      <div className="relative">
        <input
          type="text"
          value={inputValue}
          onChange={(e) => setInputValue(e.target.value)}
          onFocus={() => setShowSuggestions(true)}
          placeholder={placeholder}
          className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-md text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500"
        />

        {/* Suggestions dropdown */}
        {showSuggestions && (inputValue.trim() || suggestions.length > 0) && (
          <div className="absolute z-10 w-full mt-1 bg-gray-800 border border-gray-700 rounded-md shadow-lg max-h-60 overflow-y-auto">
            {loading ? (
              <div className="px-4 py-3 text-sm text-gray-400">Loading...</div>
            ) : suggestions.length > 0 ? (
              <>
                {suggestions.map((tag) => (
                  <button
                    key={tag.id}
                    type="button"
                    onClick={() => handleAddTag(tag.display_name)}
                    className="w-full px-4 py-2 text-left hover:bg-gray-700 flex items-center gap-2"
                  >
                    <span
                      className="w-3 h-3 rounded-full"
                      style={{ backgroundColor: tag.color || "#3B82F6" }}
                    />
                    <span className="text-white text-sm">{tag.display_name}</span>
                    {tag.description && (
                      <span className="text-gray-400 text-xs ml-auto truncate">
                        {tag.description}
                      </span>
                    )}
                  </button>
                ))}
                {inputValue.trim() && (
                  <button
                    type="button"
                    onClick={() => setCreateDialogOpen(true)}
                    className="w-full px-4 py-2 text-left hover:bg-gray-700 text-blue-400 text-sm border-t border-gray-700"
                  >
                    + Create &quot;{inputValue}&quot;
                  </button>
                )}
              </>
            ) : inputValue.trim() ? (
              <button
                type="button"
                onClick={() => setCreateDialogOpen(true)}
                className="w-full px-4 py-2 text-left hover:bg-gray-700 text-blue-400 text-sm"
              >
                + Create &quot;{inputValue}&quot;
              </button>
            ) : null}
          </div>
        )}
      </div>

      {/* Create tag dialog */}
      {createDialogOpen && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-gray-800 rounded-lg p-6 max-w-md w-full mx-4">
            <h3 className="text-lg font-semibold text-white mb-4">
              Create New Tag
            </h3>
            
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-300 mb-1">
                  Tag Name
                </label>
                <input
                  type="text"
                  value={inputValue}
                  onChange={(e) => setInputValue(e.target.value)}
                  className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-md text-white"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-300 mb-1">
                  Namespace
                </label>
                <select
                  value={newTagNamespace}
                  onChange={(e) => setNewTagNamespace(e.target.value)}
                  className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-md text-white"
                >
                  <option value="system">system</option>
                  <option value="compliance">compliance</option>
                  <option value="env">env</option>
                  <option value="tier">tier</option>
                  <option value="team">team</option>
                </select>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-300 mb-1">
                  Color
                </label>
                <input
                  type="color"
                  value={newTagColor}
                  onChange={(e) => setNewTagColor(e.target.value)}
                  className="w-full h-10 bg-gray-700 border border-gray-600 rounded-md"
                />
              </div>
            </div>

            <div className="flex gap-3 mt-6">
              <button
                onClick={handleCreateNew}
                className="flex-1 px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700"
              >
                Create
              </button>
              <button
                onClick={() => {
                  setCreateDialogOpen(false);
                  setInputValue("");
                }}
                className="flex-1 px-4 py-2 bg-gray-700 text-white rounded-md hover:bg-gray-600"
              >
                Cancel
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
