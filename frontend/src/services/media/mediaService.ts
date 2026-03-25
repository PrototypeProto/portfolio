import { getJSON, postJSON } from "../../utils/fetchHelper"
import { API } from "../../services/endpoints/api"
import type { APIResponse } from "../../types/authType"
import type { MediaListResponse } from "../../types/mediaType"

export async function getMediaList(
  page: number,
  token: string,
): Promise<APIResponse<MediaListResponse>> {
  return postJSON<MediaListResponse>(API.media.list, { page }, token)
}

// Returns a blob URL you can pass directly to a <video> src
export async function getMediaFile(
  filename: string,
  token: string,
): Promise<string | null> {
  try {
    const res = await fetch(API.media.getFile(filename), {
      method: "GET",
      headers: {
        Authorization: `Bearer ${token}`,
      },
    })
    if (!res.ok) return null
    const blob = await res.blob()
    return URL.createObjectURL(blob)
  } catch {
    return null
  }
}