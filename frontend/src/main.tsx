import '@/index.css'
import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { Routes } from '@generouted/react-router'

// Import styles of packages that you've installed.
// All packages except `@mantine/hooks` require styles imports
import '@mantine/core/styles.css';
// ‼️ import notifications styles after core package styles
import '@mantine/notifications/styles.css';
import { MantineProvider, rem } from '@mantine/core';
import { Notifications } from '@mantine/notifications';

// Set the base URL for the API client
// ref: https://heyapi.dev/openapi-ts/clients/fetch#setconfig
import { client } from '@/client/client.gen';
import { API_BASE_URL } from '@/lib/constants';

// React Query
import { QueryClientProvider } from '@tanstack/react-query';
import { queryClient } from '@/lib/query';
import { ReactFlowProvider } from '@xyflow/react';

// i18n (internationalization)
import '@/i18n';


client.setConfig({
  baseUrl: API_BASE_URL,
  credentials: 'include',
});

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <MantineProvider>
      <Notifications position="top-right" zIndex={1000} styles={{
        root: {
          maxWidth: rem(300),
        }
      }}/>
      <QueryClientProvider client={queryClient}>
        <ReactFlowProvider>
          <Routes />
        </ReactFlowProvider>
      </QueryClientProvider>
    </MantineProvider>
  </StrictMode>
)
