import React, { useState, useEffect, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { ContentCard } from './ContentCard';
import { useSwipeable } from 'react-swipeable';
import { Profile } from './Profile';

interface Content {
  id: number;
  title: string;
  abstract: string;
  source: string;
  url: string;
}

export const Feed: React.FC = () => {
  const [contents, setContents] = useState<Content[]>([]);
  const [currentPage, setCurrentPage] = useState(1);
  const [loading, setLoading] = useState(false);
  const [hasMore, setHasMore] = useState(true);
  const [showProfile, setShowProfile] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);
  const [searchQuery, setSearchQuery] = useState('');

  const fetchContent = async (page: number) => {
    if (loading || !hasMore) return;
    
    try {
      setLoading(true);
      console.log('Fetching content for page:', page);
      const response = await fetch(`http://localhost:8000/api/content?page=${page}&limit=10`, {
        credentials: 'include',
        headers: {
          'Accept': 'application/json',
          'Content-Type': 'application/json'
        }
      });
      
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      
      const data = await response.json();
      console.log('Raw response:', data);
      
      if (!data.items || !Array.isArray(data.items)) {
        console.error('Invalid data format:', data);
        return;
      }
      
      if (data.items.length === 0) {
        setHasMore(false);
      } else {
        setContents(prev => [...prev, ...data.items]);
        setCurrentPage(page);
        setHasMore(data.has_more);
      }
    } catch (error) {
      console.error('Error fetching content:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleSearch = async () => {
    if (!searchQuery.trim()) return;
    
    try {
      setLoading(true);
      const response = await fetch(`http://localhost:8000/search/arxiv?query=${encodeURIComponent(searchQuery)}`, {
        credentials: 'include',
        headers: {
          'Accept': 'application/json',
          'Content-Type': 'application/json'
        }
      });
      
      if (!response.ok) {
        throw new Error('Search failed');
      }
      
      const data = await response.json();
      
      if (data.items && Array.isArray(data.items)) {
        setContents(data.items);
        setCurrentPage(1);
        setHasMore(data.has_more);
      } else {
        setContents([]);
        setHasMore(false);
      }
    } catch (error) {
      console.error('Error searching content:', error);
      setContents([]);
      setHasMore(false);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchContent(1);
  }, []);

  const handleScroll = () => {
    if (containerRef.current) {
      const { scrollTop, scrollHeight, clientHeight } = containerRef.current;
      if (scrollHeight - scrollTop <= clientHeight * 1.5) {
        fetchContent(currentPage + 1);
      }
    }
  };

  return (
    <div className="app-container">
      <header className="app-header">
        <div className="search-container">
          <input 
            type="text" 
            placeholder="Search academic papers..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            onKeyPress={(e) => e.key === 'Enter' && handleSearch()}
          />
          <button 
            className="search-button"
            onClick={handleSearch}
          >
            Search
          </button>
        </div>
        <div className="header-buttons">
          <button 
            className="profile-button"
            onClick={() => setShowProfile(!showProfile)}
          >
            <i className="fas fa-user"></i>
          </button>
          <button 
            className="logout-button"
            onClick={() => {
              localStorage.removeItem('token');
              window.location.href = '/login';
            }}
          >
            <i className="fas fa-sign-out-alt"></i>
          </button>
        </div>
      </header>

      {showProfile ? (
        <Profile />
      ) : (
        <div 
          className="feed-container" 
          ref={containerRef}
          onScroll={handleScroll}
        >
          {contents.length === 0 && !loading && (
            <div className="no-content">
              No papers found. Try searching for something!
            </div>
          )}
          
          {contents.map((content) => (
            <ContentCard key={content.id} content={content} />
          ))}
          
          {loading && (
            <div className="loading">
              Loading more papers...
            </div>
          )}
        </div>
      )}
    </div>
  );
}; 