import React, { useState, useEffect } from 'react';
import { ContentCard } from './ContentCard';

interface SavedContent {
  interaction_id: number;
  interaction_type: string;
  content: {
    id: number;
    title: string;
    abstract: string;
    source: string;
    url: string;
    metadata: {
      categories: string[];
      published_date: string;
      authors: string[];
      paper_id: string;
    };
  };
}

interface ProfileProps {
  onHomeClick: () => void;
  onSearch: (query: string) => void;
  onLogout: () => void;
}

export const Profile: React.FC<ProfileProps> = ({ onHomeClick, onSearch, onLogout }) => {
  const [savedContent, setSavedContent] = useState<SavedContent[]>([]);
  const [activeTab, setActiveTab] = useState<'likes' | 'bookmarks' | 'not_interested'>('likes');
  const [searchQuery, setSearchQuery] = useState('');

  const fetchUserInteractions = async () => {
    try {
      const token = localStorage.getItem('token');
      if (!token) {
        window.location.href = '/login';
        return;
      }

      const response = await fetch(`http://localhost:8000/api/user/interactions?type=${
        activeTab === 'likes' ? 'like' : 
        activeTab === 'bookmarks' ? 'save' : 
        'not_interested'
      }`, {
        credentials: 'include',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Accept': 'application/json'
        }
      });

      if (!response.ok) {
        if (response.status === 401) {
          alert('Unauthorized. Please log in again to view your profile.');
          return;
        }
        throw new Error('Failed to fetch interactions');
      }

      const interactions = await response.json();
      
      // Directly use the interactions with embedded content
      const validInteractions = interactions.filter((i: any) => i.content);
      
      // Map to match SavedContent type
      const mappedContent = validInteractions.map((i: any) => ({
        interaction_id: i.interaction_id,
        interaction_type: i.interaction_type,
        content: {
          ...i.content,
          metadata: {
            ...i.content.metadata,
            published_date: i.content.metadata.published_date || i.content.published_date
          }
        }
      }));

      setSavedContent(mappedContent);
    } catch (error) {
      console.error('Error fetching interactions:', error);
      alert('An unexpected error occurred. Please try again.');
    }
  };

  useEffect(() => {
    fetchUserInteractions();
  }, [activeTab]);

  useEffect(() => {
    const handleInteractionChange = () => fetchUserInteractions();
    const handleInteractionRemove = (event: Event) => {
      if (event instanceof CustomEvent && event.detail && event.detail.contentId) {
        setSavedContent(prev => prev.filter(item => item.content.id !== event.detail.contentId));
      }
    };

    window.addEventListener('interaction-change', handleInteractionChange);
    window.addEventListener('interaction-remove', handleInteractionRemove);

    return () => {
      window.removeEventListener('interaction-change', handleInteractionChange);
      window.removeEventListener('interaction-remove', handleInteractionRemove);
    };
  }, []);

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
        <button 
          className={`tab ${activeTab === 'not_interested' ? 'active' : ''}`}
          onClick={() => setActiveTab('not_interested')}
        >
          Not Interested
        </button>
      </div>

      <div className="saved-content">
        {savedContent.length === 0 ? (
          <div className="no-content">
            No {activeTab.replace('_', ' ')} content yet
          </div>
        ) : (
          savedContent.map(interaction => (
            interaction.content && (
              <ContentCard
                key={interaction.interaction_id}
                content={interaction.content}
              />
            )
          ))
        )}
      </div>
    </div>
  );
}; 