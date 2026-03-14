"""
推荐相关 API
"""
from flask import Blueprint, request, jsonify
from ..models.database import db, User, Rating
from ..services.recommender import recommender_service

recommend_bp = Blueprint('recommend', __name__, url_prefix='/api')


@recommend_bp.route('/recommend/<int:user_id>', methods=['GET'])
def get_recommendations(user_id):
    """获取推荐列表"""
    top_k = request.args.get('top_k', default=10, type=int)

    # 检查用户是否存在
    user = User.query.filter_by(user_id=user_id).first()
    if not user:
        return jsonify({'error': '用户不存在'}), 404

    # 加载用户评分到推荐系统
    ratings = Rating.query.filter_by(user_id=user_id).all()
    for rating in ratings:
        recommender_service.add_user_rating(user_id, rating.item_id, rating.rating)

    # 获取推荐
    recommendations = recommender_service.get_recommendations(user_id, top_k=top_k)

    return jsonify({
        'user_id': user_id,
        'recommendations': recommendations,
        'count': len(recommendations)
    }), 200


@recommend_bp.route('/popular', methods=['GET'])
def get_popular():
    """获取热门景点"""
    top_k = request.args.get('top_k', default=10, type=int)

    popular_items = recommender_service.get_popular_items(top_k=top_k)

    return jsonify({
        'popular_items': popular_items,
        'count': len(popular_items)
    }), 200


@recommend_bp.route('/categories', methods=['GET'])
def get_categories():
    """获取所有景点类别"""
    categories = recommender_service.get_categories()
    return jsonify({'categories': categories}), 200


@recommend_bp.route('/health', methods=['GET'])
def health_check():
    """健康检查"""
    return jsonify({
        'status': 'ok',
        'model_loaded': True,
        'num_users': recommender_service.num_users,
        'num_items': recommender_service.num_items
    }), 200
