"""
Centralized Notifications API Routes.
Exposes endpoints for users to view, manage, and mark notifications as read:
- GET /api/notifications (List user notifications)
- GET /api/notifications/unread-count (Unread badge count)
- PUT /api/notifications/<id>/read (Mark single notification as read)
- PUT /api/notifications/read-all (Mark all as read)
- DELETE /api/notifications/<id> (Dismiss notification)
"""
from flask import Blueprint, request
from backend.extensions import db
from backend.models.notification import Notification
from backend.utils.auth import token_required
from backend.utils.response import api_response, error_response

notifications_bp = Blueprint("notifications", __name__, url_prefix="/api/notifications")


@notifications_bp.route("", methods=["GET"])
@token_required
def list_user_notifications(current_user):
    """
    Retrieves the authenticated user's notifications.
    Supports filtering by unread_only=true and pagination.
    """
    unread_only = request.args.get("unread_only", "false").lower() == "true"
    limit = min(int(request.args.get("limit", 50)), 100)
    offset = int(request.args.get("offset", 0))

    query = Notification.query.filter_by(user_id=current_user.id)
    if unread_only:
        query = query.filter_by(is_read=False)

    total_count = query.count()
    unread_count = Notification.query.filter_by(user_id=current_user.id, is_read=False).count()

    notifications = query.order_by(Notification.created_at.desc()).offset(offset).limit(limit).all()

    return api_response(
        message="Notifications retrieved successfully.",
        data={
            "total": total_count,
            "unread_count": unread_count,
            "notifications": [n.to_dict() for n in notifications]
        },
        status_code=200
    )


@notifications_bp.route("/unread-count", methods=["GET"])
@token_required
def get_unread_count(current_user):
    """
    Fast lookup for real-time notification badge rendering.
    """
    count = Notification.query.filter_by(user_id=current_user.id, is_read=False).count()
    return api_response(
        message="Unread notification count retrieved.",
        data={"unread_count": count},
        status_code=200
    )


@notifications_bp.route("/<int:notification_id>/read", methods=["PUT"])
@token_required
def mark_notification_read(current_user, notification_id):
    """
    Marks a single notification as read.
    """
    notif = Notification.query.filter_by(id=notification_id, user_id=current_user.id).first()
    if not notif:
        return error_response("Notification not found.", 404)

    notif.is_read = True
    db.session.commit()

    unread_count = Notification.query.filter_by(user_id=current_user.id, is_read=False).count()

    return api_response(
        message="Notification marked as read.",
        data={"notification": notif.to_dict(), "unread_count": unread_count},
        status_code=200
    )


@notifications_bp.route("/read-all", methods=["PUT"])
@token_required
def mark_all_notifications_read(current_user):
    """
    Marks all notifications for the current user as read.
    """
    updated_count = Notification.query.filter_by(
        user_id=current_user.id, is_read=False
    ).update({"is_read": True})
    db.session.commit()

    return api_response(
        message=f"Marked {updated_count} notifications as read.",
        data={"unread_count": 0, "marked_count": updated_count},
        status_code=200
    )


@notifications_bp.route("/<int:notification_id>", methods=["DELETE"])
@token_required
def delete_notification(current_user, notification_id):
    """
    Dismisses and permanently deletes a notification.
    """
    notif = Notification.query.filter_by(id=notification_id, user_id=current_user.id).first()
    if not notif:
        return error_response("Notification not found.", 404)

    db.session.delete(notif)
    db.session.commit()

    return api_response(
        message="Notification dismissed successfully.",
        status_code=200
    )
