declare module 'katex' {
  interface KatexOptions {
    displayMode?: boolean;
    throwOnError?: boolean;
    errorColor?: string;
    macros?: Record<string, string>;
    colorIsTextColor?: boolean;
    strict?: boolean | string | ((...args: any[]) => string);
    trust?: boolean | ((context: any) => boolean);
    output?: 'html' | 'mathml';
  }

  interface KatexStatic {
    render(
      math: string,
      element: HTMLElement,
      options?: KatexOptions
    ): void;
  }

  const katex: KatexStatic;
  export default katex;
} 