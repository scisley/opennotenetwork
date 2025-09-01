"use client";

import React from "react";
import DatePicker from "react-datepicker";
import "react-datepicker/dist/react-datepicker.css";
import { Button } from "@/components/ui/button";

interface SimpleDateRangePickerProps {
  startDate?: Date;
  endDate?: Date;
  onStartDateChange?: (date: Date | null) => void;
  onEndDateChange?: (date: Date | null) => void;
  className?: string;
  disabled?: boolean;
}

export function SimpleDateRangePicker({
  startDate,
  endDate,
  onStartDateChange,
  onEndDateChange,
  className,
  disabled = false,
}: SimpleDateRangePickerProps) {
  const presets = [
    {
      label: "Last 3 hours",
      onClick: () => {
        const end = new Date();
        const start = new Date();
        start.setHours(start.getHours() - 3);
        onStartDateChange?.(start);
        onEndDateChange?.(end);
      },
    },
    {
      label: "Last 24 hours",
      onClick: () => {
        const end = new Date();
        const start = new Date();
        start.setDate(start.getDate() - 1);
        onStartDateChange?.(start);
        onEndDateChange?.(end);
      },
    },
    {
      label: "Last 7 days",
      onClick: () => {
        const end = new Date();
        const start = new Date();
        start.setDate(start.getDate() - 7);
        onStartDateChange?.(start);
        onEndDateChange?.(end);
      },
    },
    {
      label: "Last 30 days",
      onClick: () => {
        const end = new Date();
        const start = new Date();
        start.setDate(start.getDate() - 30);
        onStartDateChange?.(start);
        onEndDateChange?.(end);
      },
    },
  ];

  return (
    <div className={className}>
      <div className="flex flex-wrap gap-2 mb-4">
        {presets.map((preset) => (
          <Button
            key={preset.label}
            variant="outline"
            size="sm"
            onClick={preset.onClick}
            disabled={disabled}
            type="button"
          >
            {preset.label}
          </Button>
        ))}
      </div>

      <div className="flex gap-2 flex-wrap items-center">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Start Date & Time
          </label>
          <DatePicker
            selected={startDate}
            onChange={(date) => onStartDateChange?.(date)}
            showTimeSelect
            timeFormat="h:mm aa"
            timeIntervals={15}
            timeCaption="Time"
            dateFormat="MMMM d, yyyy h:mm aa"
            className="w-64 px-3 py-2 border rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            disabled={disabled}
            placeholderText="Select start date & time"
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            End Date & Time
          </label>
          <DatePicker
            selected={endDate}
            onChange={(date) => onEndDateChange?.(date)}
            showTimeSelect
            timeFormat="h:mm aa"
            timeIntervals={15}
            timeCaption="Time"
            dateFormat="MMMM d, yyyy h:mm aa"
            className="w-64 px-3 py-2 border rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            disabled={disabled}
            placeholderText="Select end date & time"
            minDate={startDate || undefined}
          />
        </div>
      </div>
    </div>
  );
}
