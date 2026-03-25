import { useState, useEffect } from "react";
import { useAuthContext } from "../context/AuthContext";
import { getMediaList } from "../services/media/mediaService";

export function useMedia() {
  const { accessToken } = useAuthContext();

  const [filenames, setFilenames] = useState<string[]>([]);
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchPage(page);
  }, [page]);

  const fetchPage = async (pageNum: number) => {
    setLoading(true);
    setError(null);

    const { data, ok, error } = await getMediaList(pageNum, accessToken ?? "");

    if (ok && data) {
      setFilenames(data.files);
      setTotalPages(data.total_pages);
    } else {
      setError(error);
    }

    setLoading(false);
  };

  const nextPage = () => {
    if (page < totalPages) setPage((p) => p + 1);
  };
  const prevPage = () => {
    if (page > 1) setPage((p) => p - 1);
  };

  return { filenames, page, totalPages, loading, error, nextPage, prevPage };
}
