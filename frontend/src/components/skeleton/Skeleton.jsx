import './Skeleton.css'

function classNames(...values) {
  return values.filter(Boolean).join(' ')
}

function skeletonStyle({ height, style, width }) {
  return {
    ...(width ? { '--skeleton-width': width } : {}),
    ...(height ? { '--skeleton-height': height } : {}),
    ...style,
  }
}

export function SkeletonBlock({
  as: Component = 'span',
  className = '',
  height,
  rounded = false,
  style,
  width,
  ...props
}) {
  return (
    <Component
      aria-hidden="true"
      className={classNames('skeleton-block', rounded && 'skeleton-block--rounded', className)}
      style={skeletonStyle({ height, style, width })}
      {...props}
    />
  )
}

export function SkeletonCard({ as: Component = 'section', className = '', children, ...props }) {
  return (
    <Component className={classNames('skeleton-card', className)} {...props}>
      {children}
    </Component>
  )
}

export function SkeletonCircle({ className = '', size, style, ...props }) {
  return (
    <SkeletonBlock
      className={classNames('skeleton-circle', className)}
      height={size || undefined}
      rounded
      style={style}
      width={size || undefined}
      {...props}
    />
  )
}

export function SkeletonText({ className = '', lines = 1, widths = [] }) {
  return (
    <span className={classNames('skeleton-text', className)} aria-hidden="true">
      {Array.from({ length: lines }).map((_, index) => (
        <SkeletonBlock
          className="skeleton-text__line"
          height="0.75rem"
          key={index}
          rounded
          width={widths[index] || (index === lines - 1 ? '68%' : '100%')}
        />
      ))}
    </span>
  )
}
