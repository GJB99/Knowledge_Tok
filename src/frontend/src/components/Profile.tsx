import React, { useState, useEffect } from 'react';
import { ContentCard } from './ContentCard';

interface SavedContent {
  interaction_id: number;
  content_id: number;
  interaction_type: string;
  content?: {
    id: number;
    title: string;
    abstract: string;
    source: string;
    url: string;
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

      const response = await fetch(`http://localhost:8000/api/user/interactions?type=${activeTab}`, {
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
      
      // Fetch content details for each interaction
      const contentDetails = await Promise.all(
        interactions.map(async (interaction: SavedContent) => {
          const contentResponse = await fetch(`http://localhost:8000/api/content/${interaction.content_id}`, {
            headers: {
              'Authorization': `Bearer ${token}`,
              'Accept': 'application/json'
            }
          });
          
          if (!contentResponse.ok) {
            console.error(`Failed to fetch content for ID ${interaction.content_id}`);
            return interaction;
          }
          
          const content = await contentResponse.json();
          return {
            ...interaction,
            content
          };
        })
      );

      // Filter content based on active tab
      const filteredContent = contentDetails.filter(
        item => item.interaction_type === (activeTab === 'likes' ? 'like' : activeTab === 'bookmarks' ? 'save' : 'not_interested')
      );

      setSavedContent(filteredContent);
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