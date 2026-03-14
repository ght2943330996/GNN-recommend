"""
推荐服务 - 封装推荐引擎
"""
import sys
import os
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).resolve().parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from recommend_with_model import LightGCNRecommender


class RecommenderService:
    """推荐服务单例"""
    
    _instance = None
    _recommender = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if self._recommender is None:
            self._load_recommender()
    
    def _load_recommender(self):
        """加载推荐引擎"""
        try:
            print("正在加载推荐模型...")
            self._recommender = LightGCNRecommender()
            print(f"✓ 模型加载成功！用户数: {self._recommender.num_users}, 景点数: {self._recommender.num_items}")
        except Exception as e:
            print(f"✗ 模型加载失败: {e}")
            raise
    
    @property
    def recommender(self):
        """获取推荐引擎实例"""
        return self._recommender
    
    def get_recommendations(self, user_id, top_k=10):
        """获取推荐列表"""
        return self._recommender.recommend(user_id, top_k=top_k)
    
    def get_popular_items(self, top_k=10):
        """获取热门景点"""
        return self._recommender.recommend_popular(user_id=999999, top_k=top_k)
    
    def add_user_rating(self, user_id, item_id, rating):
        """添加用户评分"""
        self._recommender.add_user_rating(user_id, item_id, rating)
    
    def is_new_user(self, user_id):
        """判断是否为新用户"""
        return self._recommender.is_new_user(user_id)
    
    def get_item_info(self, item_id):
        """获取景点信息"""
        item_info = self._recommender.map_df[self._recommender.map_df['item_id'] == item_id]
        if len(item_info) == 0:
            return None
        
        item = item_info.iloc[0]
        return {
            'item_id': int(item['item_id']),
            'item_name': item['display_name'],
            'main_category': item['main_category'],
            'original_name': item.get('name', '')
        }
    
    def search_items(self, keyword='', category='', limit=20):
        """搜索景点"""
        df = self._recommender.map_df
        
        if keyword:
            df = df[df['display_name'].str.contains(keyword, case=False, na=False)]
        
        if category:
            df = df[df['main_category'] == category]
        
        items = []
        for _, row in df.head(limit).iterrows():
            items.append({
                'item_id': int(row['item_id']),
                'item_name': row['display_name'],
                'main_category': row['main_category']
            })
        
        return items
    
    def get_categories(self):
        """获取所有类别"""
        return self._recommender.map_df['main_category'].unique().tolist()
    
    def get_similar_items(self, item_id, top_k=5):
        """获取相似景点（基于类别）"""
        item_info = self._recommender.map_df[self._recommender.map_df['item_id'] == item_id]
        
        if len(item_info) == 0:
            return []
        
        current_category = item_info['main_category'].values[0]
        
        similar_items = self._recommender.map_df[
            (self._recommender.map_df['main_category'] == current_category) &
            (self._recommender.map_df['item_id'] != item_id)
        ].head(top_k)
        
        return similar_items
    
    @property
    def num_users(self):
        """获取用户总数"""
        return self._recommender.num_users
    
    @property
    def num_items(self):
        """获取景点总数"""
        return self._recommender.num_items


# 创建全局实例
recommender_service = RecommenderService()
