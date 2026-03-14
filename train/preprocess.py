import pandas as pd
import json
import os
from datetime import datetime
import datetime

# ================= 配置 =================
DATA_DIR = './data'
OUTPUT_DIR = './dataset/yelp_tourism/old'
KEYWORDS = ['Travel', 'Hotels', 'Resorts', 'Active Life', 'Tours',
            'Amusement Parks', 'Zoos', 'Museums', 'Landmarks',
            'Parks', 'Beaches', 'Vacation Rentals']
# 中等数据量，保证速度又有足够数据
DATA_SAMPLE = 6900000  # 600 万条评论
# 控制商家数量，避免过拟合
TOP_N_ITEMS = 233  # 保留热门商家数量（100-200之间）
# 用户最小交互次数（简单过滤，不用 K-Core）
MIN_USER_INTERACTIONS = 4  # 每个用户至少3次交互
# =======================================

def load_json(path, limit=None):
    print(f"   正在读取 {path}...")
    data = []
    with open(path, 'r', encoding='utf-8') as f:
        for i, line in enumerate(f):
            if limit and i >= limit:
                break
            data.append(json.loads(line))
            if (i + 1) % 50000 == 0:
                print(f"   已读取 {i+1} 行...")
    return pd.DataFrame(data)

def main():
    print("1. 加载数据...")
    # 商家数据全读（文件较小）
    biz_df = load_json(os.path.join(DATA_DIR, 'yelp_academic_dataset_business.json'))
    print(f"   商家数据总量：{len(biz_df)}")

    # 评论数据采样
    review_df = load_json(os.path.join(DATA_DIR, 'yelp_academic_dataset_review.json'), limit=DATA_SAMPLE)
    print(f"   评论数据采样：{len(review_df)}")

    print("2. 筛选旅游 POI...")
    biz_df['categories'] = biz_df['categories'].fillna('')
    mask = biz_df['categories'].apply(lambda x: any(k in x for k in KEYWORDS))
    tourism_biz = biz_df[mask].copy()
    tourism_ids = set(tourism_biz['business_id'])
    print(f"   筛选出 {len(tourism_biz)} 个旅游相关 POI")

    print("3. 过滤评论...")
    tourism_review = review_df[review_df['business_id'].isin(tourism_ids)].copy()
    print(f"   剩余 {len(tourism_review)} 条交互记录")

    # 关键：先筛选热门商家
    print(f"4. 筛选热门商家（保留前 {TOP_N_ITEMS} 个）...")
    item_counts = tourism_review.groupby('business_id').size().sort_values(ascending=False)
    print(f"   原始商家总数：{len(item_counts)}")

    top_items = set(item_counts.head(TOP_N_ITEMS).index)
    before_filter = len(tourism_review)
    tourism_review = tourism_review[tourism_review['business_id'].isin(top_items)]
    print(f"   筛选后：{len(top_items)} 个商家，{len(tourism_review)} 条记录（保留 {len(tourism_review)/before_filter*100:.1f}%）")

    # 简单用户过滤（不用 K-Core）
    print(f"5. 过滤低活跃用户（保留交互 ≥{MIN_USER_INTERACTIONS} 次的用户）...")
    u_count = tourism_review.groupby('user_id').size()
    valid_users = set(u_count[u_count >= MIN_USER_INTERACTIONS].index)
    before = len(tourism_review)
    tourism_review = tourism_review[tourism_review['user_id'].isin(valid_users)]
    after = len(tourism_review)
    print(f"   过滤前：{before} 条记录，{len(u_count)} 个用户")
    print(f"   过滤后：{after} 条记录，{len(valid_users)} 个用户（保留 {after/before*100:.1f}%）")

    if len(tourism_review) < 1000:
        print("   错误：数据量太少！")
        return

    print("6. ID 映射与保存...")
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)

    users = tourism_review['user_id'].unique()
    items = tourism_review['business_id'].unique()
    u_map = {u: i for i, u in enumerate(users)}
    i_map = {i: idx for idx, i in enumerate(items)}

    tourism_review['user_id'] = tourism_review['user_id'].map(u_map)
    tourism_review['business_id'] = tourism_review['business_id'].map(i_map)

    final_df = tourism_review[['user_id', 'business_id', 'stars', 'date']].copy()
    final_df.columns = ['user_id', 'item_id', 'rating', 'date']
    final_df['timestamp'] = pd.to_datetime(final_df['date']).astype('int64') // 10**9
    final_df = final_df.drop(columns=['date'])

    inter_path = os.path.join(OUTPUT_DIR, 'yelp_tourism.inter')
    with open(inter_path, 'w', encoding='utf-8') as f:
        f.write('user_id:token\titem_id:token\trating:float\ttimestamp:float\n')
        final_df.to_csv(f, sep='\t', index=False, header=False)

    demo_map = []
    biz_subset = tourism_biz[tourism_biz['business_id'].isin(items)]
    for _, row in biz_subset.iterrows():
        original_id = row['business_id']
        if original_id in i_map:
            demo_map.append({
                'item_id': i_map[original_id],
                'original_name': row['name'],
                'display_name': f"旅游景点 {i_map[original_id]}",
                'category': row['categories']
            })
    pd.DataFrame(demo_map).to_csv(os.path.join(OUTPUT_DIR, 'item_mapping.csv'), index=False)

    print("\n预处理完成！")
    print(f"   交互记录：{len(tourism_review)}")
    print(f"   用户数：{len(users)}")
    print(f"   物品数：{len(items)}")
    print(f"   平均每用户交互：{len(tourism_review) / len(users):.2f}")
    print(f"   平均每商家交互：{len(tourism_review) / len(items):.2f}")

    # 数据质量评估
    print("\n数据质量评估：")
    avg_per_user = len(tourism_review) / len(users)
    if avg_per_user < 5:
        print(f"   警告：平均每用户交互 {avg_per_user:.2f} 次，建议 ≥10 次")
        print(f"   建议：降低 MIN_USER_INTERACTIONS 或增加 TOP_N_ITEMS")
    elif avg_per_user < 10:
        print(f"   ⚙️ 可用：平均每用户交互 {avg_per_user:.2f} 次，勉强可用")
        print(f"   建议：如果模型效果不好，可以降低 MIN_USER_INTERACTIONS")
    else:
        print(f"   良好：平均每用户交互 {avg_per_user:.2f} 次")

    # 数据分布统计
    user_interaction_dist = u_count[u_count >= MIN_USER_INTERACTIONS]
    print(f"\n用户交互分布：")
    print(f"   中位数：{user_interaction_dist.median():.0f} 次")
    print(f"   75分位：{user_interaction_dist.quantile(0.75):.0f} 次")
    print(f"   90分位：{user_interaction_dist.quantile(0.90):.0f} 次")

    print(f"\n   文件路径：{inter_path}")

if __name__ == '__main__':
    main()
