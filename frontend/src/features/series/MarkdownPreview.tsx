import type { ReactNode } from "react";

type MarkdownPreviewProps = {
  markdown: string;
};

export function MarkdownPreview({ markdown }: MarkdownPreviewProps) {
  const lines = markdown.split("\n");
  const blocks: ReactNode[] = [];
  let listItems: string[] = [];

  function flushList(key: string) {
    if (!listItems.length) {
      return;
    }
    blocks.push(
      <ul className="my-4 space-y-2" key={key}>
        {listItems.map((item, index) => (
          <li className="flex gap-2 text-sm leading-6 text-streamly-purpleBlue" key={`${key}-${index}`}>
            <span className="mt-2 h-1.5 w-1.5 shrink-0 rounded-streamly-pill bg-streamly-electric" />
            <span>{renderInline(item)}</span>
          </li>
        ))}
      </ul>
    );
    listItems = [];
  }

  lines.forEach((line, index) => {
    const trimmed = line.trim();
    if (trimmed.startsWith("- ")) {
      listItems.push(trimmed.slice(2));
      return;
    }

    flushList(`list-${index}`);

    if (!trimmed) {
      blocks.push(<div className="h-3" key={`space-${index}`} />);
      return;
    }

    if (trimmed.startsWith("### ")) {
      blocks.push(
        <h4
          className="mt-5 font-streamly-platform text-sm font-extrabold uppercase text-streamly-violet"
          key={`h3-${index}`}
        >
          {renderInline(trimmed.slice(4))}
        </h4>
      );
      return;
    }

    if (trimmed.startsWith("## ")) {
      blocks.push(
        <h3
          className="mt-6 font-streamly-platform text-xl font-extrabold text-streamly-coal"
          key={`h2-${index}`}
        >
          {renderInline(trimmed.slice(3))}
        </h3>
      );
      return;
    }

    if (trimmed.startsWith("# ")) {
      blocks.push(
        <h2
          className="font-streamly-platform text-2xl font-extrabold text-streamly-coal"
          key={`h1-${index}`}
        >
          {renderInline(trimmed.slice(2))}
        </h2>
      );
      return;
    }

    blocks.push(
      <p className="text-sm font-semibold leading-7 text-[var(--streamly-text-muted)]" key={`p-${index}`}>
        {renderInline(trimmed)}
      </p>
    );
  });

  flushList("list-end");

  if (!markdown.trim()) {
    return (
      <div className="grid min-h-72 place-items-center rounded-streamly-xl border border-dashed border-streamly-lavenderStrong bg-streamly-wash/70 p-8 text-center">
        <p className="text-sm font-bold text-[var(--streamly-text-muted)]">
          Preview appears as the outline takes shape.
        </p>
      </div>
    );
  }

  return <div className="prose max-w-none">{blocks}</div>;
}

function renderInline(value: string) {
  const parts = value.split(/(\*\*[^*]+\*\*)/g);
  return parts.map((part, index) => {
    if (part.startsWith("**") && part.endsWith("**")) {
      return (
        <strong className="font-extrabold text-streamly-coal" key={`${part}-${index}`}>
          {part.slice(2, -2)}
        </strong>
      );
    }
    return <span key={`${part}-${index}`}>{part}</span>;
  });
}
