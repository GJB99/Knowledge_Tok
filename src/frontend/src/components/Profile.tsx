import React, { useState, useEffect } from 'react';

interface SavedContent {
  id: number;
  title: string;
  abstract: string;
  source: string;
  url: string;
  interaction_type: string;
}

export const Profile: React.FC = () => {
  const [savedContent, setSavedContent] = useState<SavedContent[]>([]);
  const [activeTab, setActiveTab] = useState<'likes' | 'bookmarks'>('likes');

  useEffect(() => {
    fetchUserInteractions();
  }, [activeTab]);

  const fetchUserInteractions = async () => {
    try {
      const token = localStorage.getItem('token');
      if (!token) {
        window.location.href = '/login';
        return;
      }

      const response = await fetch(`/api/user/interactions?type=${activeTab}`, {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });

      if (!response.ok) {
        if (response.status === 401) {
          localStorage.removeItem('token');
          window.location.href = '/login';
          return;
        }
        throw new Error('Failed to fetch interactions');
      }

      const data = await response.json();
      setSavedContent(data);
    } catch (error) {
      console.error('Error fetching interactions:', error);
    }
  };

  return (
    <div className="profile-container">
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