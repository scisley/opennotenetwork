import { useState, useEffect } from 'react';

export function useLocalStorage<T>(key: string, defaultValue: T): [T, (value: T) => void] {
  const [value, setValue] = useState<T>(defaultValue);
  const [initialized, setInitialized] = useState(false);

  // Load from localStorage on mount
  useEffect(() => {
    if (!initialized) {
      try {
        const item = localStorage.getItem(key);
        if (item !== null) {
          setValue(JSON.parse(item));
        }
      } catch (error) {
        console.error(`Error loading ${key} from localStorage:`, error);
      }
      setInitialized(true);
    }
  }, [key, initialized]);

  // Save to localStorage whenever value changes
  useEffect(() => {
    if (initialized) {
      try {
        localStorage.setItem(key, JSON.stringify(value));
      } catch (error) {
        console.error(`Error saving ${key} to localStorage:`, error);
      }
    }
  }, [key, value, initialized]);

  return [value, setValue];
}