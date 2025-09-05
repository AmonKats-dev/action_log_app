class ActionLogComment(Base):
    __tablename__ = "action_log_comments"

    id = Column(Integer, primary_key=True, index=True)
    action_log_id = Column(Integer, ForeignKey("action_logs.id"))
    user_id = Column(Integer, ForeignKey("users.id"))
    comment = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    status = Column(String, nullable=True)
    is_approved = Column(Boolean, default=False)
    is_viewed = Column(Boolean, default=False)
    parent_id = Column(Integer, ForeignKey("action_log_comments.id"), nullable=True)

    # Relationships
    action_log = relationship("ActionLog", back_populates="comments")
    user = relationship("User", back_populates="action_log_comments")
    replies = relationship("ActionLogComment", backref=backref("parent", remote_side=[id])) 