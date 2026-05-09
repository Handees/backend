from sqlalchemy import update, inspect, Index, select, func, cast, String

from core import db
from .base import BaseModelPR, TimestampMixin
from .user_models import User


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
    commenter_id = db.Column(db.String, db.ForeignKey('user.user_id'))

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
    def get_all_by_user(cls, entity, sess, cursor=0, per_page=10):
        EntityClass = entity.__class__
        attr = inspect(EntityClass).primary_key[0]
        print("INcoming cursor", cursor)
        # cursor_cond = cls.id > cursor if cursor > 1 else cls.id >= cursor
        # cursor math
        num_partitions = 5  # corresponds to weight classes ( 1-5 )
        items_per_group = per_page // num_partitions
        start_rn = (cursor // num_partitions) + 1
        end_rn = start_rn + items_per_group - 1

        numbered_reviews = (
            select(
                cls.weight, cls.comment, cls.id,
                User.first_name, User.last_name, cls.created_at,
                func.row_number().over(
                    partition_by=cls.weight,
                    order_by=cls.id.desc()  # Order newest to oldest within the weight group
                ).label('rn')
            )
            .join(User, cls.commenter_id == User.user_id, isouter=True)
            .where(getattr(cls, attr.key) == getattr(entity, attr.key))
            .cte("numbered_reviews")
        )

        paged_subq = (
            select(numbered_reviews)
            .where(
                numbered_reviews.c.rn >= start_rn,
                numbered_reviews.c.rn <= end_rn
            )
            .cte("paged_cte")
        )
        subq = (
            select(
                paged_subq.c.weight,
                func.jsonb_agg(
                    func.jsonb_build_object(
                        'comment', paged_subq.c.comment,
                        'name', func.concat_ws(' ', paged_subq.c.first_name, paged_subq.c.last_name),
                        'created_at', cast(paged_subq.c.created_at, String)
                    )
                ).label("comments")
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
        result = sess.execute(select(stmt)).scalar()

        if result:
            # Check if any group actually returned comments in this batch
            has_comments_in_this_page = any(
                len(group_data.get('comments', [])) > 0
                for group_data in result.values()
            )
            if has_comments_in_this_page:
                next_cursor = cursor + per_page
                print(next_cursor, "out cursor")
            else:
                next_cursor = None   # Tell the UI to stop paginating

            return {"reviews": result, "cursor": next_cursor}

        return {"reviews": {}, "cursor": None}
