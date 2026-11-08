import { ArrowRight, BookOpen, Check, Code2, ListChecks, Mic, NotebookPen, ShieldCheck, type LucideIcon } from "lucide-react";
import { Link } from "react-router-dom";

import type { BlockKind, PlanBlock } from "../../types/plan.types";

const ICONS: Record<BlockKind, LucideIcon> = {
  quiz: ListChecks,
  concept: BookOpen,
  coding: Code2,
  lab: ShieldCheck,
  mock: Mic,
  recap: NotebookPen,
};

/** Where a block's "Start" goes. The block id rides along so finishing ticks it off. */
export function blockLink(block: PlanBlock): string | null {
  const params = new URLSearchParams({ block: block.id });
  if (block.subtopic_id) params.set("subtopic", block.subtopic_id);
  switch (block.kind) {
    case "quiz":
      params.set("mode", "quiz");
      params.set("count", block.minutes <= 5 ? "5" : "8");
      return `/practice?${params}`;
    case "concept":
    case "coding":
    case "lab":
      params.set("mode", block.kind);
      return `/practice?${params}`;
    case "mock":
      params.set("kind", block.mock_kind ?? "mixed");
      params.set("count", block.minutes >= 20 ? "2" : "1");
      return `/mock-interview?${params}`;
    case "recap":
      return null;
  }
}

interface BlockCardProps {
  block: PlanBlock;
  index: number;
  isNext: boolean;
  onOpenRecap: () => void;
}

export function BlockCard({ block, index, isNext, onOpenRecap }: BlockCardProps) {
  const Icon = ICONS[block.kind];
  const link = blockLink(block);
  return (
    <li className={`plan-block${block.done ? " plan-block--done" : ""}${isNext ? " plan-block--next" : ""}`}>
      <span className="plan-block__marker" aria-hidden="true">
        {block.done ? <Check size={16} /> : index + 1}
      </span>
      <div className="plan-block__body">
        <div className="plan-block__head">
          <Icon size={16} aria-hidden="true" className="plan-block__icon" />
          <strong>{block.title}</strong>
          <span className="plan-block__minutes">{block.minutes} min</span>
          {block.is_review && <span className="review-pill">Review</span>}
        </div>
        {block.subtopic_name && (
          <span className="plan-block__subtopic">
            {block.topic_name} · {block.subtopic_name}
          </span>
        )}
        <span className="muted plan-block__reason">{block.reason}</span>
      </div>
      <div className="plan-block__action">
        {block.done ? (
          <span className="badge badge--good">Done</span>
        ) : link ? (
          <Link to={link} className={`button button--small ${isNext ? "button--primary" : "button--ghost"}`}>
            Start <ArrowRight size={14} />
          </Link>
        ) : (
          <button type="button" className={`button button--small ${isNext ? "button--primary" : "button--ghost"}`} onClick={onOpenRecap}>
            Open <ArrowRight size={14} />
          </button>
        )}
      </div>
    </li>
  );
}
