import React, { useState, useEffect } from 'react';

interface SavedContent {
  id: number;
  title: string;
  abstract: string;
  source: string;
  url: string;
  interaction_type: string;
}

interface ProfileProps {
  onHomeClick: () => void;
  onSearch: (query: string) => void;
  onLogout: () => void;
}

export const Profile: React.FC<ProfileProps> = ({ onHomeClick, onSearch, onLogout }) => {
  const [savedContent, setSavedContent] = useState<SavedContent[]>([]);
  const [activeTab, setActiveTab] = useState<'likes' | 'bookmarks'>('likes');
  const [searchQuery, setSearchQuery] = useState('');

  const fetchUserInteractions = async () => {
    try {
      const token = localStorage.getItem('token');
      if (!token) {
        window.location.href = '/login';
        return;
      }

      console.log('Token:', token);

      const response = await fetch(`http://localhost:8000/api/user/interactions?type=${activeTab}`, {
        credentials: 'include',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Accept': 'application/json'
        }
      });

      const data = await response.json();
      
      if (!response.ok) {
        if (response.status === 401) {
          alert('Unauthorized. Please log in again to view your profile.');
          return;
        }
        console.error('Failed to fetch interactions:', data);
        alert('Failed to load content. Please try logging in again.');
        return;
      }

      setSavedContent(data);
    } catch (error) {
      console.error('Error fetching interactions:', error);
      alert('An unexpected error occurred. Please try again.');
    }
  };

  useEffect(() => {
    fetchUserInteractions();
  }, [activeTab]);

  return (
    <div className="profile-container">
      <header className="app-header">
        <div className="left-buttons">
          <button 
            className="home-button"
            onClick={onHomeClick}
            aria-label="Go to home feed"
            title="Go to home feed"
          >
            <i className="fas fa-home" aria-hidden="true"></i>
          </button>
        </div>

        <div className="search-container">
          <input 
            type="text" 
            placeholder="Search academic papers..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            onKeyPress={(e) => e.key === 'Enter' && onSearch(searchQuery)}
          />
          <button 
            className="search-button"
            onClick={() => onSearch(searchQuery)}
          >
            Search
          </button>
        </div>

        <button 
          className="logout-button"
          onClick={onLogout}
          aria-label="Logout"
          title="Logout"
        >
          <i className="fas fa-sign-out-alt" aria-hidden="true"></i>
          <span></span>
        </button>
      </header>
      <div className="profile-tabs">
        <button 
          className={`tab ${activeTab === 'likes' ? 'active' : ''}`}
          onClick={() => setActiveTab('likes')}
        >
          Likes
        </button>
        <button 
          className={`tab ${activeTab === 'bookmarks' ? 'active' : ''}`}
          onClick={() => setActiveTab('bookmarks')}
        >
          Bookmarks
        </button>
      </div>
      <div className="saved-content">
        {savedContent.map(content => (
          <div key={content.id} className="saved-item">
            <h3>{content.title}</h3>
            <p>{content.abstract}</p>
            <a href={content.url} target="_blank" rel="noopener noreferrer">
              Read More
            </a>
          </div>
        ))}
      </div>
    </div>
  );
}; 