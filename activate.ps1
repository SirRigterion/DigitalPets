# 🚀 Unified Activator Script for Windows - v4 (FINAL)
param([string]$Mode = "", [switch]$Help)

# ─────────────────────────────────────────────────────
# 🎨 Цвета
$Colors = @{
    Info    = [System.ConsoleColor]::Cyan
    Success = [System.ConsoleColor]::Green
    Warn    = [System.ConsoleColor]::Yellow
    Error   = [System.ConsoleColor]::Red
}

# ─────────────────────────────────────────────────────
# 📝 Логирование
function Write-Log {
    param([string]$Level, [string]$Message, [System.ConsoleColor]$Color)
    $timestamp = Get-Date -Format "HH:mm:ss"
    Write-Host "[$timestamp]" -NoNewline -ForegroundColor Cyan
    Write-Host " [$Level] " -NoNewline -ForegroundColor $Color
    Write-Host $Message
}
function Log-Info    { param([string]$M) Write-Log "INFO" $M $Colors.Info }
function Log-Success { param([string]$M) Write-Log "OK" $M $Colors.Success }
function Log-Warn    { param([string]$M) Write-Log "WARN" $M $Colors.Warn }
function Log-Error   { param([string]$M) Write-Log "ERROR" $M $Colors.Error }

# ─────────────────────────────────────────────────────
function Test-Command {
    param([string]$Cmd)
    return $null -ne (Get-Command $Cmd -ErrorAction SilentlyContinue)
}

# ─────────────────────────────────────────────────────
# 🔥 Проверка: Docker запущен и отвечает
function Test-DockerRunning {
    try {
        $null = docker info 2>&1
        return $LASTEXITCODE -eq 0
    } catch {
        return $false
    }
}

# ─────────────────────────────────────────────────────
function Get-PythonPath {
    if (Test-Command "python") {
        $cmd = Get-Command "python" -ErrorAction SilentlyContinue
        return $cmd.Source
    }
    if (Test-Command "python3") {
        $cmd = Get-Command "python3" -ErrorAction SilentlyContinue
        return $cmd.Source
    }
    return $null
}

# ─────────────────────────────────────────────────────
function Setup-Env {
    param([string]$Dir = ".")
    $envFile = Join-Path $Dir ".env"
    $exampleFile = Join-Path $Dir ".env.example"
    
    if (!(Test-Path $envFile) -and (Test-Path $exampleFile)) {
        Log-Info "Копируем $exampleFile → $envFile"
        Copy-Item $exampleFile $envFile
        Log-Warn "⚠️  Проверьте $envFile перед запуском!"
    } elseif (Test-Path $envFile) {
        Log-Success "Файл $envFile уже существует"
    } else {
        Log-Warn "⚠️  Не найдено .env.example в $Dir — пропущено"
    }
}

# ─────────────────────────────────────────────────────
function Run-Docker {
    Log-Info "🐳 Запуск в режиме Docker..."
    
    # 🔥 Проверка: установлен ли Docker
    if (!(Test-Command "docker")) {
        Log-Error "❌ Docker не установлен!"
        Log-Warn "💡 Установите Docker Desktop: https://www.docker.com/products/docker-desktop/"
        return
    }
    
    # 🔥 Проверка: запущен ли Docker Desktop
    if (!(Test-DockerRunning)) {
        Log-Error "❌ Docker Desktop не запущен!"
        Log-Warn "╔═══════════════════════════════════════════════╗"
        Log-Warn "║  1. Откройте Docker Desktop из меню Пуск      ║"
        Log-Warn "║  2. Дождитесь зелёного индикатора (🟢)        ║"
        Log-Warn "║  3. Запустите скрипт снова                    ║"
        Log-Warn "╚═══════════════════════════════════════════════╝"
        Log-Info "💡 Проверить статус: docker info"
        return
    }
    
    Log-Success "Docker готов к работе"
    
    # Проверка docker-compose.yml
    if (!(Test-Path "docker-compose.yml") -and !(Test-Path "docker-compose.yaml")) {
        Log-Error "❌ docker-compose.yml не найден!"
        return
    }
    
    Setup-Env "."
    
    Log-Info "Запускаем docker compose..."
    Log-Info "─────────────────────────────────────"
    
    docker compose up @args
    $exitCode = $LASTEXITCODE
    
    Log-Info "─────────────────────────────────────"
    if ($exitCode -ne 0) {
        Log-Error "❌ Docker compose завершился с кодом $exitCode"
    }
}

# ─────────────────────────────────────────────────────
function Run-Backend {
    Log-Info "🐍 Запуск Backend (локально)..."
    
    $pythonPath = Get-PythonPath
    if ($null -eq $pythonPath) {
        Log-Error "❌ Python не найден в PATH!"
        exit 1
    }
    Log-Info "Python: $pythonPath"
    
    Setup-Env "."
    Setup-Env "backend"
    
    if (!(Test-Path "backend\requirements.txt")) {
        Log-Error "❌ backend/requirements.txt не найден!"
        return
    }
    
    Push-Location "backend"
    
    Log-Info "Установка зависимостей..."
    & $pythonPath -m pip install -r requirements.txt
    if ($LASTEXITCODE -ne 0) {
        Log-Error "❌ Ошибка pip install (код: $LASTEXITCODE)"
        Pop-Location
        return
    }
    Log-Success "Зависимости установлены"
    
    Log-Info "Применение миграций Alembic..."
    & $pythonPath -m alembic upgrade head
    if ($LASTEXITCODE -ne 0) {
        Log-Warn "⚠️  Миграции не применены — проверь DATABASE_URL в .env"
    }
    
    Log-Success "Backend готов!"
    Log-Info "API Docs: http://localhost:8000/api/docs"
    Log-Info "Запуск сервера... (Ctrl+C для остановки)"
    Log-Info "─────────────────────────────────────"
    
    & $pythonPath main.py
    $exitCode = $LASTEXITCODE
    
    Log-Info "─────────────────────────────────────"
    if ($exitCode -ne 0) {
        Log-Error "❌ Сервер завершён с кодом $exitCode"
    } else {
        Log-Success "Сервер остановлен"
    }
    
    Pop-Location
}

