import React, { CSSProperties, ReactNode } from 'react';
import clsx from 'clsx';

interface CardProps {
  /** Additional class names for the card container */
  className?: string;
  /** Inline styles for the card container */
  style?: CSSProperties;
  /** Content to render within the card */
  children?: ReactNode;
  /** Shadow level under the card: low (lw), medium (md), or tall (tl) */
  shadow?: 'lw' | 'md' | 'tl';
}

const Card: React.FC<CardProps> = ({ className, style, children, shadow }) => {
  return (
    <div
      className={clsx('card', className, shadow && `item shadow--${shadow}`)}
      style={style}
    >
      {children}
    </div>
  );
};

export default Card;
