// Adgine 媒体发布桥接服务（对齐 wechatsync ws-bridge 模式，零依赖版）。
// 用 Node 内置 http + 手写 RFC6455 WebSocket 帧实现，无需 npm install（skill 开箱即用）。
//
// 两个端口：
//   WS  9377 —— Chrome 扩展主动连（带 Token 鉴权），桥把指令转发给它
//   HTTP 9378 —— skill 脚本（save_draft.py 等）调，桥把指令经 WS 转给扩展
//
// 主备协商：第一个实例监听 9377/9378 当 PRIMARY；后续实例发现 EADDRINUSE
// 则降级为 SECONDARY，把 HTTP 请求转发给已存在的 PRIMARY（9378）。僵尸
// PRIMARY（9377 被占但 9378 不应答）时尝试接管。

import http from 'node:http'
import crypto from 'node:crypto'

const REQUEST_TIMEOUT = 6 * 60 * 1000
const WS_GUID = '258EAFA5-E914-47DA-95CA-C5AB0DC85B11'

// ---- 极简 WebSocket 帧编解码（文本帧，无分片/二进制）----
function wsAccept(key) {
  return crypto.createHash('sha1').update(key + WS_GUID).digest('base64')
}

function decodeFrames(buffer) {
  const frames = []
  let offset = 0
  while (offset + 2 <= buffer.length) {
    const b0 = buffer[offset]
    const b1 = buffer[offset + 1]
    const opcode = b0 & 0x0f
    const masked = (b1 & 0x80) !== 0
    let len = b1 & 0x7f
    let headerLen = 2
    if (len === 126) {
      if (offset + 4 > buffer.length) break
      len = buffer.readUInt16BE(offset + 2)
      headerLen = 4
    } else if (len === 127) {
      if (offset + 10 > buffer.length) break
      len = Number(buffer.readBigUInt64BE(offset + 2))
      headerLen = 10
    }
    const maskLen = masked ? 4 : 0
    const frameEnd = offset + headerLen + maskLen + len
    if (frameEnd > buffer.length) break
    let payload = buffer.subarray(offset + headerLen + maskLen, frameEnd)
    if (masked) {
      const mask = buffer.subarray(offset + headerLen, offset + headerLen + 4)
      payload = Buffer.from(payload)
      for (let i = 0; i < payload.length; i++) payload[i] ^= mask[i & 3]
    }
    frames.push({ opcode, payload })
    offset = frameEnd
  }
  return { frames, rest: buffer.subarray(offset) }
}

function encodeTextFrame(text) {
  const payload = Buffer.from(text, 'utf8')
  const len = payload.length
  let header
  if (len < 126) {
    header = Buffer.from([0x81, len])
  } else if (len < 65536) {
    header = Buffer.alloc(4)
    header[0] = 0x81
    header[1] = 126
    header.writeUInt16BE(len, 2)
  } else {
    header = Buffer.alloc(10)
    header[0] = 0x81
    header[1] = 127
    header.writeBigUInt64BE(BigInt(len), 2)
  }
  return Buffer.concat([header, payload])
}

export class PublishBridge {
  constructor(port = 9377, { token = '', silent = false } = {}) {
    this.port = port
    // Token 由扩展在 WS 握手时推过来并记住（无需用户/skill 配置）。
    // 仅在桥与扩展之间起防伪作用；skill 调 HTTP 口时桥自动带上，用户无感。
    this.token = token || process.env.ADGINE_PUBLISH_TOKEN || ''
    this.silent = silent
    this.wsServer = null
    this.httpServer = null
    this.client = null
    this.isServerMode = false
    this.pending = new Map()
    this.connectionResolvers = []
    this._idSeq = 1
  }

  _log(...args) {
    if (!this.silent) console.error('[bridge]', ...args)
  }

  async start() {
    try {
      await this._startServer()
      this.isServerMode = true
      this._log(`PRIMARY (WS:${this.port} HTTP:${this.port + 1})`)
    } catch (e) {
      if (e.code === 'EADDRINUSE') {
        this.isServerMode = false
        this._log(`SECONDARY (forward to localhost:${this.port + 1})`)
      } else {
        throw e
      }
    }
  }

