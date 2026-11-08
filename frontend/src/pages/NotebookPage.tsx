import { Download, FileText, MessagesSquare, NotebookPen, Search, Settings } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";

import { notebookApi } from "../api/studyApi";
import { trackApi } from "../api/trackApi";
import { EmptyState } from "../components/common/EmptyState";
import { ErrorAlert } from "../components/common/ErrorAlert";
import { renderInline } from "../components/common/Markdown";
import { SkeletonList, SkeletonResults } from "../components/common/Skeleton";
import { PageHeader } from "../components/layout/PageHeader";
import { NotebookDetail } from "../components/notebook/NotebookDetail";
import { KIND_LABELS, STATUS_LABELS } from "../components/notebook/notebookLabels";
import { useProfile } from "../context/ProfileContext";
import type { NotebookFilters, NotebookItemDetail, NotebookPage as NotebookPageData } from "../types/task.types";
import type { Track } from "../types/track.types";

const SEARCH_DELAY_MS = 300;

export function NotebookPage() {
  const { profile } = useProfile();
  const [searchParams, setSearchParams] = useSearchParams();
  const selectedId = Number(searchParams.get("item")) || null;

  const [filters, setFilters] = useState<NotebookFilters>({});
  const [query, setQuery] = useState("");
  const [page, setPage] = useState<NotebookPageData | null>(null);
  const [detail, setDetail] = useState<NotebookItemDetail | null>(null);
  const [track, setTrack] = useState<Track | null>(null);
  const [error, setError] = useState<string | null>(null);

  // Debounce typing in the search box.
  useEffect(() => {
    const timer = window.setTimeout(() => setFilters((f) => ({ ...f, q: query.trim() || undefined })), SEARCH_DELAY_MS);
    return () => window.clearTimeout(timer);
  }, [query]);

  useEffect(() => {
    if (!profile) return;
    trackApi.getTrack(profile.track_id).then(setTrack).catch(() => undefined);
  }, [profile]);

  useEffect(() => {
    if (!profile) return;
    notebookApi
      .list(filters)
      .then(setPage)
      .catch((err: unknown) => setError(err instanceof Error ? err.message : String(err)));
  }, [profile, filters]);

  useEffect(() => {
    if (!selectedId) {
      setDetail(null);
      return;
    }
    notebookApi
      .getItem(selectedId)
      .then(setDetail)
      .catch((err: unknown) => setError(err instanceof Error ? err.message : String(err)));
  }, [selectedId]);

  function select(itemId: number) {
    const params = new URLSearchParams(searchParams);
    params.set("item", String(itemId));
    setSearchParams(params, { replace: true });
  }

  const setFilter = (key: keyof NotebookFilters, value: string) =>
    setFilters((current) => ({ ...current, [key]: value || undefined }));

  const exportFilters = useMemo(
    () => ({ date_from: filters.date_from, date_to: filters.date_to, topic_id: filters.topic_id, kind: filters.kind }),
    [filters],
  );

  if (profile === undefined) {
    return (
      <div className="page">
        <PageHeader eyebrow="Review" title="Notebook" />
        <SkeletonResults label="Loading" />
      </div>
    );
  }
  if (profile === null) {
    return (
      <div className="page">
        <PageHeader eyebrow="Review" title="Notebook" />
        <div className="card">
          <EmptyState
            icon={Settings}
            title="Pick your career track first"
            description="Your notebook fills up as you practise."
            actions={
              <Link to="/settings" className="button button--primary">
                Set up my prep
              </Link>
            }
          />
        </div>
      </div>
    );
  }

  return (
    <div className="page">
      <PageHeader
        eyebrow={`Review · ${profile.track_name}`}
        title="Notebook"
        description="Everything you've learnt — lessons, quiz answers, code, labs, interviews and your questions to the teacher — kept for revision."
        actions={
          <div className="button-row">
            <a className="button button--ghost" href={notebookApi.exportUrl(exportFilters, "notes")} download>
              <FileText size={16} /> Revision notes (PDF)
            </a>
            <a className="button button--primary" href={notebookApi.exportUrl(exportFilters, "full")} download>
              <Download size={16} /> Full book (PDF)
            </a>
          </div>
        }
      />

      <section className="card notebook-filters" aria-label="Filters">
        <label className="field notebook-filters__search">
          <span className="field__label">Search</span>
          <span className="notebook-filters__search-box">
            <Search size={16} aria-hidden="true" />
            <input className="input" value={query} onChange={(e) => setQuery(e.target.value)} placeholder="e.g. hash map, XSS, Big-O" />
          </span>
        </label>
        <label className="field">
          <span className="field__label">Type</span>
          <select className="input" value={filters.kind ?? ""} onChange={(e) => setFilter("kind", e.target.value)}>
            <option value="">All</option>
            {Object.entries(KIND_LABELS).map(([value, label]) => (
              <option key={value} value={value}>
                {label}
              </option>
            ))}
          </select>
        </label>
        <label className="field">
          <span className="field__label">Status</span>
          <select className="input" value={filters.status ?? ""} onChange={(e) => setFilter("status", e.target.value)}>
            <option value="">All</option>
            {Object.entries(STATUS_LABELS).map(([value, label]) => (
              <option key={value} value={value}>
                {label}
              </option>
            ))}
          </select>
        </label>
        <label className="field">
          <span className="field__label">Topic</span>
          <select className="input" value={filters.topic_id ?? ""} onChange={(e) => setFilter("topic_id", e.target.value)}>
            <option value="">All topics</option>
            {track?.topics.map((t) => (
              <option key={t.id} value={t.id}>
                {t.name}
              </option>
            ))}
          </select>
        </label>
        <label className="field">
          <span className="field__label">From</span>
          <input type="date" className="input" value={filters.date_from ?? ""} onChange={(e) => setFilter("date_from", e.target.value)} />
        </label>
        <label className="field">
          <span className="field__label">To</span>
          <input type="date" className="input" value={filters.date_to ?? ""} onChange={(e) => setFilter("date_to", e.target.value)} />
        </label>
      </section>
      <p className="muted notebook-filters__hint">The PDF buttons export what these filters show (type, topic and dates).</p>

      {error && <ErrorAlert message={error} onDismiss={() => setError(null)} />}

      <div className="notebook">
        <section className="card notebook__list" aria-label="Notebook entries">
          {!page ? (
            <SkeletonList rows={6} label="Loading notebook" />
          ) : page.total === 0 ? (
            <EmptyState
              compact
              icon={NotebookPen}
              title={Object.values(filters).some(Boolean) ? "Nothing matches" : "Your notebook is empty"}
              description={
                Object.values(filters).some(Boolean)
                  ? "Try clearing a filter."
                  : "Everything you practise is saved here automatically."
              }
              actions={
                <Link to="/practice" className="button button--primary button--small">
                  Start practising
                </Link>
              }
            />
          ) : (
            <>
              <p className="muted notebook__count">
                {page.total} item{page.total > 1 ? "s" : ""}
              </p>
              <ul>
                {page.entries.map((entry) => (
                  <li key={entry.item_id}>
                    <button
                      type="button"
                      className={`notebook-entry${entry.item_id === selectedId ? " notebook-entry--active" : ""}`}
                      onClick={() => select(entry.item_id)}
                    >
                      <span className="notebook-entry__top">
                        <span className="pill">{KIND_LABELS[entry.kind] ?? entry.kind}</span>
                        {entry.status === "weak" && <span className="notebook-entry__weak">Needs review</span>}
                        {entry.has_chat && <MessagesSquare size={13} aria-label="Has teacher chat" />}
                        <span className="muted notebook-entry__date">{new Date(entry.created_at).toLocaleDateString()}</span>
                      </span>
                      <span className="notebook-entry__title">{renderInline(entry.title)}</span>
                      <span className="muted notebook-entry__subtopic">
                        {entry.subtopic_name}
                        {entry.last_score !== null && ` · ${Math.round(entry.last_score)}%`}
                      </span>
                    </button>
                  </li>
                ))}
              </ul>
            </>
          )}
        </section>

        <div className="notebook__detail">
          {detail ? (
            <NotebookDetail item={detail} />
          ) : (
            <div className="card">
              <EmptyState compact icon={NotebookPen} title="Pick an item" description="Its revision note, your answers and the model answer show here." />
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
