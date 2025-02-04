import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import './LoginModal.css';

interface LoginModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export const LoginModal: React.FC<LoginModalProps> = ({ isOpen, onClose }) => {
  const navigate = useNavigate();
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [email, setEmail] = useState('');
  const [isResetMode, setIsResetMode] = useState(false);
  const [resetMessage, setResetMessage] = useState('');

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      const response = await fetch('http://localhost:8000/auth/login', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ username, password }),
      });

      if (response.ok) {
        const data = await response.json();
        localStorage.setItem('token', data.token);
        onClose();
        navigate('/');
      } else {
        alert('Login failed');
      }
    } catch (error) {
      console.error('Login error:', error);
      alert('Login failed');
    }
  };

  const handlePasswordReset = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      const response = await fetch('http://localhost:8000/auth/reset-password-request', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ email }),
      });

      const data = await response.json();

      if (response.ok) {
        setResetMessage('If an account exists with this email, you will receive password reset instructions.');
        setTimeout(() => {
          setIsResetMode(false);
          setResetMessage('');
        }, 5000);
      } else {
        throw new Error(data.detail || 'Password reset request failed');
      }
    } catch (error) {
      console.error('Password reset error:', error);
      setResetMessage('Failed to send reset email. Please try again.');
    }
  };

  const renderLoginForm = () => (
    <form onSubmit={handleSubmit} className="login-form">
      <h2>Login</h2>
      <div className="form-group">
        <input
          type="text"
          placeholder="Username"
          value={username}
          onChange={(e) => setUsername(e.target.value)}
        />
      </div>
      <div className="form-group">
        <input
          type="password"
          placeholder="Password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
        />
      </div>
      <button type="submit" className="login-button">Login</button>
      <div className="auth-links">
        <a href="#" onClick={(e) => {
          e.preventDefault();
          setIsResetMode(true);
        }}>
          Forgot Password?
        </a>
      </div>
    </form>
  );

  const renderResetForm = () => (
    <form onSubmit={handlePasswordReset} className="login-form">
      <h2>Reset Password</h2>
      <div className="form-group">
        <input
          type="email"
          placeholder="Enter your email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
        />
      </div>
      <button type="submit" className="login-button">Send Reset Link</button>
      {resetMessage && <div className="reset-message">{resetMessage}</div>}
      <div className="auth-links">
        <a href="#" onClick={(e) => {
          e.preventDefault();
          setIsResetMode(false);
        }}>
          Back to Login
        </a>
      </div>
    </form>
  );

  if (!isOpen) return null;

  return (
    <div className="modal-overlay" onClick={(e) => {
      if (e.target === e.currentTarget) onClose();
    }}>
      <div className="modal-content">
        <button className="modal-close" onClick={onClose} aria-label="Close login modal">
          <i className="fas fa-times" aria-hidden="true"></i>
        </button>
        {isResetMode ? renderResetForm() : renderLoginForm()}
      </div>
    </div>
  );
}; 