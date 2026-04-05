import { getJSON, postJSON, patchJSON } from "../../utils/fetchHelper";
import { API } from "../endpoints/api";
import type { APIResponse } from "../../types/authType";
import type { PendingUserRead, RejectedUserRead, UserRead } from "../../types/adminTypes";
import type { Role } from "../../types/userTypes";

export async function getAllUsers(): Promise<APIResponse<UserRead[]>> {
  return getJSON<UserRead[]>(API.admin.allUsers);
}

export async function getPendingUsers(): Promise<APIResponse<PendingUserRead[]>> {
  return getJSON<PendingUserRead[]>(API.admin.allUnapprovedUsers);
}

export async function approveUser(username: string): Promise<APIResponse<UserRead>> {
  return postJSON<UserRead>(API.admin.promoteToUser(username), {});
}

export async function rejectUser(username: string): Promise<APIResponse<RejectedUserRead>> {
  return postJSON<RejectedUserRead>(API.admin.rejectUser(username), {});
}

export async function updateUserRole(username: string, role: Role): Promise<APIResponse<null>> {
  return patchJSON<null>(API.admin.updateUserPermission(username, role), {});
}