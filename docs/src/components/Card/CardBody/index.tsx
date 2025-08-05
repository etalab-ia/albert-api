import React, { CSSProperties, ReactNode } from 'react';
import clsx from 'clsx';

interface CardBodyProps {
  className?: string;
  style?: CSSProperties;
  children?: ReactNode;
  textAlign?: 'left' | 'center' | 'right' | 'justify';
  variant?: string;
  italic?: boolean;
  noDecoration?: boolean;
  transform?: 'uppercase' | 'lowercase' | 'capitalize';
  breakWord?: boolean;
  truncate?: boolean;
  weight?: 'light' | 'normal' | 'semibold' | 'bold';
}

const CardBody: React.FC<CardBodyProps> = ({
  className,
  style,
  children,
  textAlign,
  variant,
  italic = false,
  noDecoration = false,
  transform,
  breakWord = false,
  truncate = false,
  weight,
}) => {
  const classes = clsx(
    'card__body',
    className,
    textAlign && `text--${textAlign}`,
    variant && `text--${variant}`,
    italic && 'text--italic',
    noDecoration && 'text-no-decoration',
    transform && `text--${transform}`,
    breakWord && 'text--break',
    truncate && 'text--truncate',
    weight && `text--${weight}`
  );

  return (
    <div className={classes} style={style}>
      {children}
    </div>
  );
};

export default CardBody;
