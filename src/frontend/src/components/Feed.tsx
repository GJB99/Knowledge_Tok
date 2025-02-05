import React, { useState, useEffect, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { ContentCard } from '../components/ContentCard';
import { useSwipeable } from 'react-swipeable';
import { Profile } from '../components/Profile';
import { useNavigate } from 'react-router-dom';
import { LoginModal } from '../components/LoginModal';
import { CategoriesDropdown } from './CategoriesDropdown';


interface Content {
  id: number;
  title: string;
  abstract: string;
  source: string;
  url: string;
  metadata?: {
    authors: string[];
    categories: string[];
    paper_id: string;
    published_date: string;
  };
}

interface SearchItem {
  id: number;
  title: string;
  abstract: string;
  source: string;
  url: string;
  categories?: string[];
  published_date?: string;
  metadata?: {
    authors: string[];
    categories: string[];
    paper_id: string;
    published_date: string;
  };
}

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

export const Feed: React.FC = () => {
  const [contents, setContents] = useState<Content[]>([]);
  const [currentPage, setCurrentPage] = useState(1);
  const [loading, setLoading] = useState(false);
  const [hasMore, setHasMore] = useState(true);
  const [showProfile, setShowProfile] = useState(false);
  const [showLoginModal, setShowLoginModal] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [isAuthenticated, setIsAuthenticated] = useState(!!localStorage.getItem('token'));
  const navigate = useNavigate();
  const [showCategories, setShowCategories] = useState(false);

  const fetchContent = async (page: number) => {
    if (loading || !hasMore) return;
    
    try {
      setLoading(true);
      const token = localStorage.getItem('token');
      
      const response = await fetch(`${API_BASE_URL}/api/content?page=${page}&limit=10`, {
        headers: {
          'Accept': 'application/json',
          'Content-Type': 'application/json',
          ...(token && { 'Authorization': `Bearer ${token}` })
        }
      });
      
      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || `HTTP error! status: ${response.status}`);
      }
      
      const data = await response.json();
      
      if (data.items && Array.isArray(data.items)) {
        if (page === 1) {
          setContents(data.items);
        } else {
          setContents(prev => [...prev, ...data.items]);
        }
        setCurrentPage(page);
        setHasMore(data.has_more);
      } else {
        console.error('Invalid data format:', data);
        if (page === 1) {
          setContents([]);
          setHasMore(false);
        }
      }
    } catch (error) {
      console.error('Error fetching content:', error);
      if (page === 1) {
        setContents([]);
        setHasMore(false);
      }
    } finally {
      setLoading(false);
    }
  };

  const handleSearch = async () => {
    if (!searchQuery.trim()) {
      fetchContent(1);
      return;
    }
    
    try {
      setLoading(true);
      const token = localStorage.getItem('token');
      
      const response = await fetch(`${API_BASE_URL}/search/arxiv?query=${encodeURIComponent(searchQuery)}`, {
        headers: {
          'Accept': 'application/json',
          'Content-Type': 'application/json',
          ...(token && { 'Authorization': `Bearer ${token}` })
        }
      });
      
      const data = await response.json();
      
      if (!response.ok) {
        console.error('Search error:', data);
        throw new Error(data.detail || 'Search failed');
      }
      
      if (data.items && Array.isArray(data.items)) {
        // Transform the data to include metadata in the correct format
        const transformedItems = data.items.map((item: SearchItem) => ({
          ...item,
          metadata: {
            ...item.metadata,
            categories: item.categories || item.metadata?.categories || [],
            published_date: item.published_date || item.metadata?.published_date
          }
        }));
        setContents(transformedItems);
        setCurrentPage(1);
        setHasMore(data.has_more || false);
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

  const handleProfileClick = () => {
    if (!isAuthenticated) {
      setShowLoginModal(true);
    } else {
      setShowProfile(!showProfile);
    }
  };

  const handleLogout = () => {
    localStorage.removeItem('token');
    setIsAuthenticated(false);
    setShowProfile(false);
    window.location.href = '/login';
  };

  return (
    <div className="app-container">
      <header className="app-header">
        <button 
          className="home-button"
          onClick={() => {
            setSearchQuery('');
            setCurrentPage(1);
            setHasMore(true);
            fetchContent(1).then(() => {
              setContents(prev => prev.filter(content => content !== null));
            });
          }}
          aria-label="Go to home feed"
          title="Go to home feed"
        >
          <i className="fas fa-home" aria-hidden="true"></i>
        </button>
        <button
          className="categories-button"
          onClick={() => setShowCategories(true)}
          aria-label="Show categories"
          title="Show categories"
        >
          <i className="fas fa-tags" aria-hidden="true"></i>
          <span></span>
        </button>
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
            onClick={handleProfileClick}
            aria-label="View profile"
            title="View profile"
          >
            <i className="fas fa-user" aria-hidden="true"></i>
          </button>
          <div className="right-buttons">
            {isAuthenticated && (
              <button 
                className="logout-button"
                onClick={handleLogout}
                aria-label="Logout"
                title="Logout"
              >
                <i className="fas fa-sign-out-alt" aria-hidden="true"></i>
                <span></span>
              </button>
            )}
          </div>
        </div>
      </header>

      <CategoriesDropdown 
        isOpen={showCategories} 
        onClose={() => setShowCategories(false)} 
      />

      {showProfile ? (
        <Profile 
          onHomeClick={() => {
            setShowProfile(false);
            setSearchQuery('');
            setCurrentPage(1);
            setHasMore(true);
            fetchContent(1);
          }}
          onSearch={(query: string) => {
            setShowProfile(false);
            setSearchQuery(query);
            handleSearch();
          }}
          onLogout={handleLogout}
        />
      ) : (
        <div 
          className="feed-container" 
          ref={containerRef}
        >
          {contents.length === 0 && !loading && (
            <div className="no-content">
              No papers found. Try searching for something!
            </div>
          )}
          
          {contents.map((content, index) => (
            <ContentCard key={`${content.id}-${index}`} content={content} />
          ))}
          
          {loading && (
            <div className="loading">
              Loading more papers...
            </div>
          )}
        </div>
      )}

      <LoginModal 
        isOpen={showLoginModal} 
        onClose={() => {
          setShowLoginModal(false);
          if (localStorage.getItem('token')) {
            setIsAuthenticated(true);
            fetchContent(1);
          }
        }} 
      />
    </div>
  );
}; 