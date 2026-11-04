/** The APEX mark (icon only), drawn inline so it scales crisply at any size. */
const COLORS = {
  color: { outer: '#0B2545', inner: '#2B7BE4' },
  reversed: { outer: '#FFFFFF', inner: '#5FA2F5' },
  mono: { outer: 'currentColor', inner: 'currentColor' },
};

export const ApexMark = ({
  variant = 'color',
  size = 28,
  title = 'APEX Element Group',
  decorative = false,
  className = '',
}: {
  variant?: keyof typeof COLORS;
  /** Height in px; width follows the mark's 100:88 proportions. */
  size?: number;
  title?: string;
  decorative?: boolean;
  className?: string;
}) => {
  const c = COLORS[variant];
  return (
    <svg
      viewBox="0 0 100 88"
      height={size}
      width={(size * 100) / 88}
      className={className}
      {...(decorative ? { 'aria-hidden': true } : { role: 'img' })}
    >
      {!decorative && <title>{title}</title>}
      <path fillRule="evenodd" fill={c.outer} d="M0 88 L50 0 L100 88 Z M24 88 L50 42.24 L76 88 Z" />
      <path fill={c.inner} d="M32 88 L50 56.32 L68 88 Z" />
    </svg>
  );
};
