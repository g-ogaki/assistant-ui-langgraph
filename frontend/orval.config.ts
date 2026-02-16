import { defineConfig } from 'orval';

export default defineConfig({
  api: {
    input: 'http://localhost:8000/openapi.json',
    output: {
      mode: 'tags-split',
      target: 'lib/api/generated.ts',
      schemas: 'lib/api/model',
      client: 'react-query',
    },
  },
});