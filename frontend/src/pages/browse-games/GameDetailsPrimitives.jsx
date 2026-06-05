export function Fact({ icon, label }) {
  return (
    <div className="details-fact">
      {icon}
      <span>{label}</span>
    </div>
  )
}

export function InfoCard({
  badge = '',
  className = '',
  ctaDisabled = false,
  icon,
  title,
  eyebrow,
  cta,
  ctaIcon,
  onCtaClick,
  rightArrow,
  children,
}) {
  return (
    <section className={`details-card details-info-card ${className}`.trim()}>
      <div className="details-info-card__icon">{icon}</div>

      <div className="details-info-card__body">
        <div className="details-info-card__title">
          <h2>{title}</h2>
          {badge && <span>{badge}</span>}
        </div>
        {eyebrow && <p className="details-eyebrow">{eyebrow}</p>}
        {children}
        {cta && (
          <button
            className="details-secondary-action details-text-button"
            type="button"
            disabled={ctaDisabled}
            onClick={onCtaClick}
          >
            {ctaIcon && <span className="details-action-icon">{ctaIcon}</span>}
            <span>{cta}</span>
          </button>
        )}
      </div>

      {rightArrow && onCtaClick && (
        <button
          className="details-card-arrow"
          type="button"
          aria-label={cta || title}
          onClick={onCtaClick}
        >
          ›
        </button>
      )}

      {rightArrow && !onCtaClick && <span className="details-card-arrow">›</span>}
    </section>
  )
}
