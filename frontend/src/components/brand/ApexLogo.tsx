import horizontal from '../../assets/brand/apex-logo-horizontal.svg';
import horizontalReversed from '../../assets/brand/apex-logo-horizontal-reversed.svg';
import stacked from '../../assets/brand/apex-logo-stacked.svg';

const SOURCES = {
  horizontal: { color: horizontal, reversed: horizontalReversed },
  stacked: { color: stacked, reversed: stacked },
};

/** Full APEX Element Group logo, used exactly as supplied in brand/. */
export const ApexLogo = ({
  layout = 'horizontal',
  variant = 'color',
  className = '',
}: {
  layout?: keyof typeof SOURCES;
  variant?: 'color' | 'reversed';
  className?: string;
}) => <img src={SOURCES[layout][variant]} alt="APEX Element Group" className={className} />;
