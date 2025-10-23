'use client';

import { useState, useEffect } from 'react';
import { ChevronDown, ChevronRight } from 'lucide-react';
import { Label } from '@/components/ui/label';
import { Input } from '@/components/ui/input';
import { Checkbox } from '@/components/ui/checkbox';

export interface DateRangeValue {
  after?: string;  // ISO datetime string
  before?: string; // ISO datetime string
}

interface DateRangeFilterProps {
  value: DateRangeValue;
  onChange: (value: DateRangeValue) => void;
}

export function DateRangeFilter({ value, onChange }: DateRangeFilterProps) {
  // Initialize expanded state based on whether there are active filters
  const hasActiveFilter = !!(value.after || value.before);
  const [isOpen, setIsOpen] = useState(hasActiveFilter);

  // Parse ISO string to date and time parts
  const parseDateTime = (isoString?: string) => {
    if (!isoString) return { date: '', time: '' };
    try {
      const dt = new Date(isoString);
      const year = dt.getFullYear();
      const month = String(dt.getMonth() + 1).padStart(2, '0');
      const day = String(dt.getDate()).padStart(2, '0');
      const hours = String(dt.getHours()).padStart(2, '0');
      const minutes = String(dt.getMinutes()).padStart(2, '0');
      return {
        date: `${year}-${month}-${day}`,
        time: `${hours}:${minutes}`
      };
    } catch {
      return { date: '', time: '' };
    }
  };

  // Local state for input values - only update parent on blur/enter
  const [localAfterDate, setLocalAfterDate] = useState(parseDateTime(value.after).date);
  const [localAfterTime, setLocalAfterTime] = useState(parseDateTime(value.after).time);
  const [localBeforeDate, setLocalBeforeDate] = useState(parseDateTime(value.before).date);
  const [localBeforeTime, setLocalBeforeTime] = useState(parseDateTime(value.before).time);

  // Sync local state when props change (but not while typing)
  useEffect(() => {
    const after = parseDateTime(value.after);
    const before = parseDateTime(value.before);
    setLocalAfterDate(after.date);
    setLocalAfterTime(after.time);
    setLocalBeforeDate(before.date);
    setLocalBeforeTime(before.time);
  }, [value.after, value.before]);

  // Update expansion state when value changes
  useEffect(() => {
    setIsOpen(!!(value.after || value.before));
  }, [value.after, value.before]);

  // Combine and update parent
  const updateAfter = () => {
    if (!localAfterDate) {
      onChange({ ...value, after: undefined });
    } else {
      const timeStr = localAfterTime || '00:00';
      try {
        const isoString = new Date(`${localAfterDate}T${timeStr}:00`).toISOString();
        onChange({ ...value, after: isoString });
      } catch {
        // Invalid date, don't update
      }
    }
  };

  const updateBefore = () => {
    if (!localBeforeDate) {
      onChange({ ...value, before: undefined });
    } else {
      const timeStr = localBeforeTime || '23:59';
      try {
        const isoString = new Date(`${localBeforeDate}T${timeStr}:00`).toISOString();
        onChange({ ...value, before: isoString });
      } catch {
        // Invalid date, don't update
      }
    }
  };

  const handleToggle = (checked: boolean) => {
    setIsOpen(checked);
    // When unchecking, clear the date range
    if (!checked) {
      setLocalAfterDate('');
      setLocalAfterTime('');
      setLocalBeforeDate('');
      setLocalBeforeTime('');
      onChange({});
    }
  };

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <button
          onClick={() => handleToggle(!isOpen)}
          className="flex items-center gap-2 text-sm font-medium hover:text-gray-700"
        >
          {isOpen ? (
            <ChevronDown className="h-4 w-4" />
          ) : (
            <ChevronRight className="h-4 w-4" />
          )}
          Date Range
        </button>
        <Checkbox
          checked={isOpen}
          onCheckedChange={handleToggle}
          title="Filter by date range"
        />
      </div>

      {isOpen && (
        <div className="pl-6 space-y-3">
          <p className="text-xs text-gray-500">
            Filter posts by creation date and time
          </p>

          <div className="space-y-3">
            <div>
              <div className="flex items-center justify-between mb-1">
                <Label className="text-xs text-gray-600">After</Label>
                {localAfterDate && (
                  <button
                    onClick={() => {
                      setLocalAfterDate('');
                      setLocalAfterTime('');
                      onChange({ ...value, after: undefined });
                    }}
                    className="text-xs text-blue-600 hover:text-blue-700"
                  >
                    Clear
                  </button>
                )}
              </div>
              <div className="flex gap-2">
                <Input
                  type="date"
                  value={localAfterDate}
                  onChange={(e) => setLocalAfterDate(e.target.value)}
                  onBlur={updateAfter}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter') updateAfter();
                  }}
                  className="h-8 text-xs w-40"
                  placeholder="YYYY-MM-DD"
                />
                <Input
                  type="time"
                  value={localAfterTime}
                  onChange={(e) => setLocalAfterTime(e.target.value)}
                  onBlur={updateAfter}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter') updateAfter();
                  }}
                  className="h-8 text-xs w-28"
                  placeholder="HH:MM"
                />
              </div>
            </div>

            <div>
              <div className="flex items-center justify-between mb-1">
                <Label className="text-xs text-gray-600">Before</Label>
                {localBeforeDate && (
                  <button
                    onClick={() => {
                      setLocalBeforeDate('');
                      setLocalBeforeTime('');
                      onChange({ ...value, before: undefined });
                    }}
                    className="text-xs text-blue-600 hover:text-blue-700"
                  >
                    Clear
                  </button>
                )}
              </div>
              <div className="flex gap-2">
                <Input
                  type="date"
                  value={localBeforeDate}
                  onChange={(e) => setLocalBeforeDate(e.target.value)}
                  onBlur={updateBefore}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter') updateBefore();
                  }}
                  className="h-8 text-xs w-40"
                  placeholder="YYYY-MM-DD"
                />
                <Input
                  type="time"
                  value={localBeforeTime}
                  onChange={(e) => setLocalBeforeTime(e.target.value)}
                  onBlur={updateBefore}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter') updateBefore();
                  }}
                  className="h-8 text-xs w-28"
                  placeholder="HH:MM"
                />
              </div>
            </div>
          </div>

        </div>
      )}
    </div>
  );
}