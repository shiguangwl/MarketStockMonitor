#!/bin/bash

# MarketStockMonitor 简化部署脚本 - 仅支持密码认证
set -e

# ===========================================
# 配置区域 - 请修改为你的服务器信息
# ===========================================
# SERVER_USER="root"                    # 服务器用户名
# SERVER_HOST="192.168.1.250"          # 服务器IP地址
# SERVER_PORT="22"                      # SSH端口
# SERVER_PASSWORD="ojbk"       # 服务器密码 - 请修改为实际密码

SERVER_USER="root"                    # 服务器用户名
SERVER_HOST="192.168.1.250"          # 服务器IP地址
SERVER_PORT="33005"                      # SSH端口
SERVER_PASSWORD="uQU+50WBkKQKkPTm"       # 服务器密码 - 请修改为实际密码

REMOTE_PATH="/root/MarketStockMonitor" # 服务器上的项目路径
TEMP_PATH="/tmp/MarketStockMonitor-$(date +%s)" # 临时文件夹路径

# Docker配置
IMAGE_NAME="market-stock-monitor"
CONTAINER_NAME="market-app"
APP_PORT="8000"

# 项目文件
PROJECT_ARCHIVE="project-$(date +%s).tar.gz"

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

print_step() {
    echo -e "${BLUE}[步骤] $1${NC}"
}

print_success() {
    echo -e "${GREEN}[成功] $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}[警告] $1${NC}"
}

print_error() {
    echo -e "${RED}[错误] $1${NC}"
}

# 检查环境
check_requirements() {
    print_step "检查部署环境..."
    
    # 检查必要文件
    if [ ! -f "Dockerfile" ]; then
        print_error "Dockerfile 不存在"
        exit 1
    fi
    
    if [ ! -f "requirements.txt" ]; then
        print_error "requirements.txt 不存在"
        exit 1
    fi
    
    # 检查sshpass
    if ! command -v sshpass &> /dev/null; then
        print_warning "sshpass 未安装，正在尝试安装..."
        if command -v brew &> /dev/null; then
            brew install sshpass
        else
            print_error "请手动安装 sshpass: brew install sshpass"
            exit 1
        fi
    fi
    
    print_success "环境检查通过"
}

# 打包项目源代码
package_project() {
    print_step "打包项目源代码..."
    
    # 创建.deployignore文件（如果不存在）
    if [ ! -f ".deployignore" ]; then
        cat > .deployignore << EOF
.git/
.gitignore
__pycache__/
*.pyc
*.pyo
*.pyd
.Python
venv/
.venv/
env/
.env/
*.log
.DS_Store
.idea/
.vscode/
*.tar.gz
*.tar
deploy.sh
deploy-*.sh
DEPLOYMENT.md
EOF
    fi
    
    # 使用兼容的tar命令，避免macOS扩展属性问题
    if [[ "$OSTYPE" == "darwin"* ]]; then
        # macOS系统，使用--no-xattrs参数
        tar --exclude-from=.deployignore --no-xattrs -czf $PROJECT_ARCHIVE .
    else
        # Linux系统
        tar --exclude-from=.deployignore -czf $PROJECT_ARCHIVE .
    fi
    
    if [ $? -eq 0 ]; then
        print_success "项目打包成功: $PROJECT_ARCHIVE"
    else
        print_error "项目打包失败"
        exit 1
    fi
}

# 测试连接
test_connection() {
    print_step "测试服务器连接..."
    
    sshpass -p "$SERVER_PASSWORD" ssh -p $SERVER_PORT -o StrictHostKeyChecking=no $SERVER_USER@$SERVER_HOST "echo '连接测试成功'" 2>/dev/null
    
    if [ $? -eq 0 ]; then
        print_success "服务器连接正常"
    else
        print_error "服务器连接失败，请检查IP、用户名和密码"
        exit 1
    fi
}

