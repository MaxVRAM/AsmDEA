import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'
import fs from 'node:fs'
import path from 'node:path'

export default defineConfig(({ mode }) => {
  const parentDir = path.resolve(process.cwd(), '..')
  const env = loadEnv(mode, parentDir, '')
  const reportsDir = env.OUTPUT_PATH && path.resolve(parentDir, env.OUTPUT_PATH)

  return {
    plugins: [
      react(),
      reportsDir && {
        name: 'asmdea-reports',
        configureServer(server) {
          server.middlewares.use('/reports', (req, res, next) => {
            const file = reportsDir + req.url
            fs.createReadStream(file).on('error', next).pipe(res)
          })
        }
      }
    ],
    server: { port: 5173, open: true }
  }
})