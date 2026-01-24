import React from 'react';
import { twMerge } from 'tailwind-merge';
import { Loader2 } from 'lucide-react';

interface LoaderProps {
  className?: string;
  size?: number;
}

export const Loader: React.FC<LoaderProps> = ({ className, size = 24 }) => {
  return (
    <Loader2 
      className={twMerge('animate-spin text-current', className)} 
      size={size} 
    />
  );
};
