"""
评分相关 API
"""
from flask import Blueprint, request, jsonify
from ..models.database import db, User, Rating
from ..services.recommender import recommender_service

rating_bp = Blueprint('rating', __name__, url_prefix='/api/rating')


@rating_bp.route('/add', methods=['POST'])
def add_rating():
    """添加或更新评分"""
    data = request.json
    user_id = data.get('user_id')
    item_id = data.get('item_id')
    rating_value = data.get('rating')

    if not all([user_id, item_id, rating_value]):
        return jsonify({'error': '缺少必要参数'}), 400

    if not (1 <= rating_value <= 5):
        return jsonify({'error': '评分必须在1-5之间'}), 400

    # 检查用户是否存在
    user = User.query.filter_by(user_id=user_id).first()
    if not user:
        return jsonify({'error': '用户不存在'}), 404

    # 检查是否已评分
    existing_rating = Rating.query.filter_by(
        user_id=user_id,
        item_id=item_id
    ).first()

    if existing_rating:
        # 更新评分
        existing_rating.rating = rating_value
        message = '评分已更新'
    else:
        # 新增评分
        new_rating = Rating(
            user_id=user_id,
            item_id=item_id,
            rating=rating_value
        )
        db.session.add(new_rating)
        message = '评分已添加'

    db.session.commit()

    # 更新推荐系统中的评分
    recommender_service.add_user_rating(user_id, item_id, rating_value)

    return jsonify({
        'message': message,
        'user_id': user_id,
        'item_id': item_id,
        'rating': rating_value
    }), 200


@rating_bp.route('/user/<int:user_id>', methods=['GET'])
def get_user_ratings(user_id):
    """获取用户的所有评分"""
    ratings = Rating.query.filter_by(user_id=user_id).all()

    rating_list = []
    for rating in ratings:
        # 获取景点信息
        item_info = recommender_service.get_item_info(rating.item_id)
        if item_info:
            rating_list.append({
                'rating_id': rating.id,
                'item_id': rating.item_id,
                'item_name': item_info['item_name'],
                'main_category': item_info['main_category'],
                'rating': rating.rating,
                'created_at': rating.created_at.isoformat()
            })

    return jsonify({
        'user_id': user_id,
        'ratings': rating_list,
        'count': len(rating_list)
    }), 200


@rating_bp.route('/user/<int:user_id>/history', methods=['GET'])
def get_user_rating_history(user_id):
    """获取用户评分历史（带详细信息）"""
    # 获取分页参数
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    
    # 获取筛选参数
    rating_filter = request.args.get('rating', type=int)  # 按评分筛选
    category_filter = request.args.get('category', type=str)  # 按类别筛选
    
    # 查询评分
    query = Rating.query.filter_by(user_id=user_id).order_by(Rating.updated_at.desc())
    
    ratings = query.all()
    
    # 构建评分列表
    rating_list = []
    for rating in ratings:
        item_info = recommender_service.get_item_info(rating.item_id)
        if item_info:
            # 应用筛选
            if rating_filter and int(rating.rating) != rating_filter:
                continue
            if category_filter and item_info['main_category'] != category_filter:
                continue
                
            rating_list.append({
                'rating_id': rating.id,
                'item_id': rating.item_id,
                'item_name': item_info['item_name'],
                'main_category': item_info['main_category'],
                'rating': rating.rating,
                'created_at': rating.created_at.isoformat(),
                'updated_at': rating.updated_at.isoformat()
            })
    
    # 手动分页
    total = len(rating_list)
    start = (page - 1) * per_page
    end = start + per_page
    paginated_list = rating_list[start:end]
    
    return jsonify({
        'user_id': user_id,
        'ratings': paginated_list,
        'total': total,
        'page': page,
        'per_page': per_page,
        'pages': (total + per_page - 1) // per_page
    }), 200


@rating_bp.route('/update', methods=['PUT'])
def update_rating():
    """更新评分"""
    data = request.json
    rating_id = data.get('rating_id')
    new_rating = data.get('rating')
    
    if not rating_id or not new_rating:
        return jsonify({'error': '缺少必要参数'}), 400
    
    if not (1 <= new_rating <= 5):
        return jsonify({'error': '评分必须在1-5之间'}), 400
    
    rating = Rating.query.get(rating_id)
    if not rating:
        return jsonify({'error': '评分不存在'}), 404
    
    rating.rating = new_rating
    db.session.commit()
    
    # 更新推荐系统
    recommender_service.add_user_rating(rating.user_id, rating.item_id, new_rating)
    
    return jsonify({
        'message': '评分已更新',
        'rating_id': rating_id,
        'rating': new_rating
    }), 200
