'use client';

import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { ReactQueryDevtools } from '@tanstack/react-query-devtools';
import { useState, useRef, createContext, useContext } from 'react';
import type { RefObject } from 'react';

const ThreadIdContext = createContext<RefObject<string | null> | null>(null);

export function useThreadId() {
  const context = useContext(ThreadIdContext);
  if (context === null) {
    throw new Error("useThreadId must be used within a Providers");
  }
  return context;
}

export default function Providers({ children }: { children: React.ReactNode }) {
  const [queryClient] = useState(() => new QueryClient());
  const threadIdRef = useRef<string | null>(null);

  return (
    <QueryClientProvider client={queryClient}>
      <ThreadIdContext.Provider value={threadIdRef}>
        {children}
      </ThreadIdContext.Provider>
      <ReactQueryDevtools initialIsOpen={false} />
    </QueryClientProvider>
  );
}