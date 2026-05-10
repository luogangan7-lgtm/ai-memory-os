const { app, BrowserWindow, dialog, Tray, Menu } = require('electron');
const { spawn } = require('child_process');
const path = require('path');
const http = require('http');

let mainWindow = null;
let backendProcess = null;
let tray = null;
const PORT = 8003;

// Resolve paths based on environment
const isPackaged = app.isPackaged;
const baseDir = isPackaged ? process.resourcesPath : path.join(__dirname, '..');

function checkDocker() {
    return new Promise((resolve) => {
        const { exec } = require('child_process');
        exec('docker -v', (error) => {
            if (error) {
                resolve(false);
            } else {
                resolve(true);
            }
        });
    });
}

async function handleDockerMissing() {
    const { shell } = require('electron');
    const result = await dialog.showMessageBox({
        type: 'info',
        title: 'Docker 环境检测',
        message: '未检测到 Docker 环境',
        detail: 'AI Memory OS 推荐使用 Docker 以获得完整性能（支持 PostgreSQL/Qdrant/Neo4j）。\n\n我们将自动为您开启“零依赖模式”（Standalone）。如果您想体验完整版，可以点击下方按钮直接下载 Docker Desktop。',
        buttons: ['继续 (Standalone)', '立即下载 Docker'],
        defaultId: 0
    });

    if (result.response === 1) {
        let dockerUrl = 'https://www.docker.com/products/docker-desktop/';
        if (process.platform === 'darwin') {
            dockerUrl = process.arch === 'arm64' 
                ? 'https://desktop.docker.com/mac/main/arm64/Docker.dmg' 
                : 'https://desktop.docker.com/mac/main/amd64/Docker.dmg';
        } else if (process.platform === 'win32') {
            dockerUrl = 'https://desktop.docker.com/win/main/amd64/Docker%20Desktop%20Installer.exe';
        }
        shell.openExternal(dockerUrl);
    }
}

function startBackend() {
    let executable = '';
    let args = [];
    let cwd = baseDir;

    if (isPackaged) {
        // In packaged app, look for the PyInstaller binary
        const binName = process.platform === 'win32' ? 'memory-os-backend.exe' : 'memory-os-backend';
        executable = path.join(baseDir, 'bin', binName);
    } else {
        // In dev, use the venv python
        executable = path.join(baseDir, '.venv', process.platform === 'win32' ? 'Scripts/python.exe' : 'bin/python');
        args = ['-m', 'uvicorn', 'backend.main:app', '--host', '127.0.0.1', '--port', String(PORT)];
        cwd = baseDir;
    }

    console.log(`Starting backend: ${executable} ${args.join(' ')}`);

    backendProcess = spawn(executable, args, {
        cwd: cwd,
        env: { ...process.env, PORT: String(PORT), PYTHONPATH: baseDir }
    });

    backendProcess.stdout.on('data', (data) => console.log(`Backend: ${data}`));
    backendProcess.stderr.on('data', (data) => console.error(`Backend Error: ${data}`));
}

function checkServer(callback) {
    const check = () => {
        const req = http.get(`http://127.0.0.1:${PORT}/admin/setup/status`, (res) => {
            if (res.statusCode === 200) {
                callback();
            } else {
                setTimeout(check, 1000);
            }
        });
        req.on('error', () => setTimeout(check, 1000));
    };
    check();
}

function createMainWindow() {
    mainWindow = new BrowserWindow({
        width: 1280,
        height: 850,
        title: 'AI Memory OS',
        icon: path.join(__dirname, 'icon.png'),
        webPreferences: {
            nodeIntegration: false,
            contextIsolation: true
        }
    });

    // Check setup status and redirect
    http.get(`http://127.0.0.1:${PORT}/admin/setup/status`, (res) => {
        let data = '';
        res.on('data', (chunk) => data += chunk);
        res.on('end', () => {
            const status = JSON.parse(data);
            if (status.complete) {
                mainWindow.loadURL(`http://127.0.0.1:${PORT}/manage/`);
            } else {
                mainWindow.loadURL(`http://127.0.0.1:${PORT}/manage/wizard.html`);
            }
        });
    });

    mainWindow.on('closed', () => {
        mainWindow = null;
    });
}

function createTray() {
    tray = new Tray(path.join(__dirname, 'icon.png'));
    const contextMenu = Menu.buildFromTemplate([
        { label: '打开控制台', click: () => { if (mainWindow) mainWindow.show(); else createMainWindow(); } },
        { type: 'separator' },
        { label: '退出系统', click: () => { app.quit(); } }
    ]);
    tray.setToolTip('AI Memory OS');
    tray.setContextMenu(contextMenu);
}

app.on('ready', async () => {
    const hasDocker = await checkDocker();
    if (!hasDocker) {
        await handleDockerMissing();
    }
    startBackend();
    createTray();
    checkServer(createMainWindow);
});

app.on('window-all-closed', () => {
    // Keep backend running in tray
    if (process.platform !== 'darwin') {
        // On Windows/Linux, we might want to stay in tray
    }
});

app.on('will-quit', () => {
    if (backendProcess) {
        backendProcess.kill();
    }
});
