interface BadgeProps {
  tone: 'benign' | 'critical' | 'warning' | 'neutral'
  children: React.ReactNode
  size?: 'sm' | 'lg'
}

const TONE_CLASSES: Record<BadgeProps['tone'], string> = {
  benign: 'bg-benign/15 text-benign border-benign/40',
  critical: 'bg-critical-bg text-critical border-critical/40',
  warning: 'bg-warning/15 text-warning border-warning/40',
  neutral: 'bg-panel-raised text-secondary border-hairline',
}

/** BENIGN/ATTACK/status pill. Sentence case, not all-caps — see §7.3/§7.5 tone. */
export function Badge({ tone, children, size = 'sm' }: BadgeProps) {
  const sizeClasses = size === 'lg' ? 'px-3 py-1.5 text-sm' : 'px-2 py-0.5 text-xs'
  return (
    <span
      className={`inline-flex items-center rounded-pill border font-medium ${TONE_CLASSES[tone]} ${sizeClasses}`}
    >
      {children}
    </span>
  )
}
