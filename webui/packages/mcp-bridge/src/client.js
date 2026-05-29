export class MemoryOSClient {
  constructor({ token, server }) {
    this.token = token;
    this.server = server.replace(/\/$/, '');
    this.postUrl = null;
    this.connected = false;
    this.pendingRequests = new Map();
    this.nextId = 1;
    this.headers = {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json',
      'User-Agent': 'ai-memory-os-mcp/1.0',
    };
  }

  async connect() {
    this._shouldReconnect = true;
    this._reconnectAttempt = 0;
    while (this._shouldReconnect) {
      try {
        await this._doConnect();
        this._reconnectAttempt = 0;
        return;
      } catch (err) {
        this._reconnectAttempt++;
        const delay = Math.min(1000 * Math.pow(2, this._reconnectAttempt), 30000);
        process.stderr.write(`[Memory OS] Connection failed (attempt ${this._reconnectAttempt}), retrying in ${delay}ms: ${err.message}
`);
        await new Promise(r => setTimeout(r, delay));
      }
    }
  }

  async _doConnect() {
    return new Promise(async (resolve, reject) => {
      let resolved = false;
      const resolveConnect = () => {
        if (!resolved) {
          resolved = true;
          resolve();
        }
      };
      const rejectConnect = (err) => {
        if (!resolved) {
          resolved = true;
          reject(err);
        }
      };

      try {
        const url = `${this.server}/mcp?token=${this.token}`;
        const res = await fetch(url, {
          headers: { 'Accept': 'text/event-stream' }
        });
        if (!res.ok) {
          const errText = await res.text().catch(() => res.statusText);
          throw new Error(`API Handshake Error ${res.status}: ${errText}`);
        }
        if (!res.body) {
          throw new Error("Response body is null");
        }

        // Start background reader
        this._readStream(res.body.getReader(), resolveConnect, rejectConnect);

      } catch (err) {
        rejectConnect(err);
      }
    });
  }

  async _readStream(reader, resolveConnect, rejectConnect) {
    const decoder = new TextDecoder();
    let buffer = '';
    try {
      while (true) {
        const { value, done } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });

        let eventBoundary;
        while ((eventBoundary = buffer.indexOf('\n\n')) !== -1) {
          const block = buffer.slice(0, eventBoundary);
          buffer = buffer.slice(eventBoundary + 2);
          this._handleEventBlock(block, resolveConnect);
        }
      }
    } catch (err) {
      process.stderr.write(`[Memory OS] SSE stream error: ${err.message}\n`);
      rejectConnect(err);
    } finally {
      this.connected = false;
      const closeErr = new Error("SSE connection closed");
      for (const [id, pending] of this.pendingRequests) {
        pending.reject(closeErr);
      }
      this.pendingRequests.clear();
    }
  }

  _handleEventBlock(block, resolveConnect) {
    const lines = block.split('\n');
    let eventType = 'message';
    let dataStr = '';
    for (const line of lines) {
      if (line.startsWith('event:')) {
        eventType = line.slice(6).trim();
      } else if (line.startsWith('data:')) {
        dataStr += line.slice(5).trim();
      }
    }

    if (eventType === 'endpoint') {
      const postPath = dataStr.trim();
      this.postUrl = `${this.server}${postPath}`;
      this.connected = true;
      resolveConnect();
    } else if (eventType === 'message') {
      try {
        const msg = JSON.parse(dataStr);
        if (msg.id !== undefined) {
          const pending = this.pendingRequests.get(msg.id);
          if (pending) {
            this.pendingRequests.delete(msg.id);
            if (msg.error) {
              pending.reject(new Error(msg.error.message || JSON.stringify(msg.error)));
            } else {
              pending.resolve(msg.result);
            }
          }
        }
      } catch (e) {
        process.stderr.write(`[Memory OS] Failed to parse message JSON: ${e.message}\n`);
      }
    }
  }


  async _reconnect() {
    this._reconnectAttempt = 0;
    while (this._shouldReconnect) {
      try {
        process.stderr.write(`[Memory OS] Reconnecting (attempt ${this._reconnectAttempt + 1})...\n`);
        const url = `${this.server}/mcp?token=${this.token}`;
        const res = await fetch(url, { headers: { 'Accept': 'text/event-stream' } });
        if (!res.ok) throw new Error(`Handshake ${res.status}`);
        if (!res.body) throw new Error("No body");
        await this._doConnect();
        process.stderr.write('[Memory OS] Reconnected successfully\n');
        return;
      } catch (err) {
        this._reconnectAttempt++;
        const delay = Math.min(1000 * Math.pow(2, this._reconnectAttempt), 30000);
        process.stderr.write(`[Memory OS] Reconnect failed (attempt ${this._reconnectAttempt}): ${err.message}, retrying in ${delay}ms\n`);
        await new Promise(r => setTimeout(r, delay));
      }
    }
  }

  async sendRequest(method, params = {}) {
    if (!this.connected || !this.postUrl) {
      throw new Error("Client is not connected to SSE server");
    }
    const id = this.nextId++;
    return new Promise(async (resolve, reject) => {
      this.pendingRequests.set(id, { resolve, reject });

      // Timeout safety
      const timeoutId = setTimeout(() => {
        if (this.pendingRequests.has(id)) {
          this.pendingRequests.delete(id);
          reject(new Error(`Request ${method} (id: ${id}) timed out after 30s`));
        }
      }, 30000);

      try {
        const res = await fetch(this.postUrl, {
          method: 'POST',
          headers: this.headers,
          body: JSON.stringify({ jsonrpc: '2.0', id, method, params })
        });
        if (!res.ok) {
          clearTimeout(timeoutId);
          this.pendingRequests.delete(id);
          const errText = await res.text().catch(() => res.statusText);
          throw new Error(`Failed to POST request: ${res.status} ${errText}`);
        }
        // POST response is usually just acknowledgment like {"status":"ok"}, actual result comes via SSE.
      } catch (err) {
        clearTimeout(timeoutId);
        this.pendingRequests.delete(id);
        reject(err);
      }
    });
  }
}
