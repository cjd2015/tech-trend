from typing import Dict, List

from sqlalchemy.orm import Session

from app.models.raw_signal import Topic
from app.topics.reviewer import TopicAutoReviewer
from app.topics.scorer import TopicScorer

class TopicClassifier:
    """主题分类器：根据评分决定主题状态"""

    def __init__(self, db: Session):
        self.db = db
        self.scorer = TopicScorer(db)
        self.reviewer = TopicAutoReviewer(db)

    def classify_topics(self, topic_ids: List[int] = None) -> Dict[str, int]:
        """分类主题状态"""
        query = self.db.query(Topic)
        if topic_ids:
            query = query.filter(Topic.id.in_(topic_ids))

        topics = query.all()
        status_changes = {
            'promoted_to_candidate': 0,
            'promoted_to_validated': 0,
            'promoted_to_recorded': 0,
            'demoted': 0,
            'reviewed': 0,
            'useful': 0,
            'reference': 0,
            'discarded': 0,
            'stored': 0,
            'removed': 0,
        }
        review_topic_ids = []

        for topic in topics:
            new_status = self._determine_status(topic)

            if new_status != topic.status:
                old_status = topic.status
                topic.status = new_status

                # 记录状态变化
                if self._is_promotion(old_status, new_status):
                    if new_status == 'candidate':
                        status_changes['promoted_to_candidate'] += 1
                    elif new_status == 'validated':
                        status_changes['promoted_to_validated'] += 1
                else:
                    status_changes['demoted'] += 1

            if topic.status in {'candidate', 'validated', 'recorded', 'discarded'}:
                review_topic_ids.append(topic.id)

        self.db.commit()

        review_result = self.reviewer.review_topics(review_topic_ids)
        status_changes['reviewed'] = review_result['reviewed']
        status_changes['useful'] = review_result['useful']
        status_changes['reference'] = review_result['reference']
        status_changes['discarded'] = review_result['discarded']
        status_changes['stored'] = review_result['stored']
        status_changes['removed'] = review_result['removed']
        status_changes['promoted_to_recorded'] = review_result['useful']

        return status_changes

    def _determine_status(self, topic: Topic) -> str:
        """根据评分确定主题状态"""
        # 确保评分是最新的
        if not hasattr(topic, 'final_score') or topic.final_score is None:
            scores = self.scorer.calculate_topic_scores(topic)
            for key, value in scores.items():
                setattr(topic, key, value)

        score = topic.final_score
        cross_signals = topic.cross_signal_score

        # 状态判定规则
        if score >= 15.0 and cross_signals >= 10.0:  # 中高分且中等覆盖
            return 'validated'
        elif score >= 8.0 or cross_signals >= 5.0:  # 基础分数或单一维度覆盖
            return 'candidate'
        else:
            return 'observed'

    def _is_promotion(self, old_status: str, new_status: str) -> bool:
        """判断是否是状态晋升"""
        status_order = {'discarded': 0, 'observed': 1, 'candidate': 2, 'validated': 3, 'recorded': 4}
        return status_order.get(new_status, 0) > status_order.get(old_status, 0)
