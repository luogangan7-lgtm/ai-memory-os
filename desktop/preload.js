const { contextBridge } = require('electron');
contextBridge.exposeInMainWorld('memoryOS', {
  platform: process.platform,
  version: '1.0.0',
  serverUrl: 'http://localhost:8000'
});
