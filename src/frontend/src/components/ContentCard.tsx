import React, { useState, useEffect } from 'react';
import { motion, HTMLMotionProps } from 'framer-motion';
import { MathText } from './MathText';

interface ContentCardProps {
  content: {
    id: number;
    title: string;
    abstract: string;
    source: string;
    url: string;
    metadata?: {
      categories?: string[];
      published_date?: string;
    };
  };
}

type MotionDivProps = HTMLMotionProps<"div"> & { className?: string };

export const ContentCard: React.FC<ContentCardProps> = ({ content }) => {
  console.log("ContentCard received content:", content);
  const [isLiked, setIsLiked] = useState(false);
  const [isSaved, setIsSaved] = useState(false);
  const [isNotInterested, setIsNotInterested] = useState(false);

  const checkInteractionStatus = async () => {
    try {
      const token = localStorage.getItem('token');
      if (!token) return;

      const response = await fetch(`http://localhost:8000/api/content/${content.id}/interaction-status`, {
        headers: {
          'Authorization': `Bearer ${token}`,
          'Accept': 'application/json'
        }
      });

      if (!response.ok) {
        if (response.status === 401) {
          localStorage.removeItem('token');
          return;
        }
        throw new Error('Failed to fetch interaction status');
      }

      const data = await response.json();
      setIsLiked(data.isLiked);
      setIsSaved(data.isSaved);
      setIsNotInterested(data.isNotInterested);
    } catch (error) {
      console.error('Error checking interaction status:', error);
    }
  };

  useEffect(() => {
    checkInteractionStatus();
  }, [content.id]);

  const handleInteraction = async (type: 'like' | 'save' | 'share' | 'not_interested' | 'read_more') => {
    try {
      if (type === 'share') {
        if (navigator.share) {
          await navigator.share({
            title: content.title,
            text: content.abstract,
            url: content.url,
          });
        } else {
          await navigator.clipboard.writeText(content.url);
          alert('Link copied to clipboard!');
        }
      }

      const token = localStorage.getItem('token');
      if (!token) {
        alert('Please login to interact with this content.');
        window.location.href = '/login';
        return;
      }

      // Always record the interaction in the database
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
          alert('Unauthorized action. Please try logging in again.');
          return;
        }
        throw new Error(`Failed to ${type} the content.`);
      }

      const data = await response.json();
      if (type === 'like') setIsLiked(data.action === 'added');
      if (type === 'save') setIsSaved(data.action === 'added');
      if (type === 'not_interested') setIsNotInterested(true);

      // If this is a read_more interaction, open the URL after recording
      if (type === 'read_more') {
        window.open(content.url, '_blank');
      }
    } catch (error) {
      console.error('Error in handleInteraction:', error);
      alert('An unexpected error occurred. Please try again.');
    }
  };

  const motionProps: MotionDivProps = {
    className: "content-card",
    initial: { opacity: 0, y: 20 },
    animate: { opacity: 1, y: 0 },
    exit: { opacity: 0, y: -20 }
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'long',
      day: 'numeric'
    });
  };

  return (
    <motion.div {...motionProps}>
      <h2><MathText text={content.title} /></h2>
      {content.metadata?.categories && (
        <div className="categories">
          {content.metadata.categories.map((category, index) => (
            <span key={index} className="category-tag">
              {category}
            </span>
          ))}
        </div>
      )}
      <p className="abstract"><MathText text={content.abstract} /></p>
      <div className="source-info">
        <div className="source-date">
          <span>arXiv,</span>
          {content.metadata?.published_date && (
            <span className="date">{formatDate(content.metadata.published_date)}</span>
          )}
        </div>
        <a 
          href="#"
          onClick={(e) => {
            e.preventDefault();
            handleInteraction('read_more');
          }}
          rel="noopener noreferrer"
        >
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
          <i className="fas fa-heart" aria-hidden="true"></i>
        </button>
        <button
          className={`interaction-button ${isSaved ? 'active' : ''}`}
          onClick={() => handleInteraction('save')}
          aria-label={`${isSaved ? 'Remove from' : 'Save to'} bookmarks`}
          title={`${isSaved ? 'Remove from' : 'Save to'} bookmarks`}
        >
          <i className="fas fa-bookmark" aria-hidden="true"></i>
        </button>
        <button
          className="interaction-button"
          onClick={() => handleInteraction('share')}
          aria-label="Share this paper"
          title="Share this paper"
        >
          <i className="fas fa-share" aria-hidden="true"></i>
        </button>
        <button
          className={`interaction-button ${isNotInterested ? 'active' : ''}`}
          onClick={() => handleInteraction('not_interested')}
          aria-label="Not interested in this paper"
          title="Not interested in this paper"
        >
          <i className="fas fa-ban" aria-hidden="true"></i>
        </button>
      </div>
    </motion.div>
  );
}; 