import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import ChatPage from '../pages/ChatPage';
import api from '../api/axios';

// Mock the API axios instance
vi.mock('../api/axios', () => ({
  default: {
    post: vi.fn(),
    get: vi.fn()
  }
}));

// Mock services/api
vi.mock('../services/api', () => ({
  getHealthRecords: vi.fn().mockResolvedValue([])
}));

describe('Clinical Interview Guided UI Workflow', () => {
  it('renders initial start screen inviting the user to describe symptoms', () => {
    render(<ChatPage language="English" setLanguage={vi.fn()} />);
    
    expect(screen.getByText('Begin Clinical Screening')).toBeInTheDocument();
    expect(screen.getByPlaceholderText('Describe your pregnancy symptoms to begin clinical assessment...')).toBeInTheDocument();
  });

  it('triggers the stateful clinical interview on symptom query submit', async () => {
    // Setup mock api response for starting interview
    api.post.mockResolvedValue({
      data: {
        status: 'success',
        data: {
          completed: false,
          response: 'To better understand your symptoms, could you please answer this follow-up question:\n\n💬 **How severe is your headache?**',
          step_number: 1,
          total_steps: 3,
          collected_symptoms: ['Headache'],
          answers: {},
          risk_level: 'Routine Medical Review 🟡'
        }
      }
    });

    render(<ChatPage language="English" setLanguage={vi.fn()} />);
    
    const textarea = screen.getByPlaceholderText('Describe your pregnancy symptoms to begin clinical assessment...');
    const submitBtn = screen.getByRole('button', { name: '➤' });

    fireEvent.change(textarea, { target: { value: 'I have a headache' } });
    fireEvent.click(submitBtn);

    await waitFor(() => {
      // Verify API was called with start query
      expect(api.post).toHaveBeenCalledWith('/ai/chat', {
        query: 'I have a headache',
        language: 'English',
        action: 'submit'
      });
    });

    // Check that UI transitioned to show step status and the active question
    await waitFor(() => {
      expect(screen.getByText(/Question 1 of 3/)).toBeInTheDocument();
      expect(screen.getByText(/Risk Progress:/)).toBeInTheDocument();
      expect(screen.getByText(/Routine Medical Review 🟡/)).toBeInTheDocument();
      expect(screen.getByText(/How severe is your headache/)).toBeInTheDocument();
    });
  });

  it('allows user to trigger reset to clear an active interview session', async () => {
    // Setup initial state as active interview
    api.post.mockResolvedValue({
      data: {
        status: 'success',
        data: {
          completed: false,
          response: 'To better understand your symptoms, could you please answer this follow-up question:\n\n💬 **How severe is your headache?**',
          step_number: 1,
          total_steps: 3,
          collected_symptoms: ['Headache'],
          answers: {},
          risk_level: 'Routine Medical Review 🟡'
        }
      }
    });

    render(<ChatPage language="English" setLanguage={vi.fn()} />);
    
    const textarea = screen.getByPlaceholderText('Describe your pregnancy symptoms to begin clinical assessment...');
    const submitBtn = screen.getByRole('button', { name: '➤' });
    fireEvent.change(textarea, { target: { value: 'I have a headache' } });
    fireEvent.click(submitBtn);

    await waitFor(() => {
      expect(screen.getByText('Reset')).toBeInTheDocument();
    });

    // Setup reset mock response
    api.post.mockResolvedValue({
      data: {
        status: 'success',
        data: {
          completed: true,
          response: 'Clinical interview session reset. How can I help you today?',
          step_number: 0,
          total_steps: 0,
          collected_symptoms: [],
          answers: {},
          risk_level: 'Home Care 🟢'
        }
      }
    });

    const resetBtn = screen.getByText('Reset');
    fireEvent.click(resetBtn);

    await waitFor(() => {
      expect(api.post).toHaveBeenCalledWith('/ai/chat', {
        query: 'reset',
        language: 'English',
        action: 'reset'
      });
    });
  });
});
