'use client';

import * as React from 'react';
import { cn } from '@/lib/utils/cn';

export interface ToggleSwitchProps extends Omit<React.InputHTMLAttributes<HTMLInputElement>, 'type'> {
  label?: string;
  description?: string;
}

const ToggleSwitch = React.forwardRef<HTMLInputElement, ToggleSwitchProps>(
  ({ className, label, description, id, ...props }, ref) => {
    const inputId = id || React.useId();

    return (
      <div className={cn('flex items-center', className)}>
        <label className="relative inline-flex cursor-pointer items-center">
          <input ref={ref} type="checkbox" id={inputId} className="peer sr-only" {...props} />
          <div className="peer h-6 w-11 rounded-full bg-gray-200 after:absolute after:left-[2px] after:top-[2px] after:h-5 after:w-5 after:rounded-full after:border after:border-gray-300 after:bg-white after:transition-all after:content-[''] peer-checked:bg-primary peer-checked:after:translate-x-full peer-checked:after:border-white peer-focus:outline-none peer-focus:ring-2 peer-focus:ring-ring peer-focus:ring-offset-2" />
        </label>
        {(label || description) && (
          <div className="ml-3">
            {label && (
              <label htmlFor={inputId} className="text-sm font-medium text-foreground cursor-pointer">
                {label}
              </label>
            )}
            {description && <p className="text-sm text-muted-foreground">{description}</p>}
          </div>
        )}
      </div>
    );
  }
);
ToggleSwitch.displayName = 'ToggleSwitch';

export { ToggleSwitch };
