#!/bin/bash
# 🚀 Unified Activator Script for Linux/macOS/WSL - v5 (FINAL)
# Usage: ./activate.sh or ./activate.sh docker|backend|frontend|clean

set -e

# ─────────────────────────────────────────────────────
# 🎨 Цвета (ANSI escape codes)
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# ─────────────────────────────────────────────────────
# 📝 Логирование
log_info()    { echo -e "${CYAN}[$(date +%H:%M:%S)]${NC} ${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${CYAN}[$(date +%H:%M:%S)]${NC} ${GREEN}[OK]${NC} $1"; }
log_warn()    { echo -e "${CYAN}[$(date +%H:%M:%S)]${NC} ${YELLOW}[WARN]${NC} $1"; }
log_error()   { echo -e "${CYAN}[$(date +%H:%M:%S)]${NC} ${RED}[ERROR]${NC} $1"; }

# ─────────────────────────────────────────────────────
# 🔍 Проверка команды
check_command() {
    command -v "$1" &> /dev/null
    return $?
}

# ─────────────────────────────────────────────────────
# 🔥 Проверка: Docker запущен и отвечает
check_docker_running() {
    docker info &> /dev/null
    return $?
}

# ─────────────────────────────────────────────────────
# 🔥 Получаем путь к python
get_python_path() {
    if check_command "python3"; then
        echo "$(command -v python3)"
    elif check_command "python"; then
        echo "$(command -v python)"
    else
        echo ""
    fi
}

# ─────────────────────────────────────────────────────
# 📦 Копирование .env
setup_env() {
    local dir="${1:-.}"
    local env_file="$dir/.env"
    local example_file="$dir/.env.example"
    
    if [[ ! -f "$env_file" ]] && [[ -f "$example_file" ]]; then
        log_info "Копируем $example_file → $env_file"
        cp "$example_file" "$env_file"
        log_warn "⚠️  Проверьте $env_file перед запуском!"
    elif [[ -f "$env_file" ]]; then
        log_success "Файл $env_file уже существует"
    else
        log_warn "⚠️  Не найдено .env.example в $dir — пропущено"
    fi
}

# ─────────────────────────────────────────────────────
# 🐳 Docker режим
run_docker() {
    log_info "🐳 Запуск в режиме Docker..."
    
    # Проверка: установлен ли Docker
    if ! check_command "docker"; then
        log_error "❌ Docker не установлен!"
        log_warn "💡 Установите Docker: https://docs.docker.com/get-docker/"
        return 1
    fi
    
    # Проверка: запущен ли Docker
    if ! check_docker_running; then
        log_error "❌ Docker не запущен!"
        log_warn "╔═══════════════════════════════════════════════╗"
        log_warn "║  1. Запустите Docker Desktop/Daemon           ║"
        log_warn "║  2. Дождитесь готовности                      ║"
        log_warn "║  3. Запустите скрипт снова                    ║"
        log_warn "╚═══════════════════════════════════════════════╝"
        log_info "💡 Проверить статус: docker info"
        return 1
    fi
    
    log_success "Docker готов к работе"
    
    # Проверка docker-compose.yml
    if [[ ! -f "docker-compose.yml" ]] && [[ ! -f "docker-compose.yaml" ]] && [[ ! -f "compose.yml" ]] && [[ ! -f "compose.yaml" ]]; then
        log_error "❌ docker-compose.yml не найден!"
        return 1
    fi
    
    setup_env "."
    
    log_info "Запускаем docker compose..."
    log_info "─────────────────────────────────────"
    
    docker compose up "$@"
    local exit_code=$?
    
    log_info "─────────────────────────────────────"
    if [[ $exit_code -ne 0 ]]; then
        log_error "❌ Docker compose завершился с кодом $exit_code"
    fi
}

# ─────────────────────────────────────────────────────
# 🐍 Backend режим
run_backend() {
    log_info "🐍 Запуск Backend (локально)..."
    
    local python_path
    python_path="$(get_python_path)"
    
    if [[ -z "$python_path" ]]; then
        log_error "❌ Python не найден в PATH!"
        log_warn "💡 Установите Python 3.10+ или проверьте PATH"
        return 1
    fi
    log_info "Python: $python_path"
    
    setup_env "."
    setup_env "backend"
    
    if [[ ! -f "backend/requirements.txt" ]]; then
        log_error "❌ backend/requirements.txt не найден!"
        return 1
    fi
    
    pushd "backend" > /dev/null || return 1
    
    log_info "Установка зависимостей..."
    "$python_path" -m pip install -r requirements.txt
    if [[ $? -ne 0 ]]; then
        log_error "❌ Ошибка pip install (код: $?)"
        popd > /dev/null
        return 1
    fi
    log_success "Зависимости установлены"
    
    log_info "Применение миграций Alembic..."
    "$python_path" -m alembic upgrade head
    if [[ $? -ne 0 ]]; then
        log_warn "⚠️  Миграции не применены — проверь DATABASE_URL в .env"
    fi
    
    log_success "Backend готов!"
    log_info "API Docs: http://localhost:8000/api/docs"
    log_info "Запуск сервера... (Ctrl+C для остановки)"
    log_info "─────────────────────────────────────"
    
    "$python_path" main.py
    local exit_code=$?
    
    log_info "─────────────────────────────────────"
    if [[ $exit_code -ne 0 ]]; then
        log_error "❌ Сервер завершён с кодом $exit_code"
    else
        log_success "Сервер остановлен"
    fi
    
    popd > /dev/null
}

