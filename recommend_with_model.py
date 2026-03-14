import re
import pandas as pd
import numpy as np
import os
import torch

# 支持灵活的路径配置
import sys
from pathlib import Path

# 获取项目根目录
if hasattr(sys, '_MEIPASS'):
    # PyInstaller 打包后的路径
    BASE_DIR = Path(sys._MEIPASS)
else:
    # 开发环境路径
    BASE_DIR = Path(__file__).resolve().parent

# 优先使用新路径，如果不存在则使用旧路径
MODEL_PATH_NEW = BASE_DIR / 'src' / 'data' / 'models'
MODEL_PATH_OLD = BASE_DIR / 'train' / 'saved'

if MODEL_PATH_NEW.exists() and list(MODEL_PATH_NEW.glob('*.pth')):
    MODEL_PATH = str(MODEL_PATH_NEW)
elif MODEL_PATH_OLD.exists():
    MODEL_PATH = str(MODEL_PATH_OLD)
else:
    MODEL_PATH = './train/saved'  # 默认路径

DATA_DIR = str(BASE_DIR / 'dataset' / 'yelp_tourism')
OUTPUT_DIR = str(BASE_DIR / 'recommend_results')
# =======================================


class LightGCNRecommender:
    """LightGCN 推荐系统"""

    def __init__(self, model_file=None):
        """初始化推荐系统，只加载模型参数"""
        # 自动选择最新的模型文件
        if model_file is None:
            model_files = [f for f in os.listdir(MODEL_PATH) if f.endswith('.pth')]
            if not model_files:
                raise FileNotFoundError(f"在 {MODEL_PATH} 目录下没有找到模型文件")
            model_files.sort(key=lambda x: os.path.getmtime(os.path.join(MODEL_PATH, x)), reverse=True)
            model_file = os.path.join(MODEL_PATH, model_files[0])

        # 加载模型参数
        checkpoint = torch.load(model_file, map_location='cpu')

        # 提取嵌入矩阵（推理不需要加载整个模型），只需要用户嵌入矩阵和物品嵌入矩阵，两者点积得到分数
        state_dict = checkpoint['state_dict']
        self.user_embeddings = state_dict['user_embedding.weight'].cpu()  #用户兴趣特征128维
        self.item_embeddings = state_dict['item_embedding.weight'].cpu()  #物品对应特征128维

        self.num_users = self.user_embeddings.shape[0]  # 获取用户总数
        self.num_items = self.item_embeddings.shape[0]  # 获取物品总数

        #关联映射表
        self.map_df = pd.read_csv(os.path.join(DATA_DIR, 'item_mapping_travel.csv'))
        self.inter_df = pd.read_csv(
            os.path.join(DATA_DIR, 'yelp_tourism.inter'),
            sep='\t'
        )

        self.inter_df.columns = ['user_id', 'item_id', 'rating', 'timestamp']

        # 构建邻接关系（用于图卷积）用于实时图传播
        # 1.训练时用过图，但图结构被扔掉了，只保留了节点 embedding。为了新用户能"桥接"，必须在推理时重建这张图。
        # 2.老用户的嵌入已经是训练收敛后的最终状态（已经通过图卷积聚合过邻居信息）直接查表 self.user_embeddings[user_id] 就行
        self._build_graph()

        # 存储新用户的评分数据
        self.new_user_ratings = {}


    #构建用户-物品二部图的邻接关系，用于实时图传播的协同过滤
    def _build_graph(self):
        """构建用户-物品二部图的邻接关系"""
        self.user_items = {}
        self.item_users = {}

        for _, row in self.inter_df.iterrows():
            user_id = int(row['user_id'])
            item_id = int(row['item_id'])

            if user_id not in self.user_items:
                self.user_items[user_id] = []
            self.user_items[user_id].append(item_id)

            if item_id not in self.item_users:
                self.item_users[item_id] = []
            self.item_users[item_id].append(user_id)

    #判断函数
    def is_new_user(self, user_id):
        """判断是否为新用户"""
        return user_id >= self.num_users

    def add_user_rating(self, user_id, item_id, rating):
        """添加用户评分"""
        if user_id not in self.new_user_ratings:
            self.new_user_ratings[user_id] = []
        self.new_user_ratings[user_id].append((item_id, rating))



    """获取用户历史交互记录"""
    def get_user_history(self, user_id):
        """获取用户历史交互记录"""
        history = self.inter_df[self.inter_df['user_id'] == user_id]['item_id'].tolist()
        if user_id in self.new_user_ratings:
            history.extend([item_id for item_id, _ in self.new_user_ratings[user_id]])
        return history

    def recommend(self, user_id, top_k=10):

        is_new = self.is_new_user(user_id)
        has_ratings = user_id in self.new_user_ratings and len(self.new_user_ratings[user_id]) > 0

        if is_new and not has_ratings:
            return self.recommend_popular(user_id, top_k)
        elif is_new and has_ratings:
            return self.recommend_with_realtime_propagation(user_id, top_k)
        else:
            return self.recommend_with_model(user_id, top_k)

    #1.热门推荐（冷启动）
    def recommend_popular(self, user_id, top_k=32):
        """热门推荐（冷启动）"""
        history = set(self.get_user_history(user_id)) #用于去重

        item_stats = self.inter_df.groupby('item_id').agg({
            'rating': ['count', 'mean']
        }).reset_index()
        item_stats.columns = ['item_id', 'interaction_count', 'avg_rating']
        item_stats['popularity_score'] = (
            item_stats['interaction_count'] * 0.7 +
            item_stats['avg_rating'] * 10
        )
        item_popularity = item_stats.sort_values('popularity_score', ascending=False)

        rec_list = []
        for _, row in item_popularity.iterrows():
            if row['item_id'] not in history:
                item_info = self.map_df[self.map_df['item_id'] == row['item_id']]
                item_name = item_info['display_name'].values[0] if len(item_info) > 0 else f"景点 {row['item_id']}"
                main_category = item_info['main_category'].values[0] if len(item_info) > 0 else "未知类别"
                rec_list.append({
                    'user_id': user_id,
                    'item_id': int(row['item_id']),
                    'item_name': item_name,
                    'main_category': main_category,
                    'score': row['popularity_score'],
                    'strategy': 'popular'
                })
                if len(rec_list) >= top_k:
                    break
        return rec_list

    #2.实时图传播推荐入口
    def recommend_with_realtime_propagation(self, user_id, top_k=32):

        history = set(self.get_user_history(user_id)) #用于后续去重

        # 同时获取正负样本
        user_emb, negative_items = self.get_user_embedding_realtime(user_id, n_layers=2)

        # 计算分数，作点积（涉及矩阵分解，分越高越相似，最高为1）
        scores = torch.matmul(user_emb, self.item_embeddings.T)
