import React, { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { useAuthStore } from '@/store/useAuthStore';
import { Button } from '@/components/common/Button';
import { Mail, Lock, AlertCircle } from 'lucide-react';

export const LoginPage: React.FC = () => {
    const navigate = useNavigate();
    const { login, isLoading, error, setError } = useAuthStore();

    const [formData, setFormData] = useState({
        email: '',
        password: '',
    });

    const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        const { name, value } = e.target;
        setFormData(prev => ({
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
            navigate('/');
        } catch {
            // Error is already set by the store
        }
    };

    return (
        <div className= "min-h-screen bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center px-4" >
        <div className="bg-white rounded-lg shadow-2xl p-8 w-full max-w-md" >
            <div className="text-center mb-8" >
                <h1 className="text-3xl font-bold text-gray-800" > Map Adviser </h1>
                    < p className = "text-gray-600 mt-2" > Sign in to your account </p>
                        </div>

    {
        error && (
            <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg mb-6 flex items-center gap-2" >
                <AlertCircle size={ 20 } />
        { error }
        </div>
                )}

<form onSubmit={ handleSubmit } className = "space-y-4" >
    <div>
    <label className="block text-sm font-medium text-gray-700 mb-2" >
        Email Address
            </label>
            < div className = "relative" >
                <Mail className="absolute left-3 top-3 text-gray-400" size = { 20} />
                    <input
                                type="email"
name = "email"
value = { formData.email }
onChange = { handleChange }
placeholder = "Enter your email"
className = "w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
disabled = { isLoading }
    />
    </div>
    </div>

    < div >
    <label className="block text-sm font-medium text-gray-700 mb-2" >
        Password
        </label>
        < div className = "relative" >
            <Lock className="absolute left-3 top-3 text-gray-400" size = { 20} />
                <input
                                type="password"
name = "password"
value = { formData.password }
onChange = { handleChange }
placeholder = "Enter your password"
className = "w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
disabled = { isLoading }
    />
    </div>
    </div>

    < Button
type = "submit"
variant = "primary"
className = "w-full"
disabled = { isLoading }
    >
    { isLoading? 'Signing in...': 'Sign In' }
    </Button>
    </form>

    < div className = "mt-6 text-center" >
        <p className="text-gray-600 text-sm" >
            Don't have an account?{' '}
                < Link to = "/register" className = "text-blue-600 hover:underline font-semibold" >
                    Sign up
                        </Link>
                        </p>
                        </div>
                        </div>
                        </div>
    );
};
