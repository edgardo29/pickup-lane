export function NeedASubDetailSectionHeading({ eyebrow, icon = null }) {
  return (
    <header className="need-sub-detail-section-heading need-sub-detail-section-heading--solo">
      {icon && (
        <span className="need-sub-detail-section-heading__icon" aria-hidden="true">
          {icon}
        </span>
      )}
      <h2>{eyebrow}</h2>
    </header>
  )
}