  _startServer() {
    return new Promise((resolve, reject) => {
      this.wsServer = http.createServer()
      this.wsServer.on('upgrade', (req, socket) => {
        const key = req.headers['sec-websocket-key']
        if (!key) {
          socket.destroy()
          return
        }
        socket.write(
          'HTTP/1.1 101 Switching Protocols\r\n' +
            'Upgrade: websocket\r\n' +
            'Connection: Upgrade\r\n' +
            `Sec-WebSocket-Accept: ${wsAccept(key)}\r\n\r\n`
        )
        this._onExtensionConnect(socket)
      })
      // 只绑 127.0.0.1：桥只服务本机扩展与 skill，外部网络摸不到
      this.wsServer.listen(this.port, '127.0.0.1', () => {
        this._log(`WS listening on 127.0.0.1:${this.port}`)
        this._startHttpApi().then(resolve, reject)
      })
      this.wsServer.on('error', reject)
    })
  }

  _onExtensionConnect(socket) {
    this._log('extension connected')
    const conn = { socket, buffer: Buffer.alloc(0) }
    this.client = conn
    for (const r of this.connectionResolvers.splice(0)) r()
    socket.on('data', (chunk) => {
      conn.buffer = Buffer.concat([conn.buffer, chunk])
      const { frames, rest } = decodeFrames(conn.buffer)
      conn.buffer = rest
      for (const f of frames) {
        if (f.opcode === 0x1) this._onMessage(f.payload.toString('utf8'))
        else if (f.opcode === 0x8) socket.end()
      }
    })
    socket.on('close', () => {
      this._log('extension disconnected')
      if (this.client === conn) this.client = null
    })
    socket.on('error', () => {
      if (this.client === conn) this.client = null
    })
  }

  _startHttpApi() {
    return new Promise((resolve, reject) => {
      this.httpServer = http.createServer((req, res) => {
        res.setHeader('Access-Control-Allow-Origin', '*')
        res.setHeader('Access-Control-Allow-Methods', 'POST, GET, OPTIONS')
        res.setHeader('Access-Control-Allow-Headers', 'Content-Type')
        if (req.method === 'OPTIONS') {
          res.writeHead(200); res.end(); return
        }
        if (req.method === 'GET' && req.url === '/status') {
          res.writeHead(200, { 'Content-Type': 'application/json' })
          res.end(JSON.stringify({ connected: this.isConnected(), mode: 'primary' }))
          return
        }
        if (req.method === 'POST' && req.url === '/request') {
          let body = ''
          req.on('data', (c) => (body += c))
          req.on('end', async () => {
            try {
              const { method, params, token } = JSON.parse(body)
              const result = await this._requestInternal(method, params, token)
              res.writeHead(200, { 'Content-Type': 'application/json' })
              res.end(JSON.stringify({ result }))
            } catch (e) {
              res.writeHead(500, { 'Content-Type': 'application/json' })
              res.end(JSON.stringify({ error: e.message }))
            }
          })
          return
        }
        res.writeHead(404); res.end('Not found')
      })
      this.httpServer.listen(this.port + 1, '127.0.0.1', () => {
        this._log(`HTTP API on 127.0.0.1:${this.port + 1}`)
        resolve()
      })
      this.httpServer.on('error', reject)
    })
  }

  _onMessage(data) {
    let msg
    try {
      msg = JSON.parse(data)
    } catch {
      return
    }
    // 扩展握手后推 Token 注册（免用户配置）
    if (msg.type === 'register' && typeof msg.token === 'string' && msg.token) {
      this.token = msg.token
      this._log('extension registered token')
      return
    }
    const entry = this.pending.get(msg.id)
    if (!entry) return
    this.pending.delete(msg.id)
    clearTimeout(entry.timeout)
    if (msg.error) entry.reject(new Error(msg.error))
    else entry.resolve(msg.result)
  }

  _sendToExtension(text) {
    if (this.client?.socket?.writable) {
      this.client.socket.write(encodeTextFrame(text))
    }
  }

