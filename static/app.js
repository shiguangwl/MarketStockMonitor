class MarketMonitor {
    constructor() {
        this.eventSource = null;
        this.isConnected = false;
        this.isPaused = false;
        this.klineChart = null;
        this.marketData = new Map();
        this.klineData = new Map();
        this.maxStreamItems = 50;
        
        this.init();
    }

    async init() {
        this.setupEventListeners();
        await this.loadInitialData();
        this.connectToStream();
        this.initializeChart();
        this.startMarketTimeUpdate();
    }

    setupEventListeners() {
        // 刷新按钮
        document.getElementById('refreshBtn').addEventListener('click', () => {
            this.refreshData();
        });

        // 测试按钮
        document.getElementById('testBtn').addEventListener('click', () => {
            this.testConnection();
        });

        // 过滤器按钮
        this.setupFilterButtons();

        // 流控制按钮
        document.getElementById('pauseStream').addEventListener('click', () => {
            this.toggleStream();
        });

        document.getElementById('clearStream').addEventListener('click', () => {
            this.clearStream();
        });

        // 图表控制
        document.getElementById('chartMarket').addEventListener('change', () => {
            this.updateChart();
        });

        document.getElementById('chartTimeframe').addEventListener('change', () => {
            this.updateChart();
        });

        // 关闭提示框
        document.getElementById('closeError').addEventListener('click', () => {
            this.hideToast('error');
        });

        document.getElementById('closeSuccess').addEventListener('click', () => {
            this.hideToast('success');
        });
    }

    setupFilterButtons() {
        // 数据源过滤器
        document.getElementById('sourceFilters').addEventListener('click', (e) => {
            if (e.target.classList.contains('filter-btn')) {
                this.toggleFilter(e.target, 'source');
            }
        });

        // 市场过滤器
        document.getElementById('marketFilters').addEventListener('click', (e) => {
            if (e.target.classList.contains('filter-btn')) {
                this.toggleFilter(e.target, 'market');
            }
        });

        // 数据类型过滤器
        document.getElementById('dataTypeFilters').addEventListener('click', (e) => {
            if (e.target.classList.contains('filter-btn')) {
                this.toggleFilter(e.target, 'dataType');
            }
        });
    }

    toggleFilter(button, type) {
        const container = button.parentElement;
        const buttons = container.querySelectorAll('.filter-btn');
        
        // 如果点击的是"全部"按钮
        if (button.dataset[type] === 'all') {
            buttons.forEach(btn => btn.classList.remove('active'));
            button.classList.add('active');
        } else {
            // 取消"全部"按钮的激活状态
            const allButton = container.querySelector('[data-' + type + '="all"]');
            if (allButton) {
                allButton.classList.remove('active');
            }
            
            // 切换当前按钮状态
            button.classList.toggle('active');
            
            // 如果没有任何按钮被激活，激活"全部"按钮
            const activeButtons = container.querySelectorAll('.filter-btn.active');
            if (activeButtons.length === 0 && allButton) {
                allButton.classList.add('active');
            }
        }

        // 重新连接流以应用过滤器
        this.reconnectStream();
    }

    async loadInitialData() {
        this.showLoading();
        
        try {
            // 加载数据源列表
            const sources = await this.fetchAPI('/api/sources');
            this.updateSourceFilters(sources);
            this.updateSourcesStatus(sources);

            // 加载市场数据
            await this.loadMarketData(sources);
            
            this.showToast('success', '数据加载完成');
        } catch (error) {
            console.error('加载初始数据失败:', error);
            this.showToast('error', '数据加载失败: ' + error.message);
        } finally {
            this.hideLoading();
        }
    }

    async loadMarketData(sources) {
        for (const source of sources) {
            for (const market of source.supported_markets) {
                try {
                    // 获取实时数据
                    const realtimeData = await this.fetchAPI(
                        `/api/sources/${source.source_id}/latest/${market}/realtime`
                    );
                    this.updateMarketCard(realtimeData);

                    // 获取市场状态
                    const statusData = await this.fetchAPI(
                        `/api/sources/${source.source_id}/market-status/${market}`
                    );
                    this.updateMarketStatus(market, statusData);

                } catch (error) {
                    console.warn(`获取 ${source.source_id} ${market} 数据失败:`, error);
                }
            }
        }
    }

    updateSourceFilters(sources) {
        const container = document.getElementById('sourceFilters');
        
        // 清除现有的非"全部"按钮
        const existingButtons = container.querySelectorAll('.filter-btn:not([data-source="all"])');
        existingButtons.forEach(btn => btn.remove());

        // 添加数据源按钮
        sources.forEach(source => {
            const button = document.createElement('button');
            button.className = 'filter-btn';
            button.dataset.source = source.source_id;
            button.textContent = source.source_name;
            container.appendChild(button);
        });
    }

    updateSourcesStatus(sources) {
        const container = document.getElementById('sourcesGrid');
        container.innerHTML = '';

        sources.forEach(source => {
            const card = document.createElement('div');
            card.className = 'source-card';
            card.innerHTML = `
                <div class="source-name">${source.source_name}</div>
                <div class="source-status active">活跃</div>
                <div class="source-markets">支持市场: ${source.supported_markets.join(', ')}</div>
            `;
            container.appendChild(card);
        });
    }

    updateMarketCard(data) {
        const container = document.getElementById('marketCards');
        const cardId = `market-${data.market}`;
        let card = document.getElementById(cardId);

        if (!card) {
            card = document.createElement('div');
            card.id = cardId;
            card.className = 'market-card';
            container.appendChild(card);
        }

        const marketData = data.data;
        const change = marketData.change || 0;
        const changePercent = marketData.change_percent || 0;
        const changeClass = change >= 0 ? 'positive' : 'negative';
        const changeSymbol = change >= 0 ? '+' : '';

        card.innerHTML = `
            <div class="market-card-content">
                <div class="market-name">${marketData.name || data.market}</div>
                <div class="market-price">${this.formatPrice(marketData.price)}</div>
                <div class="market-change ${changeClass}">
                    ${changeSymbol}${this.formatPrice(change)} (${changeSymbol}${changePercent.toFixed(2)}%)
                </div>
                <div class="market-volume">成交量: ${this.formatVolume(marketData.volume)}</div>
            </div>
            <div class="market-status" id="status-${data.market}">未知</div>
        `;

        // 存储市场数据
        this.marketData.set(data.market, marketData);
    }

    updateMarketStatus(market, statusData) {
        const statusElement = document.getElementById(`status-${market}`);
        if (statusElement) {
            const isOpen = statusData.status.is_open;
            statusElement.textContent = statusData.status.status_text;
            statusElement.className = `market-status ${isOpen ? 'open' : 'closed'}`;
        }
    }

    connectToStream() {
        if (this.eventSource) {
            this.eventSource.close();
        }

        const filters = this.getActiveFilters();
        const params = new URLSearchParams();
        
        if (filters.sources.length > 0 && !filters.sources.includes('all')) {
            params.append('sources', filters.sources.join(','));
        }
        if (filters.markets.length > 0 && !filters.markets.includes('all')) {
            params.append('markets', filters.markets.join(','));
        }
        if (filters.dataTypes.length > 0 && !filters.dataTypes.includes('all')) {
            params.append('data_types', filters.dataTypes.join(','));
        }

        const url = `/api/sources/stream${params.toString() ? '?' + params.toString() : ''}`;
        
        this.eventSource = new EventSource(url);
        
        this.eventSource.onopen = () => {
            this.isConnected = true;
            this.updateConnectionStatus();
            console.log('SSE连接已建立');
        };

        this.eventSource.onmessage = (event) => {
            console.log('收到SSE消息:', event);
            this.handleStreamData(event);
        };

        this.eventSource.addEventListener('connected', (event) => {
            const data = JSON.parse(event.data);
            console.log('连接确认:', data);
            this.showToast('success', '实时数据流已连接');
        });

        this.eventSource.addEventListener('market_data', (event) => {
            if (!this.isPaused) {
                const data = JSON.parse(event.data);
                console.log('收到市场数据:', data);
                this.handleMarketData(data);
            }
        });

        this.eventSource.addEventListener('heartbeat', (event) => {
            const data = JSON.parse(event.data);
            this.updateLastUpdate();
        });

        this.eventSource.addEventListener('error', (event) => {
            const data = JSON.parse(event.data);
            console.error('SSE错误:', data);
            this.showToast('error', '数据流错误: ' + data.message);
        });

        this.eventSource.onerror = (error) => {
            console.error('SSE连接错误:', error);
            this.isConnected = false;
            this.updateConnectionStatus();
            
            // 尝试重连
            setTimeout(() => {
                if (!this.isConnected) {
                    console.log('尝试重新连接...');
                    this.connectToStream();
                }
            }, 5000);
        };
    }

    reconnectStream() {
        if (this.eventSource) {
            this.eventSource.close();
        }
        setTimeout(() => {
            this.connectToStream();
        }, 1000);
    }

    getActiveFilters() {
        const sources = Array.from(document.querySelectorAll('#sourceFilters .filter-btn.active'))
            .map(btn => btn.dataset.source);
        const markets = Array.from(document.querySelectorAll('#marketFilters .filter-btn.active'))
            .map(btn => btn.dataset.market);
        const dataTypes = Array.from(document.querySelectorAll('#dataTypeFilters .filter-btn.active'))
            .map(btn => btn.dataset.type);

        return { sources, markets, dataTypes };
    }

    handleMarketData(data) {
        console.log('处理市场数据:', data);
        
        // 转换数据格式以匹配现有的处理逻辑
        const formattedData = {
            source_id: data.source,
            market: data.symbol,
            data_type: data.type,
            data: {
                name: data.symbol,
                time: data.timestamp,
                price: data.price,
                volume: data.volume,
                open: data.open_price,
                high: data.high_price,
                low: data.low_price,
                close: data.close_price,
                change: data.change,
                change_percent: data.change_percent
            }
        };
        
        // 更新市场卡片
        this.updateMarketCard(formattedData);
        
        // 添加到数据流
        this.addToDataStream(formattedData);
        
        // 更新K线图
        if (data.type === 'kline1m' || data.type === 'realtime') {
            this.updateKlineData(formattedData);
        }
    }

    addToDataStream(data) {
        const container = document.getElementById('dataStream');
        const item = document.createElement('div');
        item.className = 'data-item';
        
        const marketData = data.data;
        const time = new Date(marketData.time || Date.now());
        
        item.innerHTML = `
            <div class="data-item-info">
                <div class="data-item-market">${marketData.name || data.market}</div>
                <div class="data-item-source">${data.source_id} - ${data.data_type}</div>
            </div>
            <div class="data-item-value">
                <div class="data-item-price">${this.formatPrice(marketData.price)}</div>
                <div class="data-item-time">${time.toLocaleTimeString()}</div>
            </div>
        `;
        
        // 插入到顶部
        container.insertBefore(item, container.firstChild);
        
        // 限制显示数量
        const items = container.querySelectorAll('.data-item');
        if (items.length > this.maxStreamItems) {
            items[items.length - 1].remove();
        }
        
        // 自动滚动到顶部
        container.scrollTop = 0;
    }

    initializeChart() {
        const ctx = document.getElementById('klineChart').getContext('2d');
        
        // 使用普通的线图，因为candlestick可能不可用
        this.klineChart = new Chart(ctx, {
            type: 'line',
            data: {
                labels: [],
                datasets: [{
                    label: '价格',
                    data: [],
                    borderColor: '#4299e1',
                    backgroundColor: 'rgba(66, 153, 225, 0.1)',
                    fill: true,
                    tension: 0.1
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    x: {
                        title: {
                            display: true,
                            text: '时间'
                        }
                    },
                    y: {
                        title: {
                            display: true,
                            text: '价格'
                        }
                    }
                },
                plugins: {
                    legend: {
                        display: true,
                        position: 'top'
                    },
                    tooltip: {
                        mode: 'index',
                        intersect: false
                    }
                },
                interaction: {
                    mode: 'nearest',
                    axis: 'x',
                    intersect: false
                }
            }
        });
    }

    updateChart() {
        const market = document.getElementById('chartMarket').value;
        const timeframe = document.getElementById('chartTimeframe').value;
        
        // 获取市场数据
        const marketDataArray = this.klineData.get(market) || [];
        
        // 准备图表数据
        const labels = marketDataArray.map(item => item.time);
        const prices = marketDataArray.map(item => item.price);
        
        this.klineChart.data.labels = labels;
        this.klineChart.data.datasets[0].data = prices;
        this.klineChart.data.datasets[0].label = `${market} 价格走势 (${timeframe})`;
        this.klineChart.update();
    }

    updateKlineData(data) {
        const market = data.market;
        const marketData = data.data;
        
        if (!this.klineData.has(market)) {
            this.klineData.set(market, []);
        }
        
        const klineArray = this.klineData.get(market);
        const time = new Date(marketData.time || Date.now()).toLocaleTimeString();
        
        // 构造数据点
        const dataPoint = {
            time: time,
            price: marketData.price || 0,
            volume: marketData.volume || 0
        };
        
        klineArray.push(dataPoint);
        
        // 限制数据点数量
        if (klineArray.length > 50) {
            klineArray.shift();
        }
        
        // 如果当前图表显示的是这个市场，更新图表
        const currentMarket = document.getElementById('chartMarket').value;
        if (currentMarket === market) {
            this.updateChart();
        }
        
        console.log(`更新 ${market} 图表数据:`, dataPoint);
    }

    toggleStream() {
        const button = document.getElementById('pauseStream');
        
        if (this.isPaused) {
            this.isPaused = false;
            button.textContent = '暂停';
            button.className = 'btn btn-secondary';
        } else {
            this.isPaused = true;
            button.textContent = '继续';
            button.className = 'btn btn-primary';
        }
    }

    clearStream() {
        const container = document.getElementById('dataStream');
        container.innerHTML = '';
    }

    async refreshData() {
        this.showLoading();
        try {
            await this.loadInitialData();
            this.showToast('success', '数据刷新完成');
        } catch (error) {
            this.showToast('error', '数据刷新失败: ' + error.message);
        } finally {
            this.hideLoading();
        }
    }

    async testConnection() {
        console.log('测试连接状态...');
        
        try {
            // 测试API连接
            const response = await this.fetchAPI('/health');
            console.log('健康检查响应:', response);
            
            // 测试SSE连接状态
            console.log('SSE连接状态:', this.isConnected);
            console.log('当前连接数:', Object.keys(this.connections || {}).length);
            
            // 获取SSE统计信息
            const stats = await this.fetchAPI('/api/sources/stream/stats');
            console.log('SSE统计信息:', stats);
            
            this.showToast('success', `连接测试完成 - API: 正常, SSE: ${this.isConnected ? '已连接' : '未连接'}`);
            
        } catch (error) {
            console.error('连接测试失败:', error);
            this.showToast('error', '连接测试失败: ' + error.message);
        }
    }

    startMarketTimeUpdate() {
        const updateTime = () => {
            const now = new Date();
            const timeString = now.toLocaleString('zh-CN', {
                year: 'numeric',
                month: '2-digit',
                day: '2-digit',
                hour: '2-digit',
                minute: '2-digit',
                second: '2-digit'
            });
            
            const timeElement = document.getElementById('marketTime');
            if (timeElement) {
                timeElement.textContent = `当前时间: ${timeString}`;
            }
        };
        
        updateTime();
        setInterval(updateTime, 1000);
    }

    updateConnectionStatus() {
        const statusElement = document.getElementById('connectionStatus');
        const lastUpdateElement = document.getElementById('lastUpdate');
        
        if (this.isConnected) {
            statusElement.textContent = '在线';
            statusElement.className = 'status-indicator online';
            this.updateLastUpdate();
        } else {
            statusElement.textContent = '离线';
            statusElement.className = 'status-indicator offline';
            lastUpdateElement.textContent = '连接断开';
        }
    }

    updateLastUpdate() {
        const lastUpdateElement = document.getElementById('lastUpdate');
        const now = new Date();
        lastUpdateElement.textContent = `最后更新: ${now.toLocaleTimeString()}`;
    }

    async fetchAPI(endpoint) {
        const response = await fetch(endpoint);
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        return await response.json();
    }

    formatPrice(price) {
        if (price == null) return 'N/A';
        return parseFloat(price).toLocaleString('zh-CN', {
            minimumFractionDigits: 2,
            maximumFractionDigits: 2
        });
    }

    formatVolume(volume) {
        if (volume == null) return 'N/A';
        
        if (volume >= 1e8) {
            return (volume / 1e8).toFixed(2) + '亿';
        } else if (volume >= 1e4) {
            return (volume / 1e4).toFixed(2) + '万';
        } else {
            return volume.toLocaleString('zh-CN');
        }
    }

    showLoading() {
        document.getElementById('loadingIndicator').style.display = 'flex';
    }

    hideLoading() {
        document.getElementById('loadingIndicator').style.display = 'none';
    }

    showToast(type, message) {
        const toastId = type === 'error' ? 'errorToast' : 'successToast';
        const messageId = type === 'error' ? 'errorMessage' : 'successMessage';
        
        const toast = document.getElementById(toastId);
        const messageElement = document.getElementById(messageId);
        
        messageElement.textContent = message;
        toast.style.display = 'flex';
        
        // 自动隐藏
        setTimeout(() => {
            this.hideToast(type);
        }, 5000);
    }

    hideToast(type) {
        const toastId = type === 'error' ? 'errorToast' : 'successToast';
        document.getElementById(toastId).style.display = 'none';
    }
}

// 页面加载完成后初始化
document.addEventListener('DOMContentLoaded', () => {
    new MarketMonitor();
});