# ─────────────────────────────────────────────────────
# ⚡ Frontend режим
run_frontend() {
    log_info "⚡ Запуск Frontend (локально)..."
    
    setup_env "."
    
    # Поиск папки frontend
    local frontend_dir=""
    for dir in "frontend" "front-end" "web" "client"; do
        if [[ -d "$dir" ]]; then
            frontend_dir="$dir"
            break
        fi
    done
    
    if [[ -z "$frontend_dir" ]]; then
        log_error "❌ Папка frontend не найдена!"
        log_warn "💡 Ожидаемые названия: frontend, front-end, web, client"
        log_warn "💡 Текущая структура:"
        ls -d */ 2>/dev/null | while read -r d; do echo "   - $d"; done
        return 1
    fi
    
    log_info "Найдена папка: $frontend_dir"
    
    local package_json="$frontend_dir/package.json"
    if [[ ! -f "$package_json" ]]; then
        log_error "❌ $package_json не найден!"
        log_warn "💡 Убедитесь, что frontend-проект инициализирован"
        return 1
    fi
    
    pushd "$frontend_dir" > /dev/null || return 1
    
    local use_bun=false
    if check_command "bun"; then
        use_bun=true
        log_info "Установка зависимостей через bun..."
        bun install
        if [[ $? -ne 0 ]]; then
            log_error "❌ Ошибка bun install"
            popd > /dev/null
            return 1
        fi
    elif check_command "npm"; then
        log_info "Установка зависимостей через npm..."
        npm install
        if [[ $? -ne 0 ]]; then
            log_error "❌ Ошибка npm install"
            popd > /dev/null
            return 1
        fi
    else
        log_error "❌ Не установлен ни bun, ни npm"
        log_warn "💡 Установите: https://bun.sh или https://nodejs.org"
        popd > /dev/null
        return 1
    fi
    
    log_success "Frontend готов!"
    log_info "Запуск dev-сервера... (Ctrl+C для остановки)"
    log_info "─────────────────────────────────────"
    
    if [[ "$use_bun" == true ]]; then
        bun dev --host 127.0.0.1
    else
        npm run dev -- --host 127.0.0.1
    fi
    
    local exit_code=$?
    log_info "─────────────────────────────────────"
    if [[ $exit_code -ne 0 ]]; then
        log_error "❌ Frontend завершён с кодом $exit_code"
    fi
    
    popd > /dev/null
}

# ─────────────────────────────────────────────────────
# 🧹 Очистка
run_clean() {
    log_warn "Очистка контейнеров и кэшей..."
    
    if check_command "docker"; then
        docker compose down &> /dev/null || true
        docker system prune -f --volumes &> /dev/null || true
        log_success "Docker очищен"
    fi
    
    # Очистка frontend
    for dir in "frontend" "front-end" "web" "client"; do
        if [[ -d "$dir/node_modules" ]]; then
            rm -rf "$dir/node_modules"
            log_info "Удалено: $dir/node_modules"
        fi
    done
    
    # Очистка backend
    if [[ -d "backend/__pycache__" ]]; then
        rm -rf "backend/__pycache__"
        log_info "Удалено: backend/__pycache__"
    fi
    if [[ -d "backend/.pytest_cache" ]]; then
        rm -rf "backend/.pytest_cache"
        log_info "Удалено: backend/.pytest_cache"
    fi
    if [[ -f "backend/.mypy_cache" ]]; then
        rm -rf "backend/.mypy_cache"
        log_info "Удалено: backend/.mypy_cache"
    fi
    
    log_success "Очистка завершена"
}

# ─────────────────────────────────────────────────────
# 📋 Меню
show_menu() {
    echo -e ""
    echo -e "${GREEN}╔════════════════════════════════════╗${NC}"
    echo -e "${GREEN}║      Единый активатор  (Linux)     ║${NC}"
    echo -e "${GREEN}╚════════════════════════════════════╝${NC}"
    echo -e ""
    echo -e "${YELLOW}Выберите режим запуска:${NC}"
    echo "  1) 🐳 Docker"
    echo "  2) 🐍 Backend Local"
    echo "  3) ⚡ Frontend Local"
    echo "  4) 🧹 Очистка"
    echo "  0) ❌ Выход"
    echo ""
}

# ─────────────────────────────────────────────────────
# 🔽 Точка входа
main() {
    # Обработка аргументов командной строки
    case "$1" in
        docker|-d|--docker)
            run_docker "${@:2}"
            return 0
            ;;
        backend|-b|--backend)
            run_backend "${@:2}"
            return 0
            ;;
        frontend|-f|--frontend)
            run_frontend "${@:2}"
            return 0
            ;;
        clean|-c|--clean)
            run_clean "${@:2}"
            return 0
            ;;
        help|-h|--help)
            echo -e "${CYAN}Использование: ./activate.sh [режим]${NC}"
            echo "Режимы: docker, backend, frontend, clean"
            echo ""
            echo "Примеры:"
            echo "  ./activate.sh          # интерактивное меню"
            echo "  ./activate.sh docker   # запустить Docker"
            echo "  ./activate.sh backend  # запустить Backend"
            return 0
            ;;
    esac
    
    # Интерактивный режим
    local exit_requested=false
    
    while [[ "$exit_requested" == false ]]; do
        show_menu
        read -p "> " choice
        case "$choice" in
            1) run_docker ;;
            2) run_backend ;;
            3) run_frontend ;;
            4) run_clean ;;
            0)
                log_info "Выход. Удачи! 👋"
                exit_requested=true
                ;;
            *)
                log_warn "Неверный выбор, попробуйте снова"
                ;;
        esac
    done
    
    exit 0
}

# 🚀 Запуск
main "$@"