####################
        # 获取用户喜欢的类别，给同类别物品加分
        user_categories = set()
        if user_id in self.new_user_ratings:
            for item_id, rating in self.new_user_ratings[user_id]:
                if rating >= 4:
                    item_info = self.map_df[self.map_df['item_id'] == item_id]
                    if len(item_info) > 0:
                        user_categories.add(item_info['main_category'].values[0])

        # 给同类别的物品加分
        if len(user_categories) > 0:
            for item_id in range(self.num_items):
                item_info = self.map_df[self.map_df['item_id'] == item_id]
                if len(item_info) > 0:
                    item_category = item_info['main_category'].values[0]
                    if item_category in user_categories:
                        scores[item_id] *= 1.5  # 同类别提升50%
#########################
        # 排除历史物品
        for item_id in history:
            if item_id < len(scores):
                scores[item_id] = float('-inf')

        #排除负样本（低分物品）
        for item_id in negative_items:
            if item_id < len(scores):
                scores[item_id] = float('-inf')

        #进一步：降低与负样本相似的物品分数
        if len(negative_items) > 0:   #检查负样本
            for neg_item_id in negative_items:
                if neg_item_id < self.num_items:
                    neg_emb = self.item_embeddings[neg_item_id] #neg_emb 形状：[1, 128] （一个负样本）
                    # 计算所有物品与负样本的相似度，作点积
                    similarities = torch.matmul(neg_emb, self.item_embeddings.T)  #训练模型的形状：[num_items, 128] （所有景点）
                    # 对相似度高的物品进行惩罚（降低分数）
                    penalty_mask = similarities > 0.5  # 相似度阈值，大于0.5差不多认为是同一类
                    scores[penalty_mask] -= 2.0  # 惩罚分数，降低排名

        #取分数最高的top_k个
        top_scores, top_items = torch.topk(scores, min(top_k, len(scores)))
        top_items = top_items.numpy()
        top_scores = top_scores.numpy()

        #组装推荐列表
        rec_list = []
        for item_id, score in zip(top_items, top_scores):
            if score == float('-inf'):     #负样本再过滤检查
                continue
            #调用映射表获取物品信息
            item_info = self.map_df[self.map_df['item_id'] == item_id]
            item_name = item_info['display_name'].values[0] if len(item_info) > 0 else f"景点 {item_id}"
            main_category = item_info['main_category'].values[0] if len(item_info) > 0 else "未知类别"
            #组装成一条记录
            rec_list.append({
                'user_id': user_id,
                'item_id': int(item_id),
                'item_name': item_name,
                'main_category': main_category,
                'score': float(score),
                'strategy': 'realtime_propagation_with_negative'
            })
        return rec_list
    #聚合正项样本到user_emb，分离负向样本到neg_items
    def get_user_embedding_realtime(self, user_id, n_layers=2):
        #如果为空，则返回一个全零向量
        if user_id not in self.new_user_ratings or not self.new_user_ratings[user_id]:
            return torch.zeros(self.item_embeddings.shape[1]), []

        ratings = self.new_user_ratings[user_id]

        pos_items = [item_id for item_id, r in ratings if r >= 4.0]
        neg_items = [item_id for item_id, r in ratings if r <= 2.0]

        #聚合正项样本
        user_emb = self._aggregate_from_positive_items(pos_items, n_layers=n_layers)

        return user_emb, neg_items
    #聚合正项样本函数，卷积核心
    def _aggregate_from_positive_items(self, pos_items, n_layers=2, temperature=0.05):

        if not pos_items:
            return torch.zeros(self.item_embeddings.shape[1])

        valid_pos = [i for i in pos_items if i < self.num_items]
        if not valid_pos:
            return torch.zeros(self.item_embeddings.shape[1])

        # 第0层
        layer_0 = torch.stack([self.item_embeddings[i] for i in valid_pos]).mean(dim=0)
        layers = [layer_0]

        if n_layers == 0:
            return layer_0

        # 第1层
        neighbor_users = set()
        for item_id in valid_pos:
            if item_id in self.item_users:
                neighbor_users.update(self.item_users[item_id])

        if neighbor_users:
            valid_neighbors = [u for u in neighbor_users if u < self.num_users]
            layer_1 = torch.stack([self.user_embeddings[u] for u in valid_neighbors]).mean(dim=0)
            layers.append(layer_1)

        if n_layers >= 2 and len(layers) > 1:
            # 第2层
            neighbor_items = set()
            for user_id in valid_neighbors:
                if user_id in self.user_items:
                    neighbor_items.update(self.user_items[user_id])
            neighbor_items -= set(valid_pos)

            if neighbor_items:
                valid_neighbor_items = [i for i in neighbor_items if i < self.num_items]
                layer_2 = torch.stack([self.item_embeddings[i] for i in valid_neighbor_items]).mean(dim=0)
                layers.append(layer_2)

        # 计算注意力权重（以layer_0为query）
        if len(layers) == 1:
            return layers[0]

        # 计算相似度分数
        scores = torch.stack([
            torch.cosine_similarity(layer_0, layer, dim=0)
            for layer in layers
        ])

        # Softmax归一化（temperature控制集中度）
        weights = torch.softmax(scores / temperature, dim=0)
#############
        # 强制提升layer_0权重：确保直接兴趣占主导
        # 方法：给layer_0的权重乘以一个增强系数，然后重新归一化
        boost_factor = 2.0  # layer_0权重增强倍数
        weights[0] *= boost_factor
        weights = weights / weights.sum()  # 重新归一化
# ##############

        # 加权求和
        result = sum(w * layer for w, layer in zip(weights, layers))
        return result

    #3.使用训练好的模型推荐（老用户）
    def recommend_with_model(self, user_id, top_k=32):
        """使用训练好的模型推荐（老用户）"""
        history = set(self.get_user_history(user_id))

        user_emb = self.user_embeddings[user_id]
        scores = torch.matmul(user_emb, self.item_embeddings.T)

        for item_id in history:
            scores[item_id] = float('-inf')

        top_scores, top_items = torch.topk(scores, top_k)
        top_items = top_items.numpy()
        top_scores = top_scores.numpy()

        rec_list = []
        for item_id, score in zip(top_items, top_scores):
            item_info = self.map_df[self.map_df['item_id'] == item_id]
            item_name = item_info['display_name'].values[0] if len(item_info) > 0 else f"景点 {item_id}"
            main_category = item_info['main_category'].values[0] if len(item_info) > 0 else "未知类别"
            rec_list.append({
                'user_id': user_id,
                'item_id': int(item_id),
                'item_name': item_name,
                'main_category': main_category,
                'score': float(score),
                'strategy': 'model_embedding'
            })
        return rec_list



