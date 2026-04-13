#!/bin/bash

# SRMT BI Production Deployment Script
# Usage: ./deploy.sh [environment]

set -e

ENVIRONMENT=${1:-production}
echo "🚀 Deploying SRMT BI to $ENVIRONMENT environment..."

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check prerequisites
check_prerequisites() {
    log_info "Checking prerequisites..."
    
    if ! command -v docker &> /dev/null; then
        log_error "Docker is not installed"
        exit 1
    fi
    
    if ! command -v docker-compose &> /dev/null; then
        log_error "Docker Compose is not installed"
        exit 1
    fi
    
    if [ ! -f "srmt_data.parquet" ]; then
        log_error "Data file 'srmt_data.parquet' not found"
        exit 1
    fi
    
    log_success "Prerequisites check passed"
}

# Environment setup
setup_environment() {
    log_info "Setting up environment..."
    
    # Create necessary directories
    mkdir -p logs
    mkdir -p ssl
    mkdir -p grafana/dashboards
    mkdir -p grafana/datasources
    
    # Copy environment file
    if [ -f ".env.$ENVIRONMENT" ]; then
        cp ".env.$ENVIRONMENT" .env
        log_success "Environment file copied"
    else
        log_warning "Environment file .env.$ENVIRONMENT not found, using defaults"
    fi
    
    # Set proper permissions
    chmod +x deploy.sh
    chmod 644 requirements.txt
    
    log_success "Environment setup completed"
}

# Build and deploy
deploy() {
    log_info "Building and deploying application..."
    
    # Stop existing containers
    log_info "Stopping existing containers..."
    docker-compose down --remove-orphans || true
    
    # Build new images
    log_info "Building application image..."
    docker-compose build --no-cache
    
    # Start services
    log_info "Starting services..."
    docker-compose up -d
    
    # Wait for services to be healthy
    log_info "Waiting for services to be healthy..."
    timeout 300 bash -c 'until docker-compose ps | grep -q "healthy"; do sleep 5; done' || {
        log_error "Services failed to become healthy within 5 minutes"
        docker-compose logs
        exit 1
    }
    
    log_success "Deployment completed successfully"
}

# Health check
health_check() {
    log_info "Performing health checks..."
    
    # Check application health
    if curl -f http://localhost:5000/api/health > /dev/null 2>&1; then
        log_success "Application is healthy"
    else
        log_error "Application health check failed"
        exit 1
    fi
    
    # Check Redis
    if docker-compose exec redis redis-cli ping | grep -q PONG; then
        log_success "Redis is healthy"
    else
        log_error "Redis health check failed"
        exit 1
    fi
    
    log_success "All health checks passed"
}

# Performance test
performance_test() {
    log_info "Running basic performance test..."
    
    # Simple load test with curl
    for i in {1..5}; do
        response_time=$(curl -o /dev/null -s -w '%{time_total}' \
            -X POST http://localhost:5000/api/analyze \
            -H "Content-Type: application/json" \
            -d '{"question":"Test query"}')
        log_info "Request $i response time: ${response_time}s"
    done
    
    log_success "Performance test completed"
}

# Backup data
backup_data() {
    log_info "Creating data backup..."
    
    timestamp=$(date +"%Y%m%d_%H%M%S")
    backup_dir="backups/$timestamp"
    mkdir -p "$backup_dir"
    
    # Backup data file
    cp srmt_data.parquet "$backup_dir/"
    
    # Backup configuration
    cp -r *.yml *.py *.txt "$backup_dir/" 2>/dev/null || true
    
    # Create archive
    tar -czf "backup_$timestamp.tar.gz" "$backup_dir/"
    rm -rf "$backup_dir"
    
    log_success "Backup created: backup_$timestamp.tar.gz"
}

# Monitor logs
monitor_logs() {
    log_info "Monitoring application logs (Press Ctrl+C to stop)..."
    docker-compose logs -f srmt_bi
}

# Main execution
main() {
    echo "🏢 SRMT Business Intelligence - Production Deployment"
    echo "=================================================="
    
    case "${1:-deploy}" in
        "deploy")
            check_prerequisites
            setup_environment
            backup_data
            deploy
            health_check
            performance_test
            log_success "🎉 SRMT BI deployed successfully!"
            echo ""
            echo "📊 Access your application:"
            echo "   - Main App: http://localhost:5000"
            echo "   - Metrics:  http://localhost:8000"
            echo "   - Grafana:  http://localhost:3000 (admin/admin_change_me)"
            echo ""
            echo "📝 To monitor logs: ./deploy.sh logs"
            ;;
        "logs")
            monitor_logs
            ;;
        "health")
            health_check
            ;;
        "backup")
            backup_data
            ;;
        "stop")
            log_info "Stopping all services..."
            docker-compose down
            log_success "All services stopped"
            ;;
        "restart")
            log_info "Restarting services..."
            docker-compose restart
            health_check
            log_success "Services restarted successfully"
            ;;
        *)
            echo "Usage: ./deploy.sh [deploy|logs|health|backup|stop|restart]"
            echo ""
            echo "Commands:"
            echo "  deploy   - Full deployment (default)"
            echo "  logs     - Monitor application logs"
            echo "  health   - Run health checks"
            echo "  backup   - Create data backup"
            echo "  stop     - Stop all services"
            echo "  restart  - Restart services"
            exit 1
            ;;
    esac
}

# Run main function with all arguments
main "$@"