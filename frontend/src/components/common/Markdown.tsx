import { Fragment, type ReactNode } from "react";

/**
 * The small slice of Markdown the agents write: paragraphs, "#" headings, "-"/"1." lists,
 * ``` code blocks, **bold**, *italic* and `code`. Renders React elements (never raw HTML),
 * so model output can't inject markup.
 */
export function Markdown({ text, className }: { text: string; className?: string }) {
  return <div className={`markdown${className ? ` ${className}` : ""}`}>{renderBlocks(text)}</div>;
}

type Block =
  | { kind: "paragraph"; lines: string[] }
  | { kind: "heading"; text: string }
  | { kind: "list"; ordered: boolean; items: string[] }
  | { kind: "code"; language: string; lines: string[] };

const BULLET = /^\s*[-*•]\s+(.*)$/;
const NUMBERED = /^\s*\d+[.)]\s+(.*)$/;
const HEADING = /^\s*#{1,6}\s+(.*)$/;
const FENCE = /^\s*```\s*([\w+-]*)\s*$/;

function parseBlocks(text: string): Block[] {
  const blocks: Block[] = [];
  let openCode: Extract<Block, { kind: "code" }> | null = null;

  for (const line of text.replace(/\r\n/g, "\n").split("\n")) {
    const fence = FENCE.exec(line);
    if (openCode) {
      if (fence) openCode = null;
      else openCode.lines.push(line);
      continue;
    }
    if (fence) {
      openCode = { kind: "code", language: fence[1], lines: [] };
      blocks.push(openCode);
      continue;
    }

    const last = blocks[blocks.length - 1];
    const bullet = BULLET.exec(line);
    const numbered = bullet ? null : NUMBERED.exec(line);
    const heading = HEADING.exec(line);
    if (!line.trim()) {
      blocks.push({ kind: "paragraph", lines: [] });
    } else if (heading) {
      blocks.push({ kind: "heading", text: heading[1] });
    } else if (bullet || numbered) {
      const ordered = Boolean(numbered);
      const item = (bullet ?? numbered)![1];
      if (last?.kind === "list" && last.ordered === ordered) last.items.push(item);
      else blocks.push({ kind: "list", ordered, items: [item] });
    } else if (last?.kind === "paragraph") {
      last.lines.push(line.trim());
    } else if (last?.kind === "list" && /^\s{2,}/.test(line)) {
      last.items[last.items.length - 1] += " " + line.trim(); // wrapped list item
    } else {
      blocks.push({ kind: "paragraph", lines: [line.trim()] });
    }
  }
  return blocks;
}

function renderBlocks(text: string): ReactNode[] {
  return parseBlocks(text)
    .filter((b) => (b.kind === "paragraph" ? b.lines.length > 0 : true))
    .map((block, i) => {
      if (block.kind === "code")
        return (
          <pre key={i} className="markdown__code" data-language={block.language || undefined}>
            <code>{block.lines.join("\n")}</code>
          </pre>
        );
      if (block.kind === "heading")
        return (
          <p key={i} className="markdown__heading">
            {renderInline(block.text)}
          </p>
        );
      if (block.kind === "list") {
        const List = block.ordered ? "ol" : "ul";
        return (
          <List key={i}>
            {block.items.map((item, j) => (
              <li key={j}>{renderInline(item)}</li>
            ))}
          </List>
        );
      }
      return (
        <p key={i}>
          {block.lines.map((line, j) => (
            <Fragment key={j}>
              {j > 0 && <br />}
              {renderInline(line)}
            </Fragment>
          ))}
        </p>
      );
    });
}

const INLINE = /(\*\*[^*]+\*\*|__[^_]+__|`[^`]+`|\*[^*\s][^*]*\*)/g;

export function renderInline(text: string): ReactNode[] {
  return text.split(INLINE).map((part, i) => {
    if (/^(\*\*|__).+\1$/.test(part)) return <strong key={i}>{part.slice(2, -2)}</strong>;
    if (/^`.+`$/.test(part)) return <code key={i}>{part.slice(1, -1)}</code>;
    if (/^\*.+\*$/.test(part)) return <em key={i}>{part.slice(1, -1)}</em>;
    return <Fragment key={i}>{part}</Fragment>;
  });
}