  async _requestInternal(method, params, _token) {
    // skill 调 HTTP 口无需带 Token：桥转发时自动带上与扩展协商好的 Token。
    // 安全边界 = 只绑 127.0.0.1 + 扩展侧校验 Token，本机外部进程摸不到桥。
    if (!this.isConnected()) {
      throw new Error('Chrome 扩展未连接：请确认已安装 Adgine 同步助手扩展并开启「媒体发布桥接」')
    }
    const id = `r${this._idSeq++}`
    return new Promise((resolve, reject) => {
      const timeout = setTimeout(() => {
        this.pending.delete(id)
        reject(new Error(`请求超时: ${method}`))
      }, REQUEST_TIMEOUT)
      this.pending.set(id, { resolve, reject, timeout })
      this._sendToExtension(JSON.stringify({ id, method, token: this.token, params }))
    })
  }

  isConnected() {
    return this.client !== null && this.client.socket?.writable === true
  }

  getMode() {
    return this.isServerMode ? 'primary' : 'secondary'
  }

  async _checkPrimaryHealth() {
    try {
      const res = await fetch(`http://localhost:${this.port + 1}/status`, {
        signal: AbortSignal.timeout(2000),
      })
      const data = await res.json()
      return { connected: Boolean(data.connected) }
    } catch {
      return { connected: false, error: 'primary not reachable' }
    }
  }

  async _tryPromote() {
    for (let i = 0; i < 5; i++) {
      try {
        await this._startServer()
        this.isServerMode = true
        this._log(`promoted to PRIMARY (WS:${this.port} HTTP:${this.port + 1})`)
        return true
      } catch {
        await new Promise((r) => setTimeout(r, 1000))
      }
    }
    return false
  }

  async _requestViaHttp(method, params, token) {
    const res = await fetch(`http://localhost:${this.port + 1}/request`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ method, params, token }),
      signal: AbortSignal.timeout(REQUEST_TIMEOUT),
    })
    const data = await res.json()
    if (data.error) throw new Error(data.error)
    return data.result
  }

  async _requestViaSecondary(method, params, token, retries = 3) {
    let lastError = new Error('primary not available')
    for (let i = 0; i < retries; i++) {
      if (i > 0) await new Promise((r) => setTimeout(r, 1000 * i))
      const health = await this._checkPrimaryHealth()
      if (!health.connected) {
        if (health.error?.includes('not reachable')) {
          const promoted = await this._tryPromote()
          if (promoted && this.isConnected()) {
            return this._requestInternal(method, params, token)
          }
        }
        lastError = new Error(health.error || 'PRIMARY 实例不可用')
        continue
      }
      try {
        return await this._requestViaHttp(method, params, token)
      } catch (e) {
        lastError = e
      }
    }
    throw lastError
  }

  async request(method, params, token) {
    if (this.isServerMode) return this._requestInternal(method, params, token ?? this.token)
    return this._requestViaSecondary(method, params, token ?? this.token)
  }

  waitForConnection(timeoutMs = 60000) {
    if (this.isConnected()) return Promise.resolve()
    const start = Date.now()
    return new Promise((resolve, reject) => {
      const poll = () => {
        if (Date.now() - start > timeoutMs) {
          reject(new Error('timeout: 等待 Chrome 扩展连接超时，请确认 Adgine 同步助手已开启「媒体发布桥接」'))
          return
        }
        if (this.isConnected()) {
          resolve()
          return
        }
        setTimeout(poll, 1000)
      }
      poll()
    })
  }

  stop() {
    if (this.wsServer) this.wsServer.close()
    if (this.httpServer) this.httpServer.close()
    if (this.client?.socket) this.client.socket.destroy()
  }
}

if (import.meta.url === `file://${process.argv[1]}`) {
  const port = Number(process.env.ADGINE_PUBLISH_PORT || 9377)
  const bridge = new PublishBridge(port)
  await bridge.start()
  if (bridge.getMode() === 'secondary') {
    console.error('[bridge] 已有 PRIMARY 在运行，本实例作为 SECONDARY 待命')
  } else {
    console.error('[bridge] 等待 Chrome 扩展连接…')
  }
  process.on('SIGINT', () => { bridge.stop(); process.exit(0) })
  process.on('SIGTERM', () => { bridge.stop(); process.exit(0) })
}
