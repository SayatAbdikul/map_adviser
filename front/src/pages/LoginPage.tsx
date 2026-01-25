import React, { useState } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { AlertCircle, Lock, Mail } from 'lucide-react';
import { useAuthStore } from '@/store/useAuthStore';
import { Button } from '@/components/common/Button';
import { Card } from '@/components/common/Card';
import { Input } from '@/components/common/Input';

export const LoginPage: React.FC = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const { login, isLoading, error, setError } = useAuthStore();

  const [formData, setFormData] = useState({
    email: '',
    password: '',
  });

  const from = (location.state as { from?: string } | null)?.from || '/map';

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value } = e.target;
    setFormData((prev) => ({
      ...prev,
      [name]: value,
    }));
    if (error) setError(null);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!formData.email || !formData.password) {
      setError('Please fill in all fields');
      return;
    }

    try {
      await login(formData.email, formData.password);
      navigate(from, { replace: true });
    } catch {
      // Error is already set by the store
    }
  };

  return (
    <div className="relative flex min-h-screen items-center justify-center px-6 py-12">
      <div className="absolute inset-0 bg-[radial-gradient(circle_at_top,_var(--app-accent-soft),_transparent_65%)] opacity-60" />
      <div className="relative grid w-full max-w-5xl gap-10 lg:grid-cols-[1fr_0.9fr] lg:items-center">
        <div className="space-y-5">
          <div className="text-xs uppercase tracking-[0.4em] app-muted">Welcome back</div>
          <h1 className="font-display text-3xl app-text sm:text-4xl">Sign in to your route console.</h1>
          <p className="text-sm app-muted sm:text-base">
            Access saved routes, collaborative rooms, and live map intelligence.
          </p>
          <div className="flex flex-wrap items-center gap-3">
            <Button type="button" variant="secondary" size="sm" onClick={() => navigate('/')}>
              Back to landing
            </Button>
            <Button type="button" variant="ghost" size="sm" onClick={() => navigate('/register')}>
              Create account
            </Button>
          </div>
        </div>

        <Card className="relative w-full max-w-md justify-self-center p-6 sm:p-8">
          <div className="space-y-2 text-center">
            <div className="text-xs uppercase tracking-[0.3em] app-muted">Map Adviser</div>
            <h2 className="font-display text-2xl app-text">Welcome back</h2>
            <p className="text-sm app-muted">Enter your credentials to continue.</p>
          </div>

          {error && (
            <div className="mt-6 flex items-center gap-2 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
              <AlertCircle size={18} />
              {error}
            </div>
          )}

          <form onSubmit={handleSubmit} className="mt-6 space-y-4">
            <Input
              label="Email address"
              name="email"
              type="email"
              value={formData.email}
              onChange={handleChange}
              placeholder="you@example.com"
              leftIcon={<Mail size={18} />}
              disabled={isLoading}
            />
            <Input
              label="Password"
              name="password"
              type="password"
              value={formData.password}
              onChange={handleChange}
              placeholder="Enter your password"
              leftIcon={<Lock size={18} />}
              disabled={isLoading}
            />
            <Button
              type="submit"
              variant="primary"
              className="w-full"
              isLoading={isLoading}
            >
              {isLoading ? 'Signing in...' : 'Sign in'}
            </Button>
          </form>

          <div className="mt-6 flex flex-col gap-3 text-center">
            <div className="text-sm app-muted">New here?</div>
            <Button type="button" variant="secondary" className="w-full" onClick={() => navigate('/register')}>
              Create an account
            </Button>
          </div>
        </Card>
      </div>
    </div>
  );
};
