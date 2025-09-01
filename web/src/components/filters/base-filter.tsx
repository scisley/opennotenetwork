'use client';

import { ReactNode, useState, useEffect } from 'react';
import { ChevronDown, ChevronRight } from 'lucide-react';
import { Checkbox } from '@/components/ui/checkbox';

interface BaseFilterProps {
  title: string;
  isActive?: boolean;
  onActiveChange: (active: boolean) => void;
  children: ReactNode;
  badge?: ReactNode;
}

export function BaseFilter({ 
  title, 
  isActive = false, 
  onActiveChange, 
  children,
  badge 
}: BaseFilterProps) {
  const [isExpanded, setIsExpanded] = useState(isActive);
  
  useEffect(() => {
    setIsExpanded(isActive);
  }, [isActive]);

  const handleToggle = (checked: boolean) => {
    setIsExpanded(checked);
    onActiveChange(checked);
  };

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <button
          onClick={() => handleToggle(!isExpanded)}
          className="flex items-center gap-2 text-sm font-medium hover:text-gray-700"
        >
          {isExpanded ? (
            <ChevronDown className="h-4 w-4" />
          ) : (
            <ChevronRight className="h-4 w-4" />
          )}
          {title}
          {badge}
        </button>
        <Checkbox
          checked={isExpanded}
          onCheckedChange={handleToggle}
          title="Filter for posts with this classification"
        />
      </div>

      {isExpanded && (
        <div className="pl-6">
          {children}
        </div>
      )}
    </div>
  );
}