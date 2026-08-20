import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import DisclaimerBox from '../components/DisclaimerBox';
import Header from '../components/Header';
import LoginPage from '../pages/LoginPage';

// Mock components that utilize APIs or WebSockets
vi.mock('../components/NotificationBell', () => ({
  default: () => <div data-testid="notification-bell">Mocked Notification Bell</div>,
}));

vi.mock('../services/api', () => ({
  loginUser: vi.fn().mockResolvedValue({
    access_token: 'mock-token-abc',
    user: { role: 'patient' },
  }),
  registerUser: vi.fn().mockResolvedValue({
    status: 'success',
  }),
  getToken: vi.fn(),
  setToken: vi.fn(),
  removeToken: vi.fn(),
}));

describe('DisclaimerBox Component', () => {
  it('renders the medical disclaimer warning message text', () => {
    const text = 'Testing disclaimer message content';
    render(<DisclaimerBox text={text} />);
    expect(screen.getByText(/Important Disclaimer:/)).toBeInTheDocument();
    expect(screen.getByText(new RegExp(text))).toBeInTheDocument();
  });
});

describe('Header Component', () => {
  it('displays the app title "MotherCare AI"', () => {
    render(<Header />);
    expect(screen.getByText('MotherCare AI')).toBeInTheDocument();
  });

  it('renders the username and Sign Out button when authenticated', () => {
    const mockLogout = vi.fn();
    render(<Header username="Alice" onLogout={mockLogout} />);

    expect(screen.getByText(/Alice/)).toBeInTheDocument();
    expect(screen.getByTestId('notification-bell')).toBeInTheDocument();

    const signOutBtn = screen.getByText('Sign Out');
    expect(signOutBtn).toBeInTheDocument();

    fireEvent.click(signOutBtn);
    expect(mockLogout).toHaveBeenCalledTimes(1);
  });
});

describe('LoginPage Component', () => {
  it('renders input elements for username and password', () => {
    render(<LoginPage onLoginSuccess={vi.fn()} />);

    expect(screen.getByPlaceholderText('Enter your username')).toBeInTheDocument();
    expect(screen.getByPlaceholderText('Enter your password')).toBeInTheDocument();

    const buttons = screen.getAllByRole('button', { name: 'Sign In' });
    expect(buttons.length).toBe(2);
  });

  it('validates user input and exposes an accessible error banner', () => {
    const { container } = render(<LoginPage onLoginSuccess={vi.fn()} />);

    const formEl = container.querySelector('form');
    fireEvent.submit(formEl);

    expect(screen.getByRole('alert')).toHaveTextContent(/validation errors/i);
    expect(screen.getByRole('alert')).toHaveTextContent(/username is required/i);
    expect(screen.getByRole('alert')).toHaveTextContent(/password is required/i);
  });

  it('makes public registration patient-only', () => {
    render(<LoginPage onLoginSuccess={vi.fn()} />);

    fireEvent.click(screen.getByRole('button', { name: 'Register' }));

    expect(screen.getByText(/Public signup creates a/i)).toHaveTextContent('patient account');
    expect(screen.queryByLabelText('Doctor')).not.toBeInTheDocument();
    expect(screen.queryByLabelText('Admin')).not.toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Create Patient Account' })).toBeInTheDocument();
  });
});
