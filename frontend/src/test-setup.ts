import '@testing-library/jest-dom/vitest';
import { cleanup, configure } from '@testing-library/react';
import { afterEach, vi } from 'vitest';
// findBy*/waitFor wait up to 5 s instead of 1 s: the lazy policy list and page switches can be
// slower than that while many test files run at once.
configure({ asyncUtilTimeout: 5000 });
afterEach(() => { cleanup(); vi.unstubAllGlobals(); });
