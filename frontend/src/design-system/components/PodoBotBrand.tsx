import podobotBrandUrl from "@/assets/podobot-brand.svg";
import podobotMarkUrl from "@/assets/podobot-mark.svg";

type PodoBotBrandProps = {
  className?: string;
  hideTextClassName?: string;
  markClassName?: string;
  tone?: "light" | "purple";
};

export function PodoBotBrand({
  className = "w-52",
  hideTextClassName = "",
  markClassName = "h-11 w-11",
  tone = "purple"
}: PodoBotBrandProps) {
  const hasCompactMark = hideTextClassName.length > 0;
  const compactMarkClassName = hideTextClassName.includes("lg:")
    ? "hidden lg:block"
    : hasCompactMark
      ? "block"
      : "hidden";

  return (
    <div
      aria-label="PodoBot premium podcast operations"
      className={["flex items-center leading-none", className].filter(Boolean).join(" ")}
      role="img"
    >
      <img
        alt=""
        aria-hidden
        className={[
          "block h-auto w-full max-w-full select-none object-contain",
          tone === "light" ? "drop-shadow-[0_18px_42px_rgba(0,0,0,0.34)]" : "",
          hideTextClassName
        ]
          .filter(Boolean)
          .join(" ")}
        decoding="async"
        draggable={false}
        src={podobotBrandUrl}
      />
      {hasCompactMark ? (
        <img
          alt=""
          aria-hidden
          className={[
            markClassName,
            compactMarkClassName,
            "max-w-full select-none object-contain"
          ]
            .filter(Boolean)
            .join(" ")}
          decoding="async"
          draggable={false}
          src={podobotMarkUrl}
        />
      ) : null}
    </div>
  );
}
