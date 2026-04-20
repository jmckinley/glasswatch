"use client";

import { useState, useEffect, useRef } from "react";
import { useAuth } from "@/contexts/AuthContext";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

interface User {
  id: string;
  full_name: string;
  email: string;
}

interface Reaction {
  emoji: string;
  user_ids: string[];
  count: number;
}

interface Comment {
  id: string;
  content: string;
  author: User;
  created_at: string;
  updated_at: string;
  parent_id: string | null;
  reactions: Reaction[];
  replies?: Comment[];
}

interface CommentThreadProps {
  entityType: string;
  entityId: string;
}

export default function CommentThread({ entityType, entityId }: CommentThreadProps) {
  const { token, user } = useAuth();
  const [comments, setComments] = useState<Comment[]>([]);
  const [newComment, setNewComment] = useState("");
  const [replyTo, setReplyTo] = useState<string | null>(null);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editContent, setEditContent] = useState("");
  const [isLoading, setIsLoading] = useState(true);
  const [showMentions, setShowMentions] = useState(false);
  const [mentionQuery, setMentionQuery] = useState("");
  const [mentionUsers, setMentionUsers] = useState<User[]>([]);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    fetchComments();
  }, [entityType, entityId, token]);

  const fetchComments = async () => {
    if (!token) return;

    setIsLoading(true);
    try {
      const response = await fetch(
        `${API_BASE_URL}/api/v1/comments?entity_type=${entityType}&entity_id=${entityId}`,
        {
          headers: {
            Authorization: `Bearer ${token}`,
          },
        }
      );

      if (response.ok) {
        const data = await response.json();
        setComments(organizeComments(data.items || data));
      }
    } catch (error) {
      console.error("Failed to fetch comments:", error);
    } finally {
      setIsLoading(false);
    }
  };

  const organizeComments = (allComments: Comment[]): Comment[] => {
    const commentMap = new Map<string, Comment>();
    const rootComments: Comment[] = [];

    // First pass: create map
    allComments.forEach((comment) => {
      commentMap.set(comment.id, { ...comment, replies: [] });
    });

    // Second pass: organize hierarchy
    allComments.forEach((comment) => {
      const commentWithReplies = commentMap.get(comment.id)!;
      if (comment.parent_id) {
        const parent = commentMap.get(comment.parent_id);
        if (parent) {
          parent.replies!.push(commentWithReplies);
        }
      } else {
        rootComments.push(commentWithReplies);
      }
    });

    return rootComments;
  };

  const handleMentionInput = (text: string) => {
    setNewComment(text);

    // Check for @ mention
    const lastAtIndex = text.lastIndexOf("@");
    if (lastAtIndex !== -1) {
      const afterAt = text.slice(lastAtIndex + 1);
      const hasSpace = afterAt.includes(" ");

      if (!hasSpace) {
        setMentionQuery(afterAt);
        setShowMentions(true);
        searchUsers(afterAt);
      } else {
        setShowMentions(false);
      }
    } else {
      setShowMentions(false);
    }
  };

  const searchUsers = async (query: string) => {
    if (!token) return;

    try {
      const response = await fetch(
        `${API_BASE_URL}/api/v1/users/search?q=${encodeURIComponent(query)}`,
        {
          headers: {
            Authorization: `Bearer ${token}`,
          },
        }
      );

      if (response.ok) {
        const data = await response.json();
        setMentionUsers(data.items || data);
      }
    } catch (error) {
      console.error("Failed to search users:", error);
    }
  };

  const insertMention = (mentionUser: User) => {
    const lastAtIndex = newComment.lastIndexOf("@");
    const before = newComment.slice(0, lastAtIndex);
    const newText = `${before}@${mentionUser.full_name} `;
    setNewComment(newText);
    setShowMentions(false);
    textareaRef.current?.focus();
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!token || !newComment.trim()) return;

    try {
      const response = await fetch(`${API_BASE_URL}/api/v1/comments`, {
        method: "POST",
        headers: {
          Authorization: `Bearer ${token}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          entity_type: entityType,
          entity_id: entityId,
          content: newComment,
          parent_id: replyTo,
        }),
      });

      if (response.ok) {
        setNewComment("");
        setReplyTo(null);
        fetchComments();
      }
    } catch (error) {
      console.error("Failed to post comment:", error);
    }
  };

  const handleEdit = async (commentId: string) => {
    if (!token || !editContent.trim()) return;

    try {
      const response = await fetch(`${API_BASE_URL}/api/v1/comments/${commentId}`, {
        method: "PATCH",
        headers: {
          Authorization: `Bearer ${token}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ content: editContent }),
      });

      if (response.ok) {
        setEditingId(null);
        setEditContent("");
        fetchComments();
      }
    } catch (error) {
      console.error("Failed to edit comment:", error);
    }
  };

  const handleDelete = async (commentId: string) => {
    if (!token || !confirm("Delete this comment?")) return;

    try {
      const response = await fetch(`${API_BASE_URL}/api/v1/comments/${commentId}`, {
        method: "DELETE",
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });

      if (response.ok) {
        fetchComments();
      }
    } catch (error) {
      console.error("Failed to delete comment:", error);
    }
  };

  const handleReaction = async (commentId: string, emoji: string) => {
    if (!token) return;

    try {
      const response = await fetch(
        `${API_BASE_URL}/api/v1/comments/${commentId}/reactions`,
        {
          method: "POST",
          headers: {
            Authorization: `Bearer ${token}`,
            "Content-Type": "application/json",
          },
          body: JSON.stringify({ emoji }),
        }
      );

      if (response.ok) {
        fetchComments();
      }
    } catch (error) {
      console.error("Failed to add reaction:", error);
    }
  };

  const formatTime = (dateString: string) => {
    const date = new Date(dateString);
    const now = new Date();
    const diff = now.getTime() - date.getTime();
    const minutes = Math.floor(diff / (1000 * 60));

    if (minutes < 60) return `${minutes}m ago`;
    const hours = Math.floor(minutes / 60);
    if (hours < 24) return `${hours}h ago`;
    const days = Math.floor(hours / 24);
    return `${days}d ago`;
  };

  const renderComment = (comment: Comment, depth: number = 0) => {
    const isAuthor = user?.id === comment.author.id;
    const isEditing = editingId === comment.id;

    return (
      <div key={comment.id} className={`${depth > 0 ? "ml-8 mt-4" : "mt-4"}`}>
        <div className="bg-gray-800 border border-gray-700 rounded-lg p-4">
          {/* Author & Time */}
          <div className="flex items-center justify-between mb-2">
            <div className="flex items-center gap-2">
              <div className="w-8 h-8 rounded-full bg-blue-600 flex items-center justify-center text-white text-sm font-semibold">
                {comment.author.full_name[0].toUpperCase()}
              </div>
              <div>
                <p className="text-sm font-medium text-white">{comment.author.full_name}</p>
                <p className="text-xs text-gray-500">{formatTime(comment.created_at)}</p>
              </div>
            </div>
            {isAuthor && !isEditing && (
              <div className="flex gap-2">
                <button
                  onClick={() => {
                    setEditingId(comment.id);
                    setEditContent(comment.content);
                  }}
                  className="text-gray-400 hover:text-white text-sm"
                >
                  Edit
                </button>
                <button
                  onClick={() => handleDelete(comment.id)}
                  className="text-gray-400 hover:text-red-400 text-sm"
                >
                  Delete
                </button>
              </div>
            )}
          </div>

          {/* Content */}
          {isEditing ? (
            <div className="space-y-2">
              <textarea
                value={editContent}
                onChange={(e) => setEditContent(e.target.value)}
                className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded text-white text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                rows={3}
              />
              <div className="flex gap-2">
                <button
                  onClick={() => handleEdit(comment.id)}
                  className="px-3 py-1 bg-blue-600 hover:bg-blue-700 text-white text-sm rounded"
                >
                  Save
                </button>
                <button
                  onClick={() => {
                    setEditingId(null);
                    setEditContent("");
                  }}
                  className="px-3 py-1 bg-gray-700 hover:bg-gray-600 text-white text-sm rounded"
                >
                  Cancel
                </button>
              </div>
            </div>
          ) : (
            <p className="text-gray-300 text-sm mb-3">{comment.content}</p>
          )}

          {/* Reactions & Actions */}
          <div className="flex items-center gap-4 text-sm">
            {/* Reactions */}
            <div className="flex gap-2">
              {comment.reactions?.map((reaction, idx) => (
                <button
                  key={idx}
                  onClick={() => handleReaction(comment.id, reaction.emoji)}
                  className={`px-2 py-1 rounded ${
                    reaction.user_ids.includes(user?.id || "")
                      ? "bg-blue-900/30 border border-blue-600"
                      : "bg-gray-700 border border-gray-600"
                  } hover:bg-gray-600 transition-colors`}
                >
                  {reaction.emoji} {reaction.count}
                </button>
              ))}
              <button
                onClick={() => handleReaction(comment.id, "👍")}
                className="px-2 py-1 rounded bg-gray-700 border border-gray-600 hover:bg-gray-600 transition-colors"
                title="Add reaction"
              >
                +
              </button>
            </div>

            {/* Reply */}
            {!isEditing && (
              <button
                onClick={() => setReplyTo(comment.id)}
                className="text-gray-400 hover:text-white"
              >
                Reply
              </button>
            )}
          </div>
        </div>

        {/* Replies */}
        {comment.replies && comment.replies.length > 0 && (
          <div className="space-y-2">
            {comment.replies.map((reply) => renderComment(reply, depth + 1))}
          </div>
        )}
      </div>
    );
  };

  if (isLoading) {
    return (
      <div className="text-center py-8">
        <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500"></div>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* Add Comment Form */}
      <form onSubmit={handleSubmit} className="bg-gray-800 border border-gray-700 rounded-lg p-4">
        {replyTo && (
          <div className="mb-2 flex items-center justify-between">
            <span className="text-sm text-gray-400">Replying to comment...</span>
            <button
              type="button"
              onClick={() => setReplyTo(null)}
              className="text-gray-400 hover:text-white text-sm"
            >
              Cancel
            </button>
          </div>
        )}
        <div className="relative">
          <textarea
            ref={textareaRef}
            value={newComment}
            onChange={(e) => handleMentionInput(e.target.value)}
            placeholder="Add a comment... (type @ to mention someone)"
            className="w-full px-4 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-blue-500"
            rows={3}
          />
          {showMentions && mentionUsers.length > 0 && (
            <div className="absolute bottom-full mb-1 w-full bg-gray-700 border border-gray-600 rounded-lg shadow-lg max-h-48 overflow-y-auto z-10">
              {mentionUsers.map((mentionUser) => (
                <button
                  key={mentionUser.id}
                  type="button"
                  onClick={() => insertMention(mentionUser)}
                  className="w-full text-left px-4 py-2 hover:bg-gray-600 text-white text-sm"
                >
                  <div className="font-medium">{mentionUser.full_name}</div>
                  <div className="text-xs text-gray-400">{mentionUser.email}</div>
                </button>
              ))}
            </div>
          )}
        </div>
        <div className="mt-3 flex justify-end">
          <button
            type="submit"
            disabled={!newComment.trim()}
            className="px-4 py-2 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-600 disabled:cursor-not-allowed text-white text-sm font-medium rounded-lg transition-colors"
          >
            Post Comment
          </button>
        </div>
      </form>

      {/* Comments List */}
      {comments.length === 0 ? (
        <p className="text-center text-gray-500 py-8">No comments yet. Be the first to comment!</p>
      ) : (
        <div className="space-y-2">
          {comments.map((comment) => renderComment(comment))}
        </div>
      )}
    </div>
  );
}
