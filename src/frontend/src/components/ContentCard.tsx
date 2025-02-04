import React, { useState } from 'react';
import { motion, HTMLMotionProps } from 'framer-motion';

interface ContentCardProps {
  content: {
    id: number;
    title: string;
    abstract: string;
    source: string;
    url: string;
  };
}

type MotionDivProps = HTMLMotionProps<"div"> & { className?: string };

export const ContentCard: React.FC<ContentCardProps> = ({ content }) => {
  const [isLiked, setIsLiked] = useState(false);
  const [isSaved, setIsSaved] = useState(false);

  const handleInteraction = async (type: 'like' | 'save' | 'share') => {
    try {
      if (type === 'share') {
        if (navigator.share) {
          await navigator.share({
            title: content.title,
            text: content.abstract,
            url: content.url,
          });
          return;
        }
        await navigator.clipboard.writeText(content.url);
        alert('Link copied to clipboard!');
        return;
      }

      const token = localStorage.getItem('token');
      if (!token) {
        alert('Please login to interact with this content.');
        window.location.href = '/login';
        return;
      }

      const response = await fetch('http://localhost:8000/api/interactions', {
        method: 'POST',
        credentials: 'include',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`,
          'Accept': 'application/json',
        },
        body: JSON.stringify({
          content_id: content.id,
          interaction_type: type,
        }),
      });

      if (!response.ok) {
        if (response.status === 401) {
          localStorage.removeItem('token');
          window.location.href = '/login';
          return;
        }
        throw new Error(`Failed to ${type} the content.`);
      }

      const data = await response.json();
      if (type === 'like') setIsLiked(data.action === 'added');
      if (type === 'save') setIsSaved(data.action === 'added');
    } catch (error) {
      console.error('Error in handleInteraction:', error);
    }
  };

  const motionProps: MotionDivProps = {
    className: "content-card",
    initial: { opacity: 0, y: 20 },
    animate: { opacity: 1, y: 0 },
    exit: { opacity: 0, y: -20 }
  };

  return (
    <motion.div {...motionProps}>
      <h2>{content.title}</h2>
      <p className="abstract">{content.abstract}</p>
      <div className="source-info">
        <span>{content.source}</span>
        <a href={content.url} target="_blank" rel="noopener noreferrer">
          Read More
        </a>
      </div>
      <div className="interaction-buttons" role="group" aria-label="Content interactions">
        <button
          className={`interaction-button ${isLiked ? 'active' : ''}`}
          onClick={() => handleInteraction('like')}
          aria-label={`${isLiked ? 'Unlike' : 'Like'} this paper`}
          title={`${isLiked ? 'Unlike' : 'Like'} this paper`}
        >
          <span className="button-label">
            {isLiked ? 'Unlike' : 'Like'} this paper
          </span>
          <i className="fas fa-heart" aria-hidden="true"></i>
        </button>
        <button
          className={`interaction-button ${isSaved ? 'active' : ''}`}
          onClick={() => handleInteraction('save')}
          aria-label={`${isSaved ? 'Remove from' : 'Save to'} bookmarks`}
          title={`${isSaved ? 'Remove from' : 'Save to'} bookmarks`}
        >
          <span className="button-label">
            {isSaved ? 'Remove from' : 'Save to'} bookmarks
          </span>
          <i className="fas fa-bookmark" aria-hidden="true"></i>
        </button>
        <button
          className="interaction-button"
          onClick={() => handleInteraction('share')}
          aria-label="Share this paper"
          title="Share this paper"
        >
          <span className="button-label">Share this paper</span>
          <i className="fas fa-share" aria-hidden="true"></i>
        </button>
      </div>
    </motion.div>
  );
}; 