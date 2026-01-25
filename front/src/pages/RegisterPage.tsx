import React, { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { useAuthStore } from '@/store/useAuthStore';
import { Button } from '@/components/common/Button';
import { Mail, Lock, User, AlertCircle, CheckCircle } from 'lucide-react';

export const RegisterPage: React.FC = () => {
    const navigate = useNavigate();
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

    const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        const { name, value } = e.target;
        setFormData(prev => ({
            ...prev,
            [name]: value,
        }));
        if (error) setError(null);

        // Update validations
        if (name === 'password') {
            setValidations(prev => ({
                ...prev,
                passwordLength: value.length >= 8,
                passwordMatch: value === formData.confirmPassword,
            }));
        } else if (name === 'confirmPassword') {
            setValidations(prev => ({
                ...prev,
                passwordMatch: value === formData.password,
            }));
        } else if (name === 'email') {
            setValidations(prev => ({
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
            navigate('/');
        } catch {
            // Error is already set by the store
        }
    };

    return (
        <div className= "min-h-screen bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center px-4 py-8" >
        <div className="bg-white rounded-lg shadow-2xl p-8 w-full max-w-md" >
            <div className="text-center mb-8" >
                <h1 className="text-3xl font-bold text-gray-800" > Map Adviser </h1>
                    < p className = "text-gray-600 mt-2" > Create your account </p>
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
        Full Name
            </label>
            < div className = "relative" >
                <User className="absolute left-3 top-3 text-gray-400" size = { 20} />
                    <input
                                type="text"
name = "name"
value = { formData.name }
onChange = { handleChange }
placeholder = "Enter your full name"
className = "w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
disabled = { isLoading }
    />
    </div>
    </div>

    < div >
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
{
    formData.email && (
        <div className="mt-1 flex items-center gap-1 text-sm" >
            {
                validations.emailFormat ? (
                    <CheckCircle size= { 16} className="text-green-600" />
                                ) : (
                        <AlertCircle size={ 16} className = "text-red-600" />
                                )
}
<span className={ validations.emailFormat ? 'text-green-600' : 'text-red-600' }>
    { validations.emailFormat ? 'Valid email' : 'Invalid email format' }
    </span>
    </div>
                        )}
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
placeholder = "Enter password (min 8 characters)"
className = "w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
disabled = { isLoading }
    />
    </div>
{
    formData.password && (
        <div className="mt-1 flex items-center gap-1 text-sm" >
            {
                validations.passwordLength ? (
                    <CheckCircle size= { 16} className="text-green-600" />
                                ) : (
                        <AlertCircle size={ 16} className = "text-red-600" />
                                )
}
<span className={ validations.passwordLength ? 'text-green-600' : 'text-red-600' }>
    { validations.passwordLength ? 'Password strong' : 'Min 8 characters required' }
    </span>
    </div>
                        )}
</div>

    < div >
    <label className="block text-sm font-medium text-gray-700 mb-2" >
        Confirm Password
            </label>
            < div className = "relative" >
                <Lock className="absolute left-3 top-3 text-gray-400" size = { 20} />
                    <input
                                type="password"
name = "confirmPassword"
value = { formData.confirmPassword }
onChange = { handleChange }
placeholder = "Confirm your password"
className = "w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
disabled = { isLoading }
    />
    </div>
{
    formData.confirmPassword && (
        <div className="mt-1 flex items-center gap-1 text-sm" >
            {
                validations.passwordMatch ? (
                    <CheckCircle size= { 16} className="text-green-600" />
                                ) : (
                        <AlertCircle size={ 16} className = "text-red-600" />
                                )
}
<span className={ validations.passwordMatch ? 'text-green-600' : 'text-red-600' }>
    { validations.passwordMatch ? 'Passwords match' : 'Passwords do not match' }
    </span>
    </div>
                        )}
</div>

    < Button
type = "submit"
variant = "primary"
className = "w-full mt-6"
disabled = { isLoading || !validations.emailFormat || !validations.passwordLength || !validations.passwordMatch}
                    >
    { isLoading? 'Creating Account...': 'Create Account' }
    </Button>
    </form>

    < div className = "mt-6 text-center" >
        <p className="text-gray-600 text-sm" >
            Already have an account ? { ' '}
                < Link to = "/login" className = "text-blue-600 hover:underline font-semibold" >
                    Sign in
                    </Link>
                    </p>
                    </div>
                    </div>
                    </div>
    );
};
