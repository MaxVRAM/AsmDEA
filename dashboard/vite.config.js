import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'
import fs from 'node:fs'
import path from 'node:path'
import { spawn } from 'node:child_process'

export default defineConfig(({ mode }) => {
  const parentDir = path.resolve(process.cwd(), '..')
  const env = loadEnv(mode, parentDir, '')
  const reportsDir = env.OUTPUT_PATH && path.resolve(parentDir, env.OUTPUT_PATH)
  const python = path.resolve(parentDir, '.venv', 'Scripts', 'python.exe')

  return {
    plugins: [
      react(),
      {
        name: 'asmdea-reports',
        configureServer(server) {
          server.middlewares.use('/reports', (req, res, next) => {
            const file = reportsDir + req.url
            fs.createReadStream(file).on('error', next).pipe(res)
          })

          server.middlewares.use('/api/run', (req, res, next) => {
            if (req.method !== 'POST') return next()
            let stderr = ''
            const child = spawn(python, ['asmdea.py', 'all'], { cwd: parentDir })
            child.stderr.on('data', d => { stderr += d.toString() })
            child.stdout.on('data', d => { console.log(d.toString()) })
            child.on('close', code => {
              res.setHeader('Content-Type', 'application/json')
              if (code === 0) {
                res.end(JSON.stringify({ ok: true }))
              } else {
                res.statusCode = 500
                res.end(JSON.stringify({ ok: false, error: stderr || `exit code ${code}` }))
              }
            })
          })
        }
      }
    ],
    server: { port: 5173, open: true },
    // Pre-bundle elkjs so the layout engine's dynamic import resolves cleanly on
    // first use, instead of racing Vite's on-demand dep optimization.
    optimizeDeps: { include: ['elkjs/lib/elk.bundled.js'] }
  }
})