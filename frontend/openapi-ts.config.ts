import { defineConfig } from '@hey-api/openapi-ts';

export default defineConfig({
  input: 'openapi.json',
  output: 'src/client',
  plugins: [
    {
      name: '@hey-api/client-fetch',
      // ref: https://github.com/hey-api/openapi-ts/issues/961#issuecomment-3134234022
      throwOnError: true,
    },
    '@tanstack/react-query',
  ],
});