# ─────────────────────────────────────────────────────
function Run-Frontend {
    Log-Info "⚡ Запуск Frontend (локально)..."
    
    Setup-Env "."
    
    $frontendDir = $null
    if (Test-Path "frontend") { $frontendDir = "frontend" }
    elseif (Test-Path "front-end") { $frontendDir = "front-end" }
    elseif (Test-Path "web") { $frontendDir = "web" }
    elseif (Test-Path "client") { $frontendDir = "client" }
    
    if ($null -eq $frontendDir) {
        Log-Error "❌ Папка frontend не найдена!"
        Log-Warn "💡 Ожидаемые названия: frontend, front-end, web, client"
        return
    }
    
    Log-Info "Найдена папка: $frontendDir"
    
    $packageJson = Join-Path $frontendDir "package.json"
    if (!(Test-Path $packageJson)) {
        Log-Error "❌ $packageJson не найден!"
        Log-Warn "💡 Убедитесь, что frontend-проект инициализирован"
        return
    }
    
    Push-Location $frontendDir
    
    $useBun = $false
    if (Test-Command "bun") {
        $useBun = $true
        Log-Info "Установка зависимостей через bun..."
        bun install
        if ($LASTEXITCODE -ne 0) {
            Log-Error "❌ Ошибка bun install"
            Pop-Location
            return
        }
    } elseif (Test-Command "npm") {
        Log-Info "Установка зависимостей через npm..."
        npm install
        if ($LASTEXITCODE -ne 0) {
            Log-Error "❌ Ошибка npm install"
            Pop-Location
            return
        }
    } else {
        Log-Error "❌ Не установлен ни bun, ни npm"
        Pop-Location
        return
    }
    
    Log-Success "Frontend готов!"
    Log-Info "Запуск dev-сервера... (Ctrl+C для остановки)"
    Log-Info "─────────────────────────────────────"
    
    if ($useBun) {
        bun dev --host 127.0.0.1
    } else {
        npm run dev -- --host 127.0.0.1
    }
    
    $exitCode = $LASTEXITCODE
    Log-Info "─────────────────────────────────────"
    if ($exitCode -ne 0) {
        Log-Error "❌ Frontend завершён с кодом $exitCode"
    }
    
    Pop-Location
}

# ─────────────────────────────────────────────────────
function Run-Clean {
    Log-Warn "Очистка контейнеров и кэшей..."
    
    if (Test-Command "docker") {
        docker compose down 2>$null | Out-Null
        docker system prune -f --volumes 2>$null | Out-Null
        Log-Success "Docker очищен"
    }
    
    $frontendDirs = @("frontend", "front-end", "web", "client")
    foreach ($dir in $frontendDirs) {
        $nodeModules = Join-Path $dir "node_modules"
        if (Test-Path $nodeModules) {
            Remove-Item -Recurse -Force $nodeModules -ErrorAction SilentlyContinue
            Log-Info "Удалено: $nodeModules"
        }
    }
    
    if (Test-Path "backend\__pycache__") {
        Remove-Item -Recurse -Force "backend\__pycache__" -ErrorAction SilentlyContinue
        Log-Info "Удалено: backend\__pycache__"
    }
    
    Log-Success "Очистка завершена"
}

# ─────────────────────────────────────────────────────
function Show-Menu {
    Write-Host ""
    Write-Host "╔════════════════════════════════════╗" -ForegroundColor Green
    Write-Host "║      Единый активатор  (Windows)   ║" -ForegroundColor Green
    Write-Host "╚════════════════════════════════════╝" -ForegroundColor Green
    Write-Host ""
    Write-Host "Выберите режим запуска:" -ForegroundColor Yellow
    Write-Host "  1) 🐳 Docker"
    Write-Host "  2) 🐍 Backend Local"
    Write-Host "  3) ⚡ Frontend Local"
    Write-Host "  4) 🧹 Очистка"
    Write-Host "  0) ❌ Выход"
    Write-Host ""
}

# ─────────────────────────────────────────────────────
function Main {
    if ($Mode -in @("docker","-d","--docker")) { Run-Docker; return }
    if ($Mode -in @("backend","-b","--backend")) { Run-Backend; return }
    if ($Mode -in @("frontend","-f","--frontend")) { Run-Frontend; return }
    if ($Mode -in @("clean","-c","--clean")) { Run-Clean; return }
    if ($Mode -in @("help","-h","--help") -or $Help) {
        Write-Host "Использование: .\activate.ps1 [режим]" -ForegroundColor Cyan
        Write-Host "Режимы: docker, backend, frontend, clean"
        return
    }
    
    $exitRequested = $false
    
    while (-not $exitRequested) {
        Show-Menu
        $choice = Read-Host "> "
        switch ($choice) {
            "1" { Run-Docker }
            "2" { Run-Backend }
            "3" { Run-Frontend }
            "4" { Run-Clean }
            "0" { 
                Log-Info "Выход. Удачи! 👋"
                $exitRequested = $true
            }
            default { Log-Warn "Неверный выбор, попробуйте снова" }
        }
    }
}

# 🚀 Запуск
Main