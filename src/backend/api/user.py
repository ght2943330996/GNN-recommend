"""
用户相关 API
"""
from flask import Blueprint, request, jsonify
from ..models.database import db, User, Rating

user_bp = Blueprint('user', __name__, url_prefix='/api/user')


@user_bp.route('/register', methods=['POST'])
def register():
    """用户注册"""
    data = request.json
    username = data.get('username')
    password = data.get('password')

    if not username or not password:
        return jsonify({'error': '用户名和密码不能为空'}), 400

    # 检查用户是否已存在
    if User.query.filter_by(username=username).first():
        return jsonify({'error': '用户名已存在'}), 400

    # 导入推荐服务
    from ..services.recommender import recommender_service
    
    # 创建新用户（分配新的 user_id）
    max_user_id = recommender_service.num_users - 1
    new_user_id = max_user_id + User.query.count() + 1

    user = User(user_id=new_user_id, username=username)
    user.set_password(password)

    db.session.add(user)
    db.session.commit()

    return jsonify({
        'message': '注册成功',
        'user_id': user.user_id,
        'username': user.username
    }), 201


@user_bp.route('/login', methods=['POST'])
def login():
    """用户登录"""
    data = request.json
    username = data.get('username')
    password = data.get('password')

    user = User.query.filter_by(username=username).first()

    if not user or not user.check_password(password):
        return jsonify({'error': '用户名或密码错误'}), 401

    # 导入推荐服务
    from ..services.recommender import recommender_service

    return jsonify({
        'message': '登录成功',
        'user_id': user.user_id,
        'username': user.username,
        'is_new_user': recommender_service.is_new_user(user.user_id)
    }), 200


@user_bp.route('/<int:user_id>/info', methods=['GET'])
def get_user_info(user_id):
    """获取用户信息"""
    user = User.query.filter_by(user_id=user_id).first()

    if not user:
        return jsonify({'error': '用户不存在'}), 404

    # 获取用户评分数量
    rating_count = Rating.query.filter_by(user_id=user_id).count()
    
    # 导入推荐服务
    from ..services.recommender import recommender_service

    return jsonify({
        'user_id': user.user_id,
        'username': user.username,
        'rating_count': rating_count,
        'is_new_user': recommender_service.is_new_user(user.user_id),
        'created_at': user.created_at.isoformat()
    }), 200


@user_bp.route('/<int:user_id>/profile', methods=['GET'])
def get_user_profile(user_id):
    """获取用户完整资料"""
    from ..models.database import Comment, Favorite
    
    user = User.query.filter_by(user_id=user_id).first()
    if not user:
        return jsonify({'error': '用户不存在'}), 404

    # 统计数据
    rating_count = Rating.query.filter_by(user_id=user_id).count()
    comment_count = Comment.query.filter_by(user_id=user_id).count()
    favorite_count = Favorite.query.filter_by(user_id=user_id).count()
    
    return jsonify({
        'user_id': user.user_id,
        'username': user.username,
        'created_at': user.created_at.isoformat(),
        'stats': {
            'rating_count': rating_count,
            'comment_count': comment_count,
            'favorite_count': favorite_count
        }
    }), 200


@user_bp.route('/<int:user_id>/analysis', methods=['GET'])
def get_user_analysis(user_id):
    """获取用户画像分析"""
    from ..services.recommender import recommender_service
    from collections import Counter
    
    user = User.query.filter_by(user_id=user_id).first()
    if not user:
        return jsonify({'error': '用户不存在'}), 404

    # 获取用户所有评分
    ratings = Rating.query.filter_by(user_id=user_id).all()
    
    if not ratings:
        return jsonify({
            'user_id': user_id,
            'category_distribution': {},
            'rating_distribution': {1: 0, 2: 0, 3: 0, 4: 0, 5: 0},
            'favorite_categories': [],
            'personality_tags': [],
            'travel_style': '新手探索者'
        }), 200

    # 分析类别偏好
    category_counts = Counter()
    rating_distribution = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}
    high_rated_categories = []
    
    for rating in ratings:
        item_info = recommender_service.get_item_info(rating.item_id)
        if item_info:
            category = item_info['main_category']
            category_counts[category] += 1
            
            # 统计评分分布
            rating_star = int(rating.rating)
            rating_distribution[rating_star] += 1
            
            # 收集高分景点的类别
            if rating.rating >= 4:
                high_rated_categories.append(category)
    
    # 最喜欢的类别（按数量排序）
    favorite_categories = [
        {'category': cat, 'count': count} 
        for cat, count in category_counts.most_common(5)
    ]
    
    # 生成个性化标签
    personality_tags = generate_personality_tags(
        category_counts, 
        rating_distribution, 
        len(ratings)
    )
    
    # 判断旅行风格
    travel_style = determine_travel_style(
        category_counts, 
        rating_distribution, 
        len(ratings)
    )
    
    return jsonify({
        'user_id': user_id,
        'category_distribution': dict(category_counts),
        'rating_distribution': rating_distribution,
        'favorite_categories': favorite_categories,
        'personality_tags': personality_tags,
        'travel_style': travel_style
    }), 200


def generate_personality_tags(category_counts, rating_distribution, total_ratings):
    """生成个性化标签"""
    tags = []
    
    # 基于类别偏好生成标签
    if category_counts:
        top_category = category_counts.most_common(1)[0][0]
        category_tags = {
            '博物馆': '文化爱好者',
            '历史遗迹': '历史探索者',
            '公园景区': '自然爱好者',
            '海滩': '海滨度假者',
            '美食': '美食达人',
            '购物': '购物狂热者',
            '娱乐场所': '娱乐追求者',
            '户外活动': '冒险家',
            '宗教场所': '文化体验者',
            '动物园': '家庭出游者'
        }
        if top_category in category_tags:
            tags.append(category_tags[top_category])
    
    # 基于评分习惯生成标签
    high_ratings = rating_distribution.get(5, 0) + rating_distribution.get(4, 0)
    if total_ratings > 0:
        high_rating_ratio = high_ratings / total_ratings
        if high_rating_ratio > 0.7:
            tags.append('乐观旅行者')
        elif high_rating_ratio < 0.3:
            tags.append('挑剔鉴赏家')
    
    # 基于活跃度生成标签
    if total_ratings >= 20:
        tags.append('资深玩家')
    elif total_ratings >= 10:
        tags.append('活跃探索者')
    else:
        tags.append('新手上路')
    
    # 基于类别多样性生成标签
    if len(category_counts) >= 5:
        tags.append('全能旅行家')
    
    return tags[:4]  # 最多返回4个标签


def determine_travel_style(category_counts, rating_distribution, total_ratings):
    """判断旅行风格"""
    if not category_counts:
        return '新手探索者'
    
    # 统计不同类型的景点偏好
    cultural = sum(category_counts.get(cat, 0) for cat in ['博物馆', '历史遗迹', '文化艺术', '宗教场所'])
    nature = sum(category_counts.get(cat, 0) for cat in ['公园景区', '海滩', '户外活动'])
    leisure = sum(category_counts.get(cat, 0) for cat in ['美食', '购物', '娱乐场所', '商业区'])
    
    max_type = max(cultural, nature, leisure)
    
    if max_type == cultural and cultural > 0:
        return '文化探索型'
    elif max_type == nature and nature > 0:
        return '自然冒险型'
    elif max_type == leisure and leisure > 0:
        return '休闲享受型'
    else:
        return '均衡体验型'
