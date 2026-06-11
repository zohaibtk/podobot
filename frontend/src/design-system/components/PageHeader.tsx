import type { ReactNode } from "react";

type PageHeaderProps = {
  actions?: ReactNode;
  aside?: ReactNode;
  children?: ReactNode;
  description: ReactNode;
  kicker: string;
  title: ReactNode;
};

export function PageHeader({
  actions,
  aside,
  children,
  description,
  kicker,
  title
}: PageHeaderProps) {
  return (
    <section className="streamly-page-hero streamly-page-header">
      <div className={aside ? "streamly-page-header-grid" : "streamly-page-header-row"}>
        <div className="streamly-page-header-copy">
          <p className="streamly-kicker">{kicker}</p>
          <h1 className="streamly-page-heading">{title}</h1>
          <p className="streamly-page-description">{description}</p>
        </div>
        {aside ? <div className="streamly-page-header-aside">{aside}</div> : actions}
      </div>
      {children ? <div className="streamly-page-header-body">{children}</div> : null}
    </section>
  );
}
