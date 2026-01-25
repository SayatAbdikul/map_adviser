import React, { useState } from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import { AlertCircle, CheckCircle, Lock, Mail, User } from 'lucide-react';
import { useAuthStore } from '@/store/useAuthStore';
import { Button } from '@/components/common/Button';
import { Card } from '@/components/common/Card';
import { Input } from '@/components/common/Input';

export const RegisterPage: React.FC = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const { register, isLoading, error, setError } = useAuthStore();

  const [formData, setFormData] = useState({
    name: '',
    email: '',
    password: '',
    confirmPassword: '',
  });

  const [validations, setValidations] = useState({
    passwordLength: false,
    passwordMatch: false,
    emailFormat: false,
  });

  const from = (location.state as { from?: string } | null)?.from || '/map';

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value } = e.target;
    setFormData((prev) => ({
      ...prev,
      [name]: value,
    }));
    if (error) setError(null);

    if (name === 'password') {
      setValidations((prev) => ({
        ...prev,
        passwordLength: value.length >= 8,
        passwordMatch: value === formData.confirmPassword,
      }));
    } else if (name === 'confirmPassword') {
      setValidations((prev) => ({
        ...prev,
        passwordMatch: value === formData.password,
      }));
    } else if (name === 'email') {
      setValidations((prev) => ({
        ...prev,
        emailFormat: /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value),
      }));
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!formData.name || !formData.email || !formData.password || !formData.confirmPassword) {
      setError('Please fill in all fields');
      return;
    }

    if (!validations.passwordLength) {
      setError('Password must be at least 8 characters long');
      return;
    }

    if (!validations.passwordMatch) {
      setError('Passwords do not match');
      return;
    }

    if (!validations.emailFormat) {
      setError('Please enter a valid email address');
      return;
    }

    try {
      await register(formData.email, formData.password, formData.name);
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
          <div className="text-xs uppercase tracking-[0.4em] app-muted">Create your account</div>
          <h1 className="font-display text-3xl app-text sm:text-4xl">Start building routes that move together.</h1>
          <p className="text-sm app-muted sm:text-base">
            Unlock the live map, room sharing, and assistant insights in one workspace.
          </p>
          <div className="flex items-center gap-3 text-sm">
            <Link to="/" className="app-muted hover:text-[color:var(--app-text)] transition-colors">
              Back to landing
            </Link>
          </div>
        </div>

        <Card className="relative w-full max-w-md justify-self-center p-6 sm:p-8">
          <div className="space-y-2 text-center">
            <div className="text-xs uppercase tracking-[0.3em] app-muted">Map Adviser</div>
            <h2 className="font-display text-2xl app-text">Join the journey</h2>
            <p className="text-sm app-muted">Create an account to start planning.</p>
          </div>

          {error && (
            <div className="mt-6 flex items-center gap-2 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
              <AlertCircle size={18} />
              {error}
            </div>
          )}

          <form onSubmit={handleSubmit} className="mt-6 space-y-4">
            <Input
              label="Full name"
              name="name"
              type="text"
              value={formData.name}
              onChange={handleChange}
              placeholder="Enter your name"
              leftIcon={<User size={18} />}
              disabled={isLoading}
            />
            <div className="space-y-2">
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
              {formData.email && (
                <div
                  className={`flex items-center gap-2 text-xs ${
                    validations.emailFormat ? 'text-emerald-600' : 'text-red-600'
                  }`}
                >
                  {validations.emailFormat ? <CheckCircle size={14} /> : <AlertCircle size={14} />}
                  {validations.emailFormat ? 'Valid email' : 'Invalid email format'}
                </div>
              )}
            </div>
            <div className="space-y-2">
              <Input
                label="Password"
                name="password"
                type="password"
                value={formData.password}
                onChange={handleChange}
                placeholder="Minimum 8 characters"
                leftIcon={<Lock size={18} />}
                disabled={isLoading}
              />
              {formData.password && (
                <div
                  className={`flex items-center gap-2 text-xs ${
                    validations.passwordLength ? 'text-emerald-600' : 'text-red-600'
                  }`}
                >
                  {validations.passwordLength ? <CheckCircle size={14} /> : <AlertCircle size={14} />}
                  {validations.passwordLength ? 'Password strong' : 'At least 8 characters'}
                </div>
              )}
            </div>
            <div className="space-y-2">
              <Input
                label="Confirm password"
                name="confirmPassword"
                type="password"
                value={formData.confirmPassword}
                onChange={handleChange}
                placeholder="Re-enter your password"
                leftIcon={<Lock size={18} />}
                disabled={isLoading}
              />
              {formData.confirmPassword && (
                <div
                  className={`flex items-center gap-2 text-xs ${
                    validations.passwordMatch ? 'text-emerald-600' : 'text-red-600'
                  }`}
                >
                  {validations.passwordMatch ? <CheckCircle size={14} /> : <AlertCircle size={14} />}
                  {validations.passwordMatch ? 'Passwords match' : 'Passwords do not match'}
                </div>
              )}
            </div>

            <Button
              type="submit"
              variant="primary"
              className="w-full"
              isLoading={isLoading}
              disabled={!validations.emailFormat || !validations.passwordLength || !validations.passwordMatch}
            >
              {isLoading ? 'Creating account...' : 'Create account'}
            </Button>
          </form>

          <div className="mt-6 text-center text-sm app-muted">
            Already have an account?{' '}
            <Link to="/login" className="font-semibold text-[color:var(--app-accent-strong)] hover:underline">
              Sign in
            </Link>
          </div>
        </Card>
      </div>
    </div>
  );
};
