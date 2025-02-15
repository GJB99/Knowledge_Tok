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
  const [isLoadingBackground, setIsLoadingBackground] = useState(false);
  const [hasMore, setHasMore] = useState(true);
  const [showProfile, setShowProfile] = useState(false);
  const [showLoginModal, setShowLoginModal] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [isAuthenticated, setIsAuthenticated] = useState(!!localStorage.getItem('token'));
  const [shownContentIds, setShownContentIds] = useState<Set<number>>(new Set());
  const [nextPageContent, setNextPageContent] = useState<Content[]>([]);
  const containerRef = useRef<HTMLDivElement>(null);
  const navigate = useNavigate();
  const [showCategories, setShowCategories] = useState(false);
  const [currentView, setCurrentView] = useState<'feed' | 'search' | 'profile'>('feed');
  const [lastFeedContents, setLastFeedContents] = useState<Content[]>([]);
  const [lastSearchContents, setLastSearchContents] = useState<Content[]>([]);

  useEffect(() => {
    const token = localStorage.getItem('token');
    if (token) {
      setIsAuthenticated(true);
      fetchContent(1);
    }
  }, []);

  const loadMore = () => {
    if (hasMore && !loading && nextPageContent.length > 0) {
      setContents(prev => [...prev, ...nextPageContent]);
      setNextPageContent([]);
      fetchContent(currentPage + 1, true);
    }
  };

  useEffect(() => {
    const handleScroll = () => {
      if (containerRef.current) {
        const { scrollTop, scrollHeight, clientHeight } = containerRef.current;
        if (scrollHeight - scrollTop <= clientHeight * 1.5) {
          loadMore();
        }
      }
    };

    containerRef.current?.addEventListener('scroll', handleScroll);
    return () => containerRef.current?.removeEventListener('scroll', handleScroll);
  }, [hasMore, loading, nextPageContent]);

  const handleProfileClick = () => {
    if (!isAuthenticated) {
      setShowLoginModal(true);
    } else {
      setCurrentView('profile');
      setShowProfile(true);
    }
  };

  const handleLogout = () => {
    localStorage.removeItem('token');
    setIsAuthenticated(false);
    setShowProfile(false);
    window.location.href = '/login';
  };

  const handleSearch = async (newPage: number = 1) => {
    if (!searchQuery.trim()) {
      setCurrentView('feed');
      setContents(lastFeedContents);
      return;
    }
    
    setCurrentView('search');
    try {
      setLoading(true);
      const token = localStorage.getItem('token');
      
      const response = await fetch(
        `${API_BASE_URL}/search/arxiv?query=${encodeURIComponent(searchQuery)}&page=${newPage}&page_size=10`,
        {
          headers: {
            'Accept': 'application/json',
            'Content-Type': 'application/json',
            ...(token && { 'Authorization': `Bearer ${token}` })
          }
        }
      );

      if (!response.ok) throw new Error('Search failed');
      
      const data = await response.json();
      const newContents = newPage === 1 ? data.items : [...contents, ...data.items];
      setContents(newContents);
      setLastSearchContents(newContents);
      setCurrentPage(newPage);
      setHasMore(data.has_more);
      
    } catch (error) {
      console.error('Search error:', error);
      setContents([]);
      setHasMore(false);
    } finally {
      setLoading(false);
    }
  };

  const fetchContent = async (page: number, isBackground: boolean = false) => {
    if (!isBackground && loading || isBackground && isLoadingBackground || !hasMore) return;
    
    let abortController = new AbortController();
    
    try {
      if (isBackground) {
        setIsLoadingBackground(true);
      } else {
        setLoading(true);
      }
      
      const token = localStorage.getItem('token');
      const excludeIds = Array.from(shownContentIds).join(',');
      const response = await fetch(
        `${API_BASE_URL}/api/recommendations?page=${page}&page_size=10&exclude=${excludeIds}`, 
        {
          signal: abortController.signal,
          headers: {
            'Accept': 'application/json',
            'Content-Type': 'application/json',
            ...(token && { 'Authorization': `Bearer ${token}` })
          }
        }
      );
      
      if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
      
      const data = await response.json();
      
      if (data.items && Array.isArray(data.items)) {
        const newIds = data.items.map((item: Content) => item.id);
        setShownContentIds(prev => {
          const updatedSet = new Set(Array.from(prev));
          newIds.forEach((id: number) => updatedSet.add(id));
          return updatedSet;
        });

        if (isBackground) {
          setNextPageContent(data.items);
        } else {
          const newContents = page === 1 ? data.items : [...contents, ...data.items];
          setContents(newContents);
          setLastFeedContents(newContents);
          if (data.has_more) {
            fetchContent(page + 1, true);
          }
        }
        setCurrentPage(page);
        setHasMore(data.has_more);
      }
    } catch (error: unknown) {
      if (error instanceof Error) {
        if (error.name === 'AbortError') {
          console.log('Fetch aborted');
          return;
        }
        console.error('Error fetching content:', error.message);
      } else {
        console.error('Unknown error fetching content');
      }
    } finally {
      if (isBackground) {
        setIsLoadingBackground(false);
      } else {
        setLoading(false);
      }
    }
    
    return () => {
      abortController.abort();
    };
  };

  const handleHomeClick = () => {
    setShowProfile(false);
    setSearchQuery('');
    setCurrentView('feed');
    setContents(lastFeedContents);
    if (lastFeedContents.length === 0) {
      fetchContent(1);
    }
  };

  return (
    <div className="app-container">
      <header className="app-header">
        <button 
          className="home-button"
          onClick={handleHomeClick}
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
            onClick={() => handleSearch()}
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
          onHomeClick={handleHomeClick}
          onSearch={(query: string) => {
            setShowProfile(false);
            setSearchQuery(query);
            handleSearch(1);
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
          
          {(loading || isLoadingBackground) && (
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