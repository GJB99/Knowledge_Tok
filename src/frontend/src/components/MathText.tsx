import React, { useEffect, useRef } from 'react';
import katex from 'katex';

export const MathText: React.FC<{ text: string }> = ({ text }) => {
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!containerRef.current) return;

    // Split text into math and non-math parts
    const parts = text.split(/(\$[^\$]+\$|\\\([^\\\)]+\\\)|\\\[[^\\\]]+\\\])/g);
    
    // Clear previous content
    containerRef.current.innerHTML = '';
    
    // Process each part
    parts.forEach((part, i) => {
      const span = document.createElement('span');
      
      if (part.startsWith('$') && part.endsWith('$')) {
        // Render inline math
        katex.render(part.slice(1, -1), span, { displayMode: false });
      } else if ((part.startsWith('\\(') && part.endsWith('\\)')) || 
                 (part.startsWith('\\[') && part.endsWith('\\]'))) {
        // Render block math
        katex.render(part.slice(2, -2), span, { displayMode: true });
      } else {
        span.textContent = part;
      }
      
      containerRef.current?.appendChild(span);
    });
  }, [text]);

  return <div ref={containerRef} />;
}; 