import { useCallback, useEffect, useState } from "react";
import api, { getErrorMessage } from "../services/api.js";

const PAGE_SIZE = 50;

export default function useResource(path, params = {}) {
  const [items, setItems] = useState([]);
  const [offset, setOffset] = useState(0);
  const [hasMore, setHasMore] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const reload = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const { data } = await api.get(path, { params: { ...params, limit: PAGE_SIZE, offset: 0 } });
      setItems(data);
      setOffset(data.length);
      setHasMore(data.length === PAGE_SIZE);
    } catch (requestError) {
      setError(getErrorMessage(requestError));
    } finally {
      setLoading(false);
    }
  }, [path, JSON.stringify(params)]);

  const loadMore = useCallback(async () => {
    if (loading || items.length < PAGE_SIZE) return;
    setLoading(true);
    setError("");
    try {
      const { data } = await api.get(path, { params: { ...params, limit: PAGE_SIZE, offset } });
      setItems((current) => [...current, ...data]);
      setOffset((current) => current + data.length);
      setHasMore(data.length === PAGE_SIZE);
    } catch (requestError) {
      setError(getErrorMessage(requestError));
    } finally {
      setLoading(false);
    }
  }, [items.length, loading, offset, path, JSON.stringify(params)]);

  useEffect(() => { reload(); }, [reload]);

  return { items, loading, error, reload, loadMore, hasMore };
}