# 上传项目到服务器
upload_project() {
    print_step "上传项目到服务器临时目录..."
    
    # 创建临时目录
    sshpass -p "$SERVER_PASSWORD" ssh -p $SERVER_PORT -o StrictHostKeyChecking=no $SERVER_USER@$SERVER_HOST "mkdir -p $TEMP_PATH"
    
    # 上传项目压缩包
    sshpass -p "$SERVER_PASSWORD" scp -P $SERVER_PORT -o StrictHostKeyChecking=no $PROJECT_ARCHIVE $SERVER_USER@$SERVER_HOST:$TEMP_PATH/
    
    print_success "项目上传成功"
}

# 在服务器上构建和部署
build_and_deploy() {
    print_step "在服务器上构建和部署应用..."
    
    sshpass -p "$SERVER_PASSWORD" ssh -p $SERVER_PORT -o StrictHostKeyChecking=no $SERVER_USER@$SERVER_HOST << EOF
        cd $TEMP_PATH
        
        echo "📦 解压项目文件..."
        tar -xzf $PROJECT_ARCHIVE 2>/dev/null || tar -xzf $PROJECT_ARCHIVE
        
        echo "🔄 停止旧容器..."
        docker stop $CONTAINER_NAME 2>/dev/null || true
        docker rm $CONTAINER_NAME 2>/dev/null || true
        
        echo "🔄 删除旧镜像..."
        docker rmi $IMAGE_NAME 2>/dev/null || true
        
        echo "🔨 构建Docker镜像..."
        docker build -t $IMAGE_NAME . --no-cache
        
        if [ \$? -ne 0 ]; then
            echo "❌ 镜像构建失败"
            exit 1
        fi
        
        echo "🚀 启动新容器..."
        docker run -d \
            --name $CONTAINER_NAME \
            -p $APP_PORT:$APP_PORT \
            --restart unless-stopped \
            -v $REMOTE_PATH/logs:/app/logs \
            --network 1panel-network \
            $IMAGE_NAME
        
        if [ \$? -eq 0 ]; then
            echo "✅ 容器启动成功！"
            echo "📍 应用地址: http://$SERVER_HOST:$APP_PORT"
            
            echo "📊 容器状态:"
            docker ps | grep $CONTAINER_NAME
            
            # 创建持久化目录
            mkdir -p $REMOTE_PATH/logs
            
            echo "🧹 清理临时文件..."
            cd /
            rm -rf $TEMP_PATH
            
            echo "✅ 部署完成！"
        else
            echo "❌ 容器启动失败"
            exit 1
        fi
EOF
    
    if [ $? -eq 0 ]; then
        print_success "服务器构建和部署成功"
    else
        print_error "服务器构建和部署失败"
        exit 1
    fi
}

# 清理本地文件
cleanup() {
    print_step "清理本地临时文件..."
    if [ -f "$PROJECT_ARCHIVE" ]; then
        rm -f $PROJECT_ARCHIVE
        print_success "清理完成"
    fi
}

# 显示部署信息
show_info() {
    print_success "🎉 部署完成！"
    echo ""
    echo "📋 部署信息:"
    echo "   服务器: $SERVER_USER@$SERVER_HOST:$SERVER_PORT"
    echo "   应用地址: http://$SERVER_HOST:$APP_PORT"
    echo "   API文档: http://$SERVER_HOST:$APP_PORT/docs"
    echo ""
    echo "🔧 管理命令:"
    echo "   查看日志: sshpass -p '$SERVER_PASSWORD' ssh $SERVER_USER@$SERVER_HOST 'docker logs -f $CONTAINER_NAME'"
    echo "   重启应用: sshpass -p '$SERVER_PASSWORD' ssh $SERVER_USER@$SERVER_HOST 'docker restart $CONTAINER_NAME'"
}

# 主函数
main() {
    echo "🚀 MarketStockMonitor 简化部署脚本"
    echo "=================================="
    
    # 检查配置
    if [ "$SERVER_PASSWORD" = "your_password" ]; then
        print_error "请先修改脚本中的 SERVER_PASSWORD 为实际密码"
        exit 1
    fi
    
    # 执行部署
    check_requirements
    package_project
    test_connection
    upload_project
    build_and_deploy
    cleanup
    show_info
}

# 捕获中断信号
trap cleanup EXIT

# 执行主函数
main "$@"