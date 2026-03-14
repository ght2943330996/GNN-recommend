const { createApp } = Vue;

createApp({
    data() {
        return {
            // API 配置
            apiBase: 'http://localhost:5000/api',

            // 用户状态
            currentUser: null,
            showUserMenu: false,

            // 导航状态
            isScrolled: false,

            // 模态框状态
            showAuthModal: false,
            showDetailModal: false,
            showFavoritesModal: false,
            isLogin: true,

            // 表单数据
            authForm: {
                username: '',
                password: ''
            },

            // 消息
            errorMessage: '',
            successMessage: '',

            // 数据加载状态
            loading: false,

            // 推荐数据
            recommendations: [],
            popularItems: [],
            allItems: [],
            categories: [],

            // 用户数据
            userRatings: {},
            favoriteIds: new Set(),
            favoriteItems: [],

            // 搜索和筛选
            searchKeyword: '',
            selectedCategory: '',

            // 景点详情
            itemDetail: null,
            itemComments: [],
            similarItems: [],
            newComment: '',

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

    computed: {
        filteredRecommendations() {
            return this.filterItems(this.recommendations).slice(0, 9);
        },

        filteredPopular() {
            return this.filterItems(this.popularItems).slice(0, 9);
        },

        filteredAllItems() {
            return this.filterItems(this.allItems).slice(0, 51);
        }
    },

    mounted() {
        // 检查本地存储
        const savedUser = localStorage.getItem('currentUser');
        if (savedUser) {
            this.currentUser = JSON.parse(savedUser);
            this.loadUserData();
        }

        // 监听滚动
        window.addEventListener('scroll', this.handleScroll);

        // 点击外部关闭下拉菜单
        document.addEventListener('click', this.handleClickOutside);

        // 加载类别
        this.loadCategories();

    },

    beforeUnmount() {
        window.removeEventListener('scroll', this.handleScroll);
        document.removeEventListener('click', this.handleClickOutside);
    },

    methods: {
        // ==================== 工具方法 ====================

        handleScroll() {
            this.isScrolled = window.scrollY > 50;
        },

        handleClickOutside(event) {
            if (!event.target.closest('.nav-user')) {
                this.showUserMenu = false;
            }
        },

        scrollToSection(sectionId) {
            const element = document.getElementById(sectionId);
            if (element) {
                const offset = 80;
                const elementPosition = element.getBoundingClientRect().top;
                const offsetPosition = elementPosition + window.pageYOffset - offset;

                window.scrollTo({
                    top: offsetPosition,
                    behavior: 'smooth'
                });
            }
        },

        getPlaceImage(category) {
            return this.categoryImages[category] || this.categoryImages['默认'];
        },

        formatDate(dateString) {
            const date = new Date(dateString);
            const now = new Date();
            const diff = now - date;
            const days = Math.floor(diff / (1000 * 60 * 60 * 24));

            if (days === 0) return '今天';
            if (days === 1) return '昨天';
            if (days < 7) return `${days}天前`;

            return date.toLocaleDateString('zh-CN', {
                year: 'numeric',
                month: 'long',
                day: 'numeric'
            });
        },

        // ==================== 认证相关 ====================

        showLoginModal() {
            this.isLogin = true;
            this.showAuthModal = true;
            this.errorMessage = '';
            this.successMessage = '';
        },

        showRegisterModal() {
            this.isLogin = false;
            this.showAuthModal = true;
            this.errorMessage = '';
            this.successMessage = '';
        },

        closeAuthModal() {
            this.showAuthModal = false;
            this.authForm = { username: '', password: '' };
            this.errorMessage = '';
            this.successMessage = '';
        },

        toggleAuthMode() {
            this.isLogin = !this.isLogin;
            this.errorMessage = '';
            this.successMessage = '';
        },

        async handleAuth() {
            this.errorMessage = '';
            this.successMessage = '';

            if (!this.authForm.username || !this.authForm.password) {
                this.errorMessage = '请填写完整信息';
                return;
            }

            try {
                const endpoint = this.isLogin ? '/user/login' : '/user/register';
                const response = await axios.post(`${this.apiBase}${endpoint}`, this.authForm);

                if (this.isLogin) {
                    this.currentUser = response.data;
                    localStorage.setItem('currentUser', JSON.stringify(this.currentUser));
                    this.closeAuthModal();
                    await this.loadUserData();
                } else {
                    this.successMessage = '注册成功！请登录';
                    setTimeout(() => {
                        this.isLogin = true;
                        this.successMessage = '';
                        this.authForm.password = '';
                    }, 1500);
                }
            } catch (error) {
                this.errorMessage = error.response?.data?.error || '操作失败，请重试';
            }
        },

        logout() {
            this.currentUser = null;
            localStorage.removeItem('currentUser');
            this.recommendations = [];
            this.popularItems = [];
            this.userRatings = {};
            this.favoriteIds.clear();
            this.favoriteItems = [];
            this.showUserMenu = false;
        },

        toggleUserMenu() {
            this.showUserMenu = !this.showUserMenu;
        },

        // ==================== 数据加载 ====================

        async loadUserData() {
            await Promise.all([
                this.loadUserRatings(),
                this.loadRecommendations(),
                this.loadPopularItems(),
                this.loadAllItems(),
                this.loadFavorites()
            ]);
        },

        async loadCategories() {
            try {
                const response = await axios.get(`${this.apiBase}/categories`);
                this.categories = response.data.categories;
            } catch (error) {
                console.error('加载类别失败:', error);
            }
        },

        async loadRecommendations() {
            if (!this.currentUser) return;

            this.loading = true;
            try {
                const response = await axios.get(
                    `${this.apiBase}/recommend/${this.currentUser.user_id}?top_k=20`
                );
                this.recommendations = response.data.recommendations;
            } catch (error) {
                console.error('加载推荐失败:', error);
            } finally {
                this.loading = false;
            }
        },

        async loadPopularItems() {
            this.loading = true;
            try {
                const response = await axios.get(`${this.apiBase}/popular?top_k=20`);
                this.popularItems = response.data.popular_items;
            } catch (error) {
                console.error('加载热门景点失败:', error);
            } finally {
                this.loading = false;
            }
        },

        async loadAllItems() {
            try {
                const response = await axios.get(`${this.apiBase}/items/search?limit=1000`);
                this.allItems = response.data.items;
            } catch (error) {
                console.error('加载全部景点失败:', error);
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

        // ==================== 评分功能 ====================

        async rateItem(itemId, rating) {
            if (!this.currentUser) {
                this.showLoginModal();
                return;
            }

            try {
                await axios.post(`${this.apiBase}/rating/add`, {
                    user_id: this.currentUser.user_id,
                    item_id: itemId,
                    rating: rating
                });

                this.userRatings[itemId] = rating;

                // 刷新推荐
                await this.loadRecommendations();
            } catch (error) {
                console.error('评分失败:', error);
                alert('评分失败，请重试');
            }
        },

        // ==================== 收藏功能 ====================

        isFavorite(itemId) {
            return this.favoriteIds.has(itemId);
        },

        // toggleFavorite(itemId) {
        //     if (!this.currentUser) {
        //         this.showLoginModal();
        //         return;
        //     }

        //     if (this.favoriteIds.has(itemId)) {
        //         this.favoriteIds.delete(itemId);
        //         this.favoriteItems = this.favoriteItems.filter(item => item.item_id !== itemId);
        //     } else {
        //         this.favoriteIds.add(itemId);
        //         // 从推荐或热门列表中找到该景点
        //         const item = [...this.recommendations, ...this.popularItems]
        //             .find(i => i.item_id === itemId);
        //         if (item) {
        //             this.favoriteItems.push(item);
        //         }
        //     }

        //     // 保存到本地存储
        //     this.saveFavorites();
        // },
        async toggleFavorite(itemId) {
            if (!this.currentUser) {
                this.showLoginModal();
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
                    this.favoriteItems = this.favoriteItems.filter(item => item.item_id !== itemId);
                } else {
                    // 添加收藏
                    await axios.post(`${this.apiBase}/favorite/add`, {
                        user_id: this.currentUser.user_id,
                        item_id: itemId
                    });

                    this.favoriteIds.add(itemId);
                    // 从推荐或热门列表中找到该景点
                    const item = [...this.recommendations, ...this.popularItems]
                        .find(i => i.item_id === itemId);
                    if (item) {
                        this.favoriteItems.push(item);
                    }
                }
            } catch (error) {
                console.error('收藏操作失败:', error);
                alert(error.response?.data?.error || '操作失败，请重试');
            }
        },

        // saveFavorites() {
        //     if (this.currentUser) {
        //         const key = `favorites_${this.currentUser.user_id}`;
        //         localStorage.setItem(key, JSON.stringify(Array.from(this.favoriteIds)));
        //     }
        // },

        // loadFavorites() {
        //     if (this.currentUser) {
        //         const key = `favorites_${this.currentUser.user_id}`;
        //         const saved = localStorage.getItem(key);
        //         if (saved) {
        //             this.favoriteIds = new Set(JSON.parse(saved));
        //             // 加载收藏的景点详情
        //             this.favoriteItems = [...this.recommendations, ...this.popularItems]
        //                 .filter(item => this.favoriteIds.has(item.item_id));
        //         }
        //     }
        // },
        async loadFavorites() {
            if (!this.currentUser) return;

            try {
                const response = await axios.get(
                    `${this.apiBase}/favorite/user/${this.currentUser.user_id}`
                );

                // 从后端加载收藏列表
                this.favoriteItems = response.data.favorites;
                this.favoriteIds = new Set(this.favoriteItems.map(item => item.item_id));
            } catch (error) {
                console.error('加载收藏失败:', error);
            }
        },

        showMyFavorites() {
            this.showUserMenu = false;
            this.showFavoritesModal = true;
        },

        closeFavoritesModal() {
            this.showFavoritesModal = false;
        },

        showMyProfile() {
            this.showUserMenu = false;
            window.location.href = 'profile.html';
        },

        // ==================== 搜索和筛选 ====================

        handleSearch() {
            // 搜索功能已通过 computed 属性实现
        },

        filterByCategory(category) {
            this.selectedCategory = category;
        },

        filterItems(items) {
            let filtered = items;

            // 按类别筛选
            if (this.selectedCategory) {
                filtered = filtered.filter(item =>
                    item.main_category === this.selectedCategory
                );
            }

            // 按关键词搜索
            if (this.searchKeyword) {
                const keyword = this.searchKeyword.toLowerCase();
                filtered = filtered.filter(item =>
                    item.item_name.toLowerCase().includes(keyword) ||
                    item.main_category.toLowerCase().includes(keyword)
                );
            }

            return filtered;
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
                this.loadSimilarItems(itemId)
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

        async submitComment() {
            if (!this.currentUser) {
                this.showLoginModal();
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
                alert('评论发表成功！');
            } catch (error) {
                console.error('发表评论失败:', error);
                alert('发表评论失败，请重试');
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

        async deleteCommentInDetail(commentId) {
            if (!confirm('确定要删除这条评论吗？')) {
                return;
            }

            try {
                await axios.delete(`${this.apiBase}/comment/${commentId}`);

                // 重新加载评论列表
                await this.loadItemComments(this.itemDetail.item_id);

                alert('评论已删除');
            } catch (error) {
                console.error('删除评论失败:', error);
                alert('删除评论失败，请重试');
            }
        }
    }
}).mount('#app');
