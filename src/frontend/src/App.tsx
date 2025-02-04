import React from 'react';
import { Routes, Route } from 'react-router-dom';
import { Feed } from './components/Feed';

function App() {
  return (
    <Routes>
      <Route path="*" element={<Feed />} />
    </Routes>
  );
}

export default App; 