"use client";

import { useState, useEffect, useCallback } from "react";
import { apiCall } from "@/lib/api";

interface TeamMember {
  id: string;
  name: string;
  email: string;
  role: string;
  created_at: string;
}

interface PendingInvite {
  id: string;
  email: string;
  role: string;
  created_at: string;
  expires_at: string;
}

const ROLE_BADGE: Record<string, string> = {
  admin: "bg-purple-900/40 text-purple-300 border border-purple-700",
  operator: "bg-blue-900/40 text-blue-300 border border-blue-700",
  analyst: "bg-green-900/40 text-green-300 border border-green-700",
  viewer: "bg-gray-700 text-gray-300 border border-gray-600",
};

function RoleBadge({ role }: { role: string }) {
  const classes = ROLE_BADGE[role] || ROLE_BADGE.viewer;
  return (
    <span className={`px-2 py-0.5 rounded text-xs font-medium capitalize ${classes}`}>
      {role}
    </span>
  );
}

function formatDate(iso: string) {
  try {
    return new Date(iso).toLocaleDateString("en-US", {
      year: "numeric",
      month: "short",
      day: "numeric",
    });
  } catch {
    return iso;
  }
}

export default function TeamSettingsPage() {
  const [members, setMembers] = useState<TeamMember[]>([]);
  const [invites, setInvites] = useState<PendingInvite[]>([]);
  const [loadingMembers, setLoadingMembers] = useState(true);
  const [loadingInvites, setLoadingInvites] = useState(true);
  const [membersError, setMembersError] = useState<string | null>(null);
  const [invitesError, setInvitesError] = useState<string | null>(null);

  // Invite form state
  const [inviteEmail, setInviteEmail] = useState("");
  const [inviteRole, setInviteRole] = useState("viewer");
  const [sendingInvite, setSendingInvite] = useState(false);
  const [inviteSuccess, setInviteSuccess] = useState<string | null>(null);
  const [inviteError, setInviteError] = useState<string | null>(null);

  const loadMembers = useCallback(async () => {
    setLoadingMembers(true);
    setMembersError(null);
    try {
      const data = await apiCall<TeamMember[]>("/users");
      setMembers(data);
    } catch (e: any) {
      setMembersError(e.message || "Failed to load team members.");
    } finally {
      setLoadingMembers(false);
    }
  }, []);

  const loadInvites = useCallback(async () => {
    setLoadingInvites(true);
    setInvitesError(null);
    try {
      const data = await apiCall<PendingInvite[]>("/invites");
      setInvites(data);
    } catch (e: any) {
      setInvitesError(e.message || "Failed to load invites.");
    } finally {
      setLoadingInvites(false);
    }
  }, []);

  useEffect(() => {
    loadMembers();
    loadInvites();
  }, [loadMembers, loadInvites]);

  const handleRevoke = async (inviteId: string) => {
    try {
      await apiCall(`/invites/${inviteId}`, { method: "DELETE" });
      setInvites((prev) => prev.filter((i) => i.id !== inviteId));
    } catch (e: any) {
      alert(`Failed to revoke invite: ${e.message}`);
    }
  };

  const handleSendInvite = async (e: React.FormEvent) => {
    e.preventDefault();
    setSendingInvite(true);
    setInviteError(null);
    setInviteSuccess(null);
    try {
      await apiCall("/invites", {
        method: "POST",
        body: { email: inviteEmail, role: inviteRole },
      });
      setInviteSuccess(`Invite sent to ${inviteEmail}`);
      setInviteEmail("");
      setInviteRole("viewer");
      // Refresh invites list
      await loadInvites();
    } catch (e: any) {
      setInviteError(e.message || "Failed to send invite.");
    } finally {
      setSendingInvite(false);
    }
  };

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-3xl font-bold text-white mb-2">Team</h1>
        <p className="text-gray-400">Manage team members and send invitations.</p>
      </div>

      {/* Team Members */}
      <div className="bg-gray-800 rounded-lg border border-gray-700 overflow-hidden">
        <div className="px-6 py-4 border-b border-gray-700">
          <h2 className="text-lg font-semibold text-white">Team Members</h2>
        </div>
        {loadingMembers ? (
          <div className="px-6 py-8 text-center text-gray-400">Loading members…</div>
        ) : membersError ? (
          <div className="px-6 py-4 text-red-400 text-sm">{membersError}</div>
        ) : members.length === 0 ? (
          <div className="px-6 py-8 text-center text-gray-500">No team members found.</div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-gray-700 text-gray-400 text-left">
                  <th className="px-6 py-3 font-medium">Name</th>
                  <th className="px-6 py-3 font-medium">Email</th>
                  <th className="px-6 py-3 font-medium">Role</th>
                  <th className="px-6 py-3 font-medium">Joined</th>
                </tr>
              </thead>
              <tbody>
                {members.map((member) => (
                  <tr key={member.id} className="border-b border-gray-700/50 hover:bg-gray-700/20">
                    <td className="px-6 py-3 text-white font-medium">{member.name}</td>
                    <td className="px-6 py-3 text-gray-300">{member.email}</td>
                    <td className="px-6 py-3">
                      <RoleBadge role={member.role} />
                    </td>
                    <td className="px-6 py-3 text-gray-400">{formatDate(member.created_at)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Pending Invites */}
      <div className="bg-gray-800 rounded-lg border border-gray-700 overflow-hidden">
        <div className="px-6 py-4 border-b border-gray-700">
          <h2 className="text-lg font-semibold text-white">Pending Invites</h2>
        </div>
        {loadingInvites ? (
          <div className="px-6 py-8 text-center text-gray-400">Loading invites…</div>
        ) : invitesError ? (
          <div className="px-6 py-4 text-red-400 text-sm">{invitesError}</div>
        ) : invites.length === 0 ? (
          <div className="px-6 py-8 text-center text-gray-500">No pending invites.</div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-gray-700 text-gray-400 text-left">
                  <th className="px-6 py-3 font-medium">Email</th>
                  <th className="px-6 py-3 font-medium">Role</th>
                  <th className="px-6 py-3 font-medium">Sent</th>
                  <th className="px-6 py-3 font-medium">Expires</th>
                  <th className="px-6 py-3 font-medium">Action</th>
                </tr>
              </thead>
              <tbody>
                {invites.map((invite) => (
                  <tr key={invite.id} className="border-b border-gray-700/50 hover:bg-gray-700/20">
                    <td className="px-6 py-3 text-gray-300">{invite.email}</td>
                    <td className="px-6 py-3">
                      <RoleBadge role={invite.role} />
                    </td>
                    <td className="px-6 py-3 text-gray-400">{formatDate(invite.created_at)}</td>
                    <td className="px-6 py-3 text-gray-400">{formatDate(invite.expires_at)}</td>
                    <td className="px-6 py-3">
                      <button
                        onClick={() => handleRevoke(invite.id)}
                        className="px-3 py-1 text-xs bg-red-900/30 hover:bg-red-900/60 text-red-400 border border-red-700/50 rounded transition-colors"
                      >
                        Revoke
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Invite Member Form */}
      <div className="bg-gray-800 rounded-lg border border-gray-700 overflow-hidden">
        <div className="px-6 py-4 border-b border-gray-700">
          <h2 className="text-lg font-semibold text-white">Invite Member</h2>
        </div>
        <div className="px-6 py-6">
          {inviteSuccess && (
            <div className="mb-4 p-3 bg-green-900/20 border border-green-700 rounded-lg text-green-400 text-sm">
              {inviteSuccess}
            </div>
          )}
          {inviteError && (
            <div className="mb-4 p-3 bg-red-900/20 border border-red-700 rounded-lg text-red-400 text-sm">
              {inviteError}
            </div>
          )}
          <form onSubmit={handleSendInvite} className="flex flex-col sm:flex-row gap-3">
            <input
              type="email"
              value={inviteEmail}
              onChange={(e) => setInviteEmail(e.target.value)}
              required
              placeholder="colleague@company.com"
              className="flex-1 px-4 py-2 bg-gray-700 border border-gray-600 text-white rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 placeholder-gray-500"
            />
            <select
              value={inviteRole}
              onChange={(e) => setInviteRole(e.target.value)}
              className="px-4 py-2 bg-gray-700 border border-gray-600 text-white rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value="viewer">Viewer — read-only</option>
              <option value="analyst">Analyst — create goals/bundles</option>
              <option value="operator">Operator — execute patches</option>
              <option value="admin">Admin — full access</option>
            </select>
            <button
              type="submit"
              disabled={sendingInvite || !inviteEmail}
              className="px-6 py-2 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-600 disabled:cursor-not-allowed text-white font-semibold rounded-lg transition-colors whitespace-nowrap"
            >
              {sendingInvite ? "Sending…" : "Send Invite"}
            </button>
          </form>
          <p className="text-gray-500 text-xs mt-3">
            The invitee will receive an email with a link to set up their account. Links expire after 7 days.
          </p>
        </div>
      </div>
    </div>
  );
}