def main():
    """演示三种推荐策略"""
    recommender = LightGCNRecommender()

    max_user_id = recommender.num_users - 1
    new_user_id = max_user_id + 1

    print(f"训练集最大用户 ID：{max_user_id}")
    print(f"模拟新用户 ID：{new_user_id}\n")

    # 场景 1：新用户无评分 - 热门推荐
    print("场景 1：新用户刚注册，无评分（热门推荐）")
    recs = recommender.recommend(new_user_id, top_k=3)
    print(f"策略：{recs[0]['strategy']}")
    for i, rec in enumerate(recs[:3], 1):
            print(f"  {i}. {rec['item_name']} [{rec['main_category']}] (分数: {rec['score']:.4f})")

    # 场景 2：新用户评分 1 个低分景点 - 实时图传播（测试负样本），实测为0分，过滤掉了负样本，模型只知道用户喜欢什么，如果只有负样本则无法聚合
    print("\n场景 2：新用户评分了 1 个低分景点（实时图传播 2层，负样本嫁接）")
    recommender.add_user_rating(new_user_id, item_id=5, rating=1.0)
    recs = recommender.recommend(new_user_id, top_k=5)
    print(f"策略：{recs[0]['strategy']}")
    for i, rec in enumerate(recs[:3], 1):
        print(f"  {i}. {rec['item_name']} [{rec['main_category']}] (分数: {rec['score']:.4f})")


    #测试验证模型
    #打印老用户id=1的景点偏好，并取出最高的10个
    # pianhao=torch.matmul(recommender.user_embeddings[1], recommender.item_embeddings.T)
    # print("\n老用户id=1的景点偏好:",pianhao)
    # top_fenshu, top_id = torch.topk(pianhao, 10)
    # print("\n老用户id=1分数最高的10个景点ID和分数:",top_id,"|",top_fenshu)

    # 场景 3：新用户又评分 2 个景点 - 实时图传播
    print("\n场景 3：新用户又评分了 2 个景点（实时图传播 2层）")
    recommender.add_user_rating(new_user_id, item_id=24, rating=5.0)
    recommender.add_user_rating(new_user_id, item_id=47, rating=5.0)
    recommender.add_user_rating(new_user_id, item_id=52, rating=5.0)
    recs = recommender.recommend(new_user_id, top_k=10)
    print(f"策略：{recs[0]['strategy']}")
    for i, rec in enumerate(recs[:10], 1):
        print(f"  {i}. {rec['item_name'],rec['main_category']} (分数: {rec['score']:.4f})")


    # 场景 4：老用户 - 模型嵌入
    print("\n场景 4：老用户推荐（模型嵌入）")
    old_user_id = 0
    recs = recommender.recommend(old_user_id, top_k=5)
    print(f"策略：{recs[0]['strategy']}")
    for i, rec in enumerate(recs[:3], 1):
        print(f"  {i}. {rec['item_name']} (分数: {rec['score']:.4f})")


    # 保存推荐结果
    all_results = []
    users = recommender.inter_df['user_id'].unique()
    for user_id in users[:10]:
        all_results.extend(recommender.recommend(user_id, top_k=5))

    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)
    pd.DataFrame(all_results).to_csv(
        os.path.join(OUTPUT_DIR, 'lightgcn_rec_results.csv'),
        index=False
    )
    print(f"\n推荐结果已保存至：{OUTPUT_DIR}/lightgcn_rec_results.csv")


if __name__ == '__main__':
    main()
