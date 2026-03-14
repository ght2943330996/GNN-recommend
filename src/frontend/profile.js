const { createApp } = Vue;

const app = createApp({
    data() {
        return {
            // API 配置
            apiBase: 'http://localhost:5000/api',
            
            // 用户状态
            currentUser: null,
            showUserMenu: false,
            
            // 加载状态
            loading: true,
            
            // 个人资料数据
            profileData: {
                user_id: null,
                username: '',
                created_at: '',
                stats: {
                    rating_count: 0,
                    comment_count: 0,
                    favorite_count: 0
                }
            },
            
            // 用户画像分析数据
            analysisData: {
                category_distribution: {},
                rating_distribution: {1: 0, 2: 0, 3: 0, 4: 0, 5: 0},
                favorite_categories: [],
                personality_tags: [],
                travel_style: '新手探索者'
            },
            
            // Tab 状态
            activeTab: 'ratings',
            
            // 评分历史
            ratingHistory: [],
            ratingFilter: '',
            categoryFilter: '',
            categories: [],
            
            // 用户评论
            userComments: [],
            
            // 用户收藏
            userFavorites: [],

            // 景点详情模态框
            showDetailModal: false,
            itemDetail: null,
            itemComments: [],
            similarItems: [],
            newComment: '',
            userRatings: {},
            favoriteIds: new Set(),
            
            // 图表实例
            categoryChart: null,
            ratingChart: null,
            
            // 景点图片映射
            categoryImages: {
                '交通枢纽': 'https://images.unsplash.com/photo-1436491865332-7a61a109cc05?w=800&q=80',
                '公园景区': 'https://images.unsplash.com/photo-1441974231531-c6227db76b6e?w=800&q=80',
                '动物园': 'https://images.unsplash.com/photo-1564349683136-77e08dba1ef7?w=800&q=80',
                '博物馆': 'https://images.unsplash.com/photo-1554907984-15263bfd63bd?w=800&q=80',
                '历史遗迹': 'https://images.unsplash.com/photo-1513635269975-59663e0ac1ad?w=800&q=80',
                '商业区': 'https://images.unsplash.com/photo-1441986300917-64674bd600d8?w=800&q=80',
                '娱乐场所': 'https://images.unsplash.com/photo-1514525253161-7a46d19cd819?w=800&q=80',
                '宗教场所': 'https://images.unsplash.com/photo-1548013146-72479768bada?w=800&q=80',
                '户外活动': 'https://images.unsplash.com/photo-1501555088652-021faa106b9b?w=800&q=80',
                '文化艺术': 'https://images.unsplash.com/photo-1499781350541-7783f6c6a0c8?w=800&q=80',
                '海滩': 'https://images.unsplash.com/photo-1507525428034-b723cf961d3e?w=800&q=80',
                '美食': 'https://images.unsplash.com/photo-1504674900247-0877df9cc836?w=800&q=80',
                '购物': 'https://images.unsplash.com/photo-1441986300917-64674bd600d8?w=800&q=80',
                '酒店': 'https://images.unsplash.com/photo-1566073771259-6a8506099945?w=800&q=80',
                '默认': 'https://images.unsplash.com/photo-1488646953014-85cb44e25828?w=800&q=80'
            }
        };
    },
    
    async mounted() {
        // 检查本地存储
        const savedUser = localStorage.getItem('currentUser');
        if (savedUser) {
            this.currentUser = JSON.parse(savedUser);
            await this.loadAllData();
        } else {
            this.loading = false;
        }
        
        // 点击外部关闭下拉菜单
        document.addEventListener('click', this.handleClickOutside);
        
        // 加载类别列表
        await this.loadCategories();
    },
    
    beforeUnmount() {
        document.removeEventListener('click', this.handleClickOutside);
        
        // 销毁图表
        if (this.categoryChart) {
            this.categoryChart.destroy();
        }
        if (this.ratingChart) {
            this.ratingChart.destroy();
        }
    },
    
    methods: {
        // ==================== 工具方法 ====================
        
        handleClickOutside(event) {
            if (!event.target.closest('.nav-user')) {
                this.showUserMenu = false;
            }
        },
        
        toggleUserMenu() {
            this.showUserMenu = !this.showUserMenu;
        },
        
        formatDate(dateString) {
            const date = new Date(dateString);
            return date.toLocaleDateString('zh-CN', {
                year: 'numeric',
                month: 'long',
                day: 'numeric'
            });
        },
        
        getPlaceImage(category) {
            return this.categoryImages[category] || this.categoryImages['默认'];
        },
        
        logout() {
            this.currentUser = null;
            localStorage.removeItem('currentUser');
            window.location.href = 'index.html';
        },
        
        // ==================== 数据加载 ====================
        
        async loadAllData() {
            this.loading = true;
            try {
                await Promise.all([
                    this.loadProfile(),
                    this.loadAnalysis(),
                    this.loadRatingHistory(),
                    this.loadComments(),
                    this.loadFavorites()
                ]);
            } catch (error) {
                console.error('加载数据失败:', error);
                alert('加载数据失败，请刷新页面重试');
            } finally {
                this.loading = false;
                
                // 等待 loading 状态更新和 DOM 渲染完成后再渲染图表
                this.$nextTick(() => {
                    // 再等一个 tick 确保 CSS 动画完成
                    setTimeout(() => {
                        this.renderCharts();
                    }, 100);
                });
            }
        },
        
        async loadProfile() {
            try {
                const response = await axios.get(
                    `${this.apiBase}/user/${this.currentUser.user_id}/profile`
                );
                this.profileData = response.data;
            } catch (error) {
                console.error('加载个人资料失败:', error);
            }
        },
        
        async loadAnalysis() {
            try {
                const response = await axios.get(
                    `${this.apiBase}/user/${this.currentUser.user_id}/analysis`
                );
                this.analysisData = response.data;
            } catch (error) {
                console.error('加载用户画像失败:', error);
            }
        },
        
        async loadCategories() {
            try {
                const response = await axios.get(`${this.apiBase}/categories`);
                this.categories = response.data.categories;
            } catch (error) {
                console.error('加载类别失败:', error);
            }
        },
        
        async loadRatingHistory() {
            try {
                const params = {
                    per_page: 100
                };
                
                if (this.ratingFilter) {
                    params.rating = this.ratingFilter;
                }
                if (this.categoryFilter) {
                    params.category = this.categoryFilter;
                }
                
                const response = await axios.get(
                    `${this.apiBase}/rating/user/${this.currentUser.user_id}/history`,
                    { params }
                );
                this.ratingHistory = response.data.ratings;
            } catch (error) {
                console.error('加载评分历史失败:', error);
            }
        },
        
        async loadComments() {
            try {
                const response = await axios.get(
                    `${this.apiBase}/comment/user/${this.currentUser.user_id}`
                );
                this.userComments = response.data.comments;
            } catch (error) {
                console.error('加载评论失败:', error);
            }
        },
        
        async loadFavorites() {
            try {
                const response = await axios.get(
                    `${this.apiBase}/favorite/user/${this.currentUser.user_id}`
                );
                this.userFavorites = response.data.favorites;
                this.favoriteIds = new Set(this.userFavorites.map(item => item.item_id));
            } catch (error) {
                console.error('加载收藏失败:', error);
            }
        },
        
        // ==================== Tab 切换 ====================
        
        switchTab(tab) {
            this.activeTab = tab;
        },
        
        // ==================== 图表渲染 ====================
        
        renderCharts() {
            this.renderCategoryChart();
            this.renderRatingChart();
        },
        
        renderCategoryChart() {
            const ctx = document.getElementById('categoryChart');
            if (!ctx) return;
            
            // 销毁旧图表
            if (this.categoryChart) {
                this.categoryChart.destroy();
            }
            
            // 准备数据
            const categories = this.analysisData.favorite_categories.slice(0, 5);
            const labels = categories.map(c => c.category);
            const data = categories.map(c => c.count);
            
            // 如果没有数据，显示空状态
            if (data.length === 0) {
                return;
            }
            
            // 创建图表
            this.categoryChart = new Chart(ctx, {
                type: 'doughnut',
                data: {
                    labels: labels,
                    datasets: [{
                        data: data,
                        backgroundColor: [
                            'rgba(255, 90, 95, 0.8)',
                            'rgba(0, 166, 153, 0.8)',
                            'rgba(255, 180, 0, 0.8)',
                            'rgba(102, 126, 234, 0.8)',
                            'rgba(118, 75, 162, 0.8)'
                        ],
                        borderColor: '#fff',
                        borderWidth: 3
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: {
                            position: 'bottom',
                            labels: {
                                padding: 15,
                                font: {
                                    size: 12,
                                    family: "'Poppins', sans-serif"
                                }
                            }
                        },
                        tooltip: {
                            backgroundColor: 'rgba(0, 0, 0, 0.8)',
                            padding: 12,
                            titleFont: {
                                size: 14,
                                family: "'Poppins', sans-serif"
                            },
                            bodyFont: {
                                size: 13,
                                family: "'Poppins', sans-serif"
                            },
                            callbacks: {
                                label: function(context) {
                                    const label = context.label || '';
                                    const value = context.parsed || 0;
                                    const total = context.dataset.data.reduce((a, b) => a + b, 0);
                                    const percentage = ((value / total) * 100).toFixed(1);
                                    return `${label}: ${value} (${percentage}%)`;
                                }
                            }
                        }
                    }
                }
            });
        },
        
        renderRatingChart() {
            const ctx = document.getElementById('ratingChart');
            if (!ctx) return;
            
            // 销毁旧图表
            if (this.ratingChart) {
                this.ratingChart.destroy();
            }
            
            // 准备数据
            const distribution = this.analysisData.rating_distribution;
            const labels = ['1星', '2星', '3星', '4星', '5星'];
            const data = [
                distribution[1] || 0,
                distribution[2] || 0,
                distribution[3] || 0,
                distribution[4] || 0,
                distribution[5] || 0
            ];
            
            // 创建图表
            this.ratingChart = new Chart(ctx, {
                type: 'bar',
                data: {
                    labels: labels,
                    datasets: [{
                        label: '评分次数',
                        data: data,
                        backgroundColor: [
                            'rgba(255, 90, 95, 0.8)',
                            'rgba(255, 140, 0, 0.8)',
                            'rgba(255, 180, 0, 0.8)',
                            'rgba(0, 166, 153, 0.8)',
                            'rgba(102, 126, 234, 0.8)'
                        ],
                        borderColor: [
                            'rgba(255, 90, 95, 1)',
                            'rgba(255, 140, 0, 1)',
                            'rgba(255, 180, 0, 1)',
                            'rgba(0, 166, 153, 1)',
                            'rgba(102, 126, 234, 1)'
                        ],
                        borderWidth: 2,
                        borderRadius: 8
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: {
                            display: false
                        },
                        tooltip: {
                            backgroundColor: 'rgba(0, 0, 0, 0.8)',
                            padding: 12,
                            titleFont: {
                                size: 14,
                                family: "'Poppins', sans-serif"
                            },
                            bodyFont: {
                                size: 13,
                                family: "'Poppins', sans-serif"
                            }
                        }
                    },
                    scales: {
                        y: {
                            beginAtZero: true,
                            ticks: {
                                stepSize: 1,
                                font: {
                                    family: "'Poppins', sans-serif"
                                }
                            },
                            grid: {
                                color: 'rgba(0, 0, 0, 0.05)'
                            }
                        },
                        x: {
                            ticks: {
                                font: {
                                    family: "'Poppins', sans-serif"
                                }
                            },
                            grid: {
                                display: false
                            }
                        }
                    }
                }
            });
        },
        
        // ==================== 评论操作 ====================
        
        async deleteComment(commentId) {
            if (!confirm('确定要删除这条评论吗？')) {
                return;
            }
            
            try {
                await axios.delete(`${this.apiBase}/comment/${commentId}`);
                
                // 从列表中移除
                this.userComments = this.userComments.filter(c => c.id !== commentId);
                
                // 更新统计
                this.profileData.stats.comment_count--;
                
                alert('评论已删除');
            } catch (error) {
                console.error('删除评论失败:', error);
                alert('删除评论失败，请重试');
            }
        },

        // ==================== 收藏功能 ====================

        isFavorite(itemId) {
            return this.favoriteIds.has(itemId);
        },

        async toggleFavorite(itemId) {
            if (!this.currentUser) {
                return;
            }
            
            const isFav = this.favoriteIds.has(itemId);
            
            try {
                if (isFav) {
                    // 取消收藏
                    await axios.post(`${this.apiBase}/favorite/remove`, {
                        user_id: this.currentUser.user_id,
                        item_id: itemId
                    });
                    
                    this.favoriteIds.delete(itemId);
                } else {
                    // 添加收藏
                    await axios.post(`${this.apiBase}/favorite/add`, {
                        user_id: this.currentUser.user_id,
                        item_id: itemId
                    });
                    
                    this.favoriteIds.add(itemId);
                }
                
                // 重新加载收藏列表
                await this.loadFavorites();
            } catch (error) {
                console.error('收藏操作失败:', error);
                alert(error.response?.data?.error || '操作失败，请重试');
            }
        },

        // ==================== 景点详情 ====================

        async viewItemDetail(itemId) {
            this.showDetailModal = true;
            this.itemDetail = null;
            this.itemComments = [];
            this.similarItems = [];
            this.newComment = '';
            
            await Promise.all([
                this.loadItemDetail(itemId),
                this.loadItemComments(itemId),
                this.loadSimilarItems(itemId),
                this.loadUserRatings()
            ]);
        },

        async loadItemDetail(itemId) {
            try {
                const response = await axios.get(`${this.apiBase}/item/${itemId}/detail`);
                this.itemDetail = response.data;
            } catch (error) {
                console.error('加载景点详情失败:', error);
            }
        },

        async loadItemComments(itemId) {
            try {
                const response = await axios.get(`${this.apiBase}/comment/item/${itemId}`);
                this.itemComments = response.data.comments;
            } catch (error) {
                console.error('加载评论失败:', error);
            }
        },

        async loadSimilarItems(itemId) {
            try {
                const response = await axios.get(`${this.apiBase}/item/${itemId}/similar?top_k=6`);
                this.similarItems = response.data.similar_items;
            } catch (error) {
                console.error('加载相似景点失败:', error);
            }
        },

        async loadUserRatings() {
            if (!this.currentUser) return;
            
            try {
                const response = await axios.get(
                    `${this.apiBase}/rating/user/${this.currentUser.user_id}`
                );
                this.userRatings = {};
                response.data.ratings.forEach(rating => {
                    this.userRatings[rating.item_id] = rating.rating;
                });
            } catch (error) {
                console.error('加载用户评分失败:', error);
            }
        },

        async submitComment() {
            if (!this.currentUser) {
                return;
            }
            
            if (!this.newComment.trim()) {
                alert('请输入评论内容');
                return;
            }
            
            try {
                await axios.post(`${this.apiBase}/comment/add`, {
                    user_id: this.currentUser.user_id,
                    item_id: this.itemDetail.item_id,
                    content: this.newComment.trim()
                });
                
                this.newComment = '';
                await this.loadItemComments(this.itemDetail.item_id);
                
                // 重新加载用户评论列表
                await this.loadComments();
                
                alert('评论发表成功！');
            } catch (error) {
                console.error('发表评论失败:', error);
                alert('发表评论失败，请重试');
            }
        },

        async deleteCommentInDetail(commentId) {
            if (!confirm('确定要删除这条评论吗？')) {
                return;
            }
            
            try {
                await axios.delete(`${this.apiBase}/comment/${commentId}`);
                
                // 重新加载评论列表
                await this.loadItemComments(this.itemDetail.item_id);
                
                // 重新加载用户评论列表
                await this.loadComments();
                
                // 更新统计
                this.profileData.stats.comment_count--;
                
                alert('评论已删除');
            } catch (error) {
                console.error('删除评论失败:', error);
                alert('删除评论失败，请重试');
            }
        },

        closeDetailModal() {
            this.showDetailModal = false;
            this.itemDetail = null;
            this.itemComments = [];
            this.similarItems = [];
            this.newComment = '';
        },

        getRatingPercentage(star) {
            if (!this.itemDetail || this.itemDetail.rating_stats.count === 0) {
                return 0;
            }
            return (this.itemDetail.rating_stats.distribution[star] / 
                    this.itemDetail.rating_stats.count * 100);
        },

        async rateItem(itemId, rating) {
            if (!this.currentUser) {
                return;
            }
            
            try {
                await axios.post(`${this.apiBase}/rating/add`, {
                    user_id: this.currentUser.user_id,
                    item_id: itemId,
                    rating: rating
                });
                
                this.userRatings[itemId] = rating;
                
                // 重新加载景点详情
                await this.loadItemDetail(itemId);
                
                // 重新加载评分历史
                await this.loadRatingHistory();
                
                alert('评分成功！');
            } catch (error) {
                console.error('评分失败:', error);
                alert('评分失败，请重试');
            }
        }

    }
});
// 挂载并暴露到全局（用于调试）
window.app = app.mount('#app');