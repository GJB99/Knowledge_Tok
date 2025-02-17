import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import './LoginModal.css';

interface LoginModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export const LoginModal: React.FC<LoginModalProps> = ({ isOpen, onClose }) => {
  const navigate = useNavigate();
  const [isSignUp, setIsSignUp] = useState(false);
  const [isResetMode, setIsResetMode] = useState(false);
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [email, setEmail] = useState('');
  const [error, setError] = useState('');
  const [resetMessage, setResetMessage] = useState('');

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      let response;
      if (isSignUp) {
        response = await fetch('http://localhost:8000/auth/register', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({ email, username, password }),
        });

        const data = await response.json();
        if (response.ok) {
          if (data.token === "pending_verification") {
            setError(data.message || "Please check your email to verify your account.");
            return;
          }
          localStorage.setItem('token', data.token);
          onClose();
        } else {
          setError(data.detail || 'Registration failed');
        }
      } else {
        response = await fetch('http://localhost:8000/token', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/x-www-form-urlencoded',
          },
          body: new URLSearchParams({
            username: username || email,
            password: password,
          }),
        });

        if (response.ok) {
          const data = await response.json();
          localStorage.setItem('token', data.access_token);
          onClose();
        } else {
          const errorData = await response.json();
          setError(errorData.detail || 'Authentication failed');
        }
      }
    } catch (error) {
      console.error('Login error:', error);
      setError('An error occurred. Please try again.');
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
    <form className="login-form" onSubmit={handleSubmit}>
      <h2>{isSignUp ? 'Sign Up' : 'Login'}</h2>
      
      {isSignUp ? (
        <>
          <div className="form-group">
            <input
              type="email"
              placeholder="Email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
            />
          </div>
          <div className="form-group">
            <input
              type="text"
              placeholder="Username"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              required
            />
          </div>
        </>
      ) : (
        <div className="form-group">
          <input
            type="text"
            placeholder="Username or Email"
            value={username || email}
            onChange={(e) => {
              if (e.target.value.includes('@')) {
                setEmail(e.target.value);
                setUsername('');
              } else {
                setUsername(e.target.value);
                setEmail('');
              }
            }}
            required
          />
        </div>
      )}
      
      <div className="form-group">
        <input
          type="password"
          placeholder="Password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          required
        />
      </div>

      {error && <div className="error-message">{error}</div>}
      
      <button type="submit" className="login-button">
        {isSignUp ? 'Sign Up' : 'Login'}
      </button>

      <div className="auth-links">
        <button 
          type="button" 
          className="switch-mode" 
          onClick={() => setIsSignUp(!isSignUp)}
        >
          {isSignUp ? 'Already have an account? Login' : "Don't have an account? Sign Up"}
        </button>
        {!isSignUp && (
          <button 
            type="button"
            className="forgot-password"
            onClick={() => setIsResetMode(true)}
          >
            Forgot Password?
          </button>
        )}
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
        <button 
          type="button"
          className="switch-mode"
          onClick={() => setIsResetMode(false)}
        >
          Back to Login
        </button>
      </div>
    </form>
  );

  if (!isOpen) return null;

  return (
    <div className="modal-overlay">
      <div className="modal-content">
        <button className="modal-close" onClick={onClose}>&times;</button>
        {isResetMode ? renderResetForm() : renderLoginForm()}
      </div>
    </div>
  );
}; 