from sqlalchemy import update, inspect, Index, select, func, cast, String

from core import db
from .base import BaseModelPR, TimestampMixin


class Reviews(TimestampMixin, BaseModelPR, db.Model):
    __table_args__ = (
        Index('ix_user_rating_weight', 'user_id', 'weight'),
        Index('ix_artisan_rating_weight', 'artisan_id', 'weight'),
    )
    weight = db.Column(db.Integer, default=0)
    comment = db.Column(db.Text)
    user_id = db.Column(db.String, db.ForeignKey('user.user_id'))
    artisan_id = db.Column(db.String, db.ForeignKey('artisan.artisan_id'))
    booking_id = db.Column(db.String, db.ForeignKey('booking.booking_id'))

    def update_sum_on_entity(self):
        with db.session() as sess:
            entity = self.user or self.artisan
            EntityClass = entity.__class__
            attr = inspect(EntityClass).primary_key[0]
            # perform atomic update
            stmt = update(
                EntityClass
            ).where(
                attr == getattr(entity, attr.key)
            ).values(
                ratings_weighted_sum=EntityClass.ratings_weighted_sum + self.weight,
                no_of_ratings=EntityClass.no_of_ratings + 1
            )
            sess.execute(stmt)
            sess.commit()

    @classmethod
    def get_all_by_user(cls, entity, sess, cursor=1, per_page=10):
        EntityClass = entity.__class__
        attr = inspect(EntityClass).primary_key[0]
        cursor_cond = cls.id > cursor if cursor > 1 else cls.id >= cursor
        paged_subq = (
            select(
                cls.weight, cls.comment, cls.id
            )
            .where(
                getattr(cls, attr.key) == getattr(entity, attr.key),
                cursor_cond
            )
            .order_by(cls.id)
            .limit(per_page)
            .cte("paged_cte")
        )
        subq = (
            select(
                paged_subq.c.weight,
                func.jsonb_agg(paged_subq.c.comment).label("comments")
            )
            .group_by(paged_subq.c.weight)
            .subquery()
        )
        weights_count_subq = (
            select(
                cls.weight, func.count(cls.weight).label("count")
            ).where(
                getattr(cls, attr.key) == getattr(entity, attr.key)
            )
            .group_by(cls.weight)
            .subquery()
        )
        stmt = (
            select(
                func.jsonb_object_agg(
                    cast(weights_count_subq.c.weight, String),
                    func.jsonb_build_object(
                        'comments',
                        func.coalesce(
                            subq.c.comments,
                            cast([], type_=db.JSON)
                        ),
                        'total_count', weights_count_subq.c.count
                    )
                )
            )
            .select_from(weights_count_subq)
            .join(
                subq,
                weights_count_subq.c.weight == subq.c.weight,
                isouter=True
            )
            .scalar_subquery()
        )
        next_cursor_col = select(func.max(paged_subq.c.id)).scalar_subquery()
        result = sess.execute(select(stmt, next_cursor_col)).first()

        if result:
            data, last_id = result
            return {"reviews": data or {}, "cursor": last_id}

        return {"reviews": {}, "cursor": None}
