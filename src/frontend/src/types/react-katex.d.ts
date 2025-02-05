declare module 'react-katex' {
  import { FC } from 'react';

  interface MathProps {
    math: string;
    block?: boolean;
    errorColor?: string;
    renderError?: (error: Error) => JSX.Element;
    settings?: any;
  }

  export const InlineMath: FC<MathProps>;
  export const BlockMath: FC<MathProps>;
} 