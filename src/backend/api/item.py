"""
景点相关 API
"""
from flask import Blueprint, request, jsonify
from ..models.database import db, User, Rating, Comment, Favorite
from ..services.recommender import recommender_service

item_bp = Blueprint('item', __name__, url_prefix='/api')


@item_bp.route('/item/<int:item_id>', methods=['GET'])
def get_item_info(item_id):
    """获取景点基本信息"""
    item_info = recommender_service.get_item_info(item_id)
    
    if not item_info:
        return jsonify({'error': '景点不存在'}), 404
    
    return jsonify(item_info), 200


@item_bp.route('/item/<int:item_id>/detail', methods=['GET'])
def get_item_detail(item_id):
    """获取景点详细信息（包含评分统计和评论）"""
    # 获取景点基本信息
    item_info = recommender_service.get_item_info(item_id)
    
    if not item_info:
        return jsonify({'error': '景点不存在'}), 404

    # 获取评分统计
    ratings = Rating.query.filter_by(item_id=item_id).all()
    rating_count = len(ratings)
    avg_rating = sum(r.rating for r in ratings) / rating_count if rating_count > 0 else 0

    # 评分分布
    rating_distribution = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}
    for r in ratings:
        rating_distribution[int(r.rating)] += 1

    # 获取最新评论（前5条）
    recent_comments = Comment.query.filter_by(item_id=item_id)\
        .order_by(Comment.created_at.desc())\
        .limit(5)\
        .all()

    comments = [comment.to_dict() for comment in recent_comments]

    # 获取总评论数
    total_comments = Comment.query.filter_by(item_id=item_id).count()

    return jsonify({
        'item_id': item_info['item_id'],
        'item_name': item_info['item_name'],
        'main_category': item_info['main_category'],
        'original_name': item_info['original_name'],
        'rating_stats': {
            'count': rating_count,
            'average': round(avg_rating, 2),
            'distribution': rating_distribution
        },
        'comments': {
            'recent': comments,
            'total': total_comments
        }
    }), 200


@item_bp.route('/item/<int:item_id>/similar', methods=['GET'])
def get_similar_items(item_id):
    """获取相似景点（基于类别和评分）"""
    top_k = request.args.get('top_k', default=5, type=int)

    # 获取相似景点
    similar_items_df = recommender_service.get_similar_items(item_id, top_k=top_k)
    
    if len(similar_items_df) == 0:
        return jsonify({'error': '景点不存在'}), 404

    items = []
    for _, row in similar_items_df.iterrows():
        # 获取评分统计
        ratings = Rating.query.filter_by(item_id=int(row['item_id'])).all()
        rating_count = len(ratings)
        avg_rating = sum(r.rating for r in ratings) / rating_count if rating_count > 0 else 0

        items.append({
            'item_id': int(row['item_id']),
            'item_name': row['display_name'],
            'main_category': row['main_category'],
            'rating_count': rating_count,
            'avg_rating': round(avg_rating, 2)
        })

    return jsonify({
        'item_id': item_id,
        'similar_items': items,
        'count': len(items)
    }), 200


@item_bp.route('/items/search', methods=['GET'])
def search_items():
    """搜索景点"""
    keyword = request.args.get('keyword', '')
    category = request.args.get('category', '')
    limit = request.args.get('limit', default=20, type=int)

    items = recommender_service.search_items(keyword, category, limit)

    return jsonify({
        'items': items,
        'count': len(items)
    }), 200


# ==================== 评论相关 ====================

@item_bp.route('/comment/add', methods=['POST'])
def add_comment():
    """添加评论"""
    data = request.json
    user_id = data.get('user_id')
    item_id = data.get('item_id')
    content = data.get('content')

    if not all([user_id, item_id, content]):
        return jsonify({'error': '缺少必要参数'}), 400

    if not content.strip():
        return jsonify({'error': '评论内容不能为空'}), 400

    # 检查用户是否存在
    user = User.query.filter_by(user_id=user_id).first()
    if not user:
        return jsonify({'error': '用户不存在'}), 404

    # 创建评论
    comment = Comment(
        user_id=user_id,
        item_id=item_id,
        content=content.strip()
    )

    db.session.add(comment)
    db.session.commit()

    return jsonify({
        'message': '评论已添加',
        'comment': comment.to_dict()
    }), 201


@item_bp.route('/comment/item/<int:item_id>', methods=['GET'])
def get_item_comments(item_id):
    """获取景点的所有评论"""
    page = request.args.get('page', default=1, type=int)
    per_page = request.args.get('per_page', default=20, type=int)

    # 分页查询评论
    pagination = Comment.query.filter_by(item_id=item_id)\
        .order_by(Comment.created_at.desc())\
        .paginate(page=page, per_page=per_page, error_out=False)

    comments = [comment.to_dict() for comment in pagination.items]

    return jsonify({
        'item_id': item_id,
        'comments': comments,
        'total': pagination.total,
        'page': page,
        'per_page': per_page,
        'pages': pagination.pages
    }), 200


@item_bp.route('/comment/user/<int:user_id>', methods=['GET'])
def get_user_comments(user_id):
    """获取用户的所有评论"""
    comments = Comment.query.filter_by(user_id=user_id)\
        .order_by(Comment.created_at.desc())\
        .all()

    comment_list = []
    for comment in comments:
        comment_dict = comment.to_dict()
        # 添加景点信息
        item_info = recommender_service.get_item_info(comment.item_id)
        if item_info:
            comment_dict['item_name'] = item_info['item_name']
            comment_dict['main_category'] = item_info['main_category']
        comment_list.append(comment_dict)

    return jsonify({
        'user_id': user_id,
        'comments': comment_list,
        'count': len(comment_list)
    }), 200


@item_bp.route('/comment/<int:comment_id>', methods=['DELETE'])
def delete_comment(comment_id):
    """删除评论"""
    comment = Comment.query.get(comment_id)

    if not comment:
        return jsonify({'error': '评论不存在'}), 404

    db.session.delete(comment)
    db.session.commit()

    return jsonify({'message': '评论已删除'}), 200


# ==================== 收藏相关 ====================

@item_bp.route('/favorite/add', methods=['POST'])
def add_favorite():
    """添加收藏"""
    data = request.json
    user_id = data.get('user_id')
    item_id = data.get('item_id')

    if not all([user_id, item_id]):
        return jsonify({'error': '缺少必要参数'}), 400

    # 检查用户是否存在
    user = User.query.filter_by(user_id=user_id).first()
    if not user:
        return jsonify({'error': '用户不存在'}), 404

    # 检查是否已收藏
    existing = Favorite.query.filter_by(user_id=user_id, item_id=item_id).first()
    if existing:
        return jsonify({'error': '已经收藏过了'}), 400

    # 创建收藏
    favorite = Favorite(user_id=user_id, item_id=item_id)
    db.session.add(favorite)
    db.session.commit()

    return jsonify({
        'message': '收藏成功',
        'favorite': favorite.to_dict()
    }), 201


@item_bp.route('/favorite/remove', methods=['POST'])
def remove_favorite():
    """取消收藏"""
    data = request.json
    user_id = data.get('user_id')
    item_id = data.get('item_id')

    if not all([user_id, item_id]):
        return jsonify({'error': '缺少必要参数'}), 400

    favorite = Favorite.query.filter_by(user_id=user_id, item_id=item_id).first()
    if not favorite:
        return jsonify({'error': '未收藏该景点'}), 404

    db.session.delete(favorite)
    db.session.commit()

    return jsonify({'message': '已取消收藏'}), 200


@item_bp.route('/favorite/user/<int:user_id>', methods=['GET'])
def get_user_favorites(user_id):
    """获取用户的所有收藏"""
    favorites = Favorite.query.filter_by(user_id=user_id)\
        .order_by(Favorite.created_at.desc())\
        .all()

    favorite_list = []
    for favorite in favorites:
        item_info = recommender_service.get_item_info(favorite.item_id)
        if item_info:
            favorite_dict = favorite.to_dict()
            favorite_dict.update(item_info)
            favorite_list.append(favorite_dict)

    return jsonify({
        'user_id': user_id,
        'favorites': favorite_list,
        'count': len(favorite_list)
    }), 200
