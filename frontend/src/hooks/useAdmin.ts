import { useState, useEffect, useCallback } from "react";
import {
  getAllUsers,
  getPendingUsers,
  approveUser,
  rejectUser,
  updateUserRole,
} from "../services/admin/adminService";
import type { UserRead, PendingUserRead } from "../types/adminTypes";
import type { Role } from "../types/userTypes";

interface UseAdminResult {
  users: UserRead[]
  pendingUsers: PendingUserRead[]
  usersLoading: boolean
  pendingLoading: boolean
  error: string | null
  // actions
  approve: (username: string) => Promise<void>
  reject: (username: string) => Promise<void>
  changeRole: (username: string, role: Role) => Promise<void>
  actionError: string | null
  actionSuccess: string | null
}

export function useAdmin(currentUsername: string): UseAdminResult {
  const [users, setUsers] = useState<UserRead[]>([]);
  const [pendingUsers, setPendingUsers] = useState<PendingUserRead[]>([]);
  const [usersLoading, setUsersLoading] = useState(true);
  const [pendingLoading, setPendingLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);
  const [actionSuccess, setActionSuccess] = useState<string | null>(null);

  useEffect(() => {
    async function fetchUsers() {
      setUsersLoading(true);
      const res = await getAllUsers();
      if (res.ok && res.data) setUsers(res.data.filter((u) => u.username !== currentUsername));
      else setError(res.error ?? "Failed to load users");
      setUsersLoading(false);
    }
    fetchUsers();
  }, []);

  useEffect(() => {
    async function fetchPending() {
      setPendingLoading(true);
      const res = await getPendingUsers();
      if (res.ok && res.data) setPendingUsers(res.data);
      else setError(res.error ?? "Failed to load pending users");
      setPendingLoading(false);
    }
    fetchPending();
  }, []);

  const clearMessages = () => {
    setActionError(null);
    setActionSuccess(null);
  };

  const approve = useCallback(async (username: string) => {
    clearMessages();
    const res = await approveUser(username);
    if (!res.ok) {
      setActionError(res.error ?? "Failed to approve user");
      return;
    }
    // Remove from pending, add to users list
    setPendingUsers((prev) => prev.filter((u) => u.username !== username));
    if (res.data) setUsers((prev) => [...prev, res.data!]);
    setActionSuccess(`${username} approved`);
  }, []);

  const reject = useCallback(async (username: string) => {
    clearMessages();
    const res = await rejectUser(username);
    if (!res.ok) {
      setActionError(res.error ?? "Failed to reject user");
      return;
    }
    // Remove from pending list
    setPendingUsers((prev) => prev.filter((u) => u.username !== username));
    setActionSuccess(`${username} rejected`);
  }, []);

  const changeRole = useCallback(async (username: string, role: Role) => {
    clearMessages();
    const res = await updateUserRole(username, role);
    if (!res.ok) {
      setActionError(res.error ?? "Failed to update role");
      return;
    }
    setUsers((prev) =>
      prev.map((u) => (u.username === username ? { ...u, role } : u))
    );
    setActionSuccess(`${username} role updated to ${role}`);
  }, []);

  return {
    users,
    pendingUsers,
    usersLoading,
    pendingLoading,
    error,
    approve,
    reject,
    changeRole,
    actionError,
    actionSuccess,
  };
}