import React, { useEffect, useRef } from 'react';
import katex from 'katex';

export const MathText: React.FC<{ text: string }> = ({ text }) => {
  const containerRef = useRef<HTMLSpanElement>(null);

  useEffect(() => {
    if (!containerRef.current) return;

    // Clear previous content
    containerRef.current.innerHTML = '';

    // More robust splitting, handles $, \( \), \[ \] and escapes
    const parts = text.split(/(\$[^\$]+\$|\\\([^\)]+\\\)|\\\[[^\]]+?\\\]|\\.)/g);

    parts.forEach((part) => {
      if (!part) return; // Skip empty parts

      const span = document.createElement('span');

      try {
        if (part.startsWith('$') && part.endsWith('$')) {
          katex.render(part.slice(1, -1), span, { displayMode: false, throwOnError: false });
        } else if (part.startsWith('\\(') && part.endsWith('\\)')) {
          katex.render(part.slice(2, -2), span, { displayMode: false, throwOnError: false });
        } else if (part.startsWith('\\[') && part.endsWith('\\]')) {
          katex.render(part.slice(2, -2), span, { displayMode: true, throwOnError: false });
        } else if (part.startsWith('\\')) {
            // Handle escaped characters (like \$)
            span.textContent = part.slice(1);
        }
        
        else {
          span.textContent = part;
        }
      } catch (error) {
        console.error('KaTeX render error:', error);
        span.textContent = part; // Display the raw text as fallback
        span.style.color = 'red'; // Optionally style the error text
      }

      containerRef.current?.appendChild(span);
    });
  }, [text]);

  return <span ref={containerRef} />;
}; 