# Academic Feed App

A modern academic content discovery platform that aggregates research papers and academic content into a TikTok-like scrolling experience. Currently integrated with arXiv, with plans to expand to other academic sources.

## Features

### Currently Implemented
- **Smart Search System:**
  - Hybrid search combining keyword matching and semantic similarity
  - Real-time content updates from arXiv
  - Content caching for improved performance

- **Interactive Feed:**
  - Infinite scroll implementation
  - Like and bookmark functionality
  - Share papers with colleagues
  - Dynamic content loading

- **User System:**
  - JWT-based authentication
  - Personal reading lists
  - Interaction history (likes and bookmarks)

## Tech Stack

- **Backend:** 
  - FastAPI and Uvicorn
  - SQLAlchemy for async database operations
  - XML/JSON parsing for API integrations

- **Frontend:**
  - React with TypeScript
  - Responsive design
  - FontAwesome icons
  - Modern UI components

- **Database:**
  - SQLite (development)
  - PostgreSQL (planned for production)

## Getting Started

### Prerequisites
- Python 3.7+
- Node.js 14+
- npm or yarn

### Backend Setup

1. Create and activate a virtual environment:
python -m venv venv
source venv/bin/activate # On Unix/macOS
venv\Scripts\activate # On Windows

2. Install dependencies:
pip install -r requirements.txt

3. Create a `.env` file based on `.env.example`

4. Start the backend server:
uvicorn src.backend.main:app --reload

### Frontend Setup

1. Install dependencies:
cd src/frontend
npm install

2. Start the development server:
npm start


## Planned Integrations

### Academic Sources
- CORE API
- Semantic Scholar
- PubMed Central
- Google Scholar
- IEEE Xplore
- JSTOR
- ScienceDirect
- Web of Science
- SpringerLink
- ACM Digital Library

### Features in Development
- Advanced recommendation system
- Citation network visualization
- Research field clustering
- Collaborative reading lists
- Paper annotations
- Hybrid RAG chatbot
- Expert user verification
- Research impact metrics
- Mobile app version

## API Endpoints

- **Root:** `http://localhost:8000/`
  - Returns welcome page
- **Search:** `http://localhost:8000/search/arxiv?query=your+search+terms`
  - Searches academic papers
- **User Interactions:** `http://localhost:8000/api/interactions`
  - Handles likes and bookmarks
- **Profile:** `http://localhost:8000/api/user/interactions`
  - Returns user's interaction history

## Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.
