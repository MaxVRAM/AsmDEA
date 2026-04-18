import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'
import fs from 'node:fs'

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), 'ASMDEA_')
  const reportsDir = env.ASMDEA_REPORTS_DIR

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