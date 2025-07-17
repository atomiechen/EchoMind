import { useState } from "react";

/**
 * A custom hook that calls a callback function when a specific value changes.
 * It does not use `useEffect`, for cases where you don't want rendering stale data.
 * 
 * Will **NOT** run on initial render.
 *
 * @param callback - The function to call when the value changes.
 * @param depValue - The value to watch for changes.
 * 
 * ref: https://react.dev/learn/you-might-not-need-an-effect#adjusting-some-state-when-a-prop-changes
 */
export function useValueChange<S>(
  callback: (value: S) => void,
  depValue: S,
) {
  const [value, setValue] = useState(depValue);
  if (value !== depValue) {
    setValue(depValue);
    callback(depValue);
  }
  return value;
}
