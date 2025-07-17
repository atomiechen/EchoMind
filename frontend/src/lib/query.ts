import { QueryClient } from '@tanstack/react-query'


export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      // staleTime: Infinity,  // never stale unless manually invalidated
      staleTime: 0,  // always stale, so that it refetches on mount
    },
  },
})

export const invalidateQueryId = (queryClient: QueryClient, id: string) => {
  queryClient.invalidateQueries({
    predicate: (query) => {
      const keyObj = query.queryKey?.[0]
      if (typeof keyObj === 'object' && keyObj !== null && '_id' in keyObj) {
        return keyObj._id === id;
      }
      return false;
    },
  });
};
