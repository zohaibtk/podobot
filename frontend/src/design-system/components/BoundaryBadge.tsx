type BoundaryBadgeProps = {
  label: string;
};

export function BoundaryBadge({ label }: BoundaryBadgeProps) {
  return (
    <span className="inline-flex rounded-streamly-pill bg-streamly-lavender px-3 py-1 text-xs font-extrabold uppercase text-streamly-violet">
      {label}
    </span>
  );
}
