from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from backend.database.models import ActionLogComment, User
from backend.database.database import get_db
from backend.utils.auth import get_current_user
from typing import List

router = APIRouter(prefix="/action-logs", tags=["action-logs"])

@router.get("/{log_id}/comments")
async def get_comments(
    log_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get all comments for a log."""
    try:
        # Get all comments for the log
        comments = db.query(ActionLogComment).filter(
            ActionLogComment.action_log_id == log_id,
            ActionLogComment.parent_id == None  # Get only top-level comments
        ).all()
        
        # Get all replies for these comments
        for comment in comments:
            comment.replies = db.query(ActionLogComment).filter(
                ActionLogComment.parent_id == comment.id
            ).all()
        
        return comments
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{log_id}/mark-comments-viewed")
async def mark_comments_viewed(
    log_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Mark all comments for a log as viewed by the current user."""
    try:
        # Get all comments for the log
        comments = db.query(ActionLogComment).filter(
            ActionLogComment.action_log_id == log_id
        ).all()
        
        # Mark each comment as viewed
        for comment in comments:
            comment.is_viewed = True
            if comment.replies:
                for reply in comment.replies:
                    reply.is_viewed = True
        
        db.commit()
        return {"message": "Comments marked as viewed"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e)) 