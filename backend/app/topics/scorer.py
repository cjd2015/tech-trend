import json
from datetime import datetime, timedelta
from typing import Dict, List
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.models.raw_signal import Topic, TopicEvidence, RawSignal

class TopicScorer:
    """主题评分器：计算多维度评分"""

    def __init__(self, db: Session):
        self.db = db

    def calculate_topic_scores(self, topic: Topic) -> Dict[str, float]:
        """计算主题的完整评分"""
        # 获取主题的所有证据
        evidences = self.db.query(TopicEvidence).filter_by(topic_id=topic.id).all()

        # 按来源类型分组证据
        evidence_by_type = {}
        for evidence in evidences:
            if evidence.source_type not in evidence_by_type:
                evidence_by_type[evidence.source_type] = []
            evidence_by_type[evidence.source_type].append(evidence)

        # 计算各维度分数
        scores = {
            'community_score': self._calculate_community_score(evidence_by_type.get('community', [])),
            'research_score': self._calculate_research_score(evidence_by_type.get('research', [])),
            'industry_score': self._calculate_industry_score(evidence_by_type.get('industry', [])),
            'knowledge_score': self._calculate_knowledge_score(evidence_by_type.get('knowledge', [])),
            'cross_signal_score': self._calculate_cross_signal_score(evidence_by_type),
            'novelty_score': self._calculate_novelty_score(topic),
            'momentum_score': self._calculate_momentum_score(topic, evidences)
        }

        # 计算最终分数
        scores['final_score'] = self._calculate_final_score(scores)

        return scores

    def _calculate_community_score(self, evidences: List[TopicEvidence]) -> float:
        """计算社区维度分数（基于HN）"""
        if not evidences:
            return 0.0

        total_score = 0.0
        for evidence in evidences:
            signal = evidence.raw_signal
            # 从metadata中获取HN特有的指标
            metadata = json.loads(signal.metadata_json or '{}')

            # HN评分算法：基础分数 + 评论数权重 + 时间衰减
            base_score = metadata.get('score', 0)
            comments = metadata.get('descendants', 0)
            hours_old = (datetime.utcnow() - (signal.published_at or signal.fetched_at)).total_seconds() / 3600

            # 时间衰减因子（越新越重要）
            time_factor = max(0.1, 1.0 / (1.0 + hours_old / 24.0))

            # 计算单个信号的分数
            signal_score = (base_score * 0.6 + comments * 0.4) * time_factor
            total_score += signal_score * evidence.weight

        return min(total_score, 100.0)  # 限制最大分数

    def _calculate_research_score(self, evidences: List[TopicEvidence]) -> float:
        """计算学术维度分数（基于arXiv）"""
        if not evidences:
            return 0.0

        total_score = 0.0
        recent_papers = 0

        for evidence in evidences:
            signal = evidence.raw_signal
            metadata = json.loads(signal.metadata_json or '{}')

            # arXiv评分：论文数量 + 近期发表权重
            days_old = (datetime.utcnow() - (signal.published_at or signal.fetched_at)).days

            if days_old <= 30:
                recent_papers += 1

            # 基础分数基于论文质量指标
            base_score = 1.0  # 每篇论文的基础分
            total_score += base_score * evidence.weight

        # 近期论文加成
        recency_bonus = min(recent_papers * 0.5, 5.0)
        total_score += recency_bonus

        return min(total_score, 50.0)  # arXiv通常论文数量不会太多

    def _calculate_industry_score(self, evidences: List[TopicEvidence]) -> float:
        """计算产业维度分数（基于专利）"""
        if not evidences:
            return 0.0

        total_score = 0.0
        unique_applicants = set()

        for evidence in evidences:
            signal = evidence.raw_signal
            metadata = json.loads(signal.metadata_json or '{}')

            # 专利评分：申请人多样性 + 技术领域重要性
            applicant = metadata.get('applicant', signal.author or 'unknown')
            unique_applicants.add(applicant)

            # 基础分数
            base_score = 2.0  # 每项专利的基础分
            total_score += base_score * evidence.weight

        # 申请人多样性加成（不同公司申请说明产业关注度高）
        diversity_bonus = len(unique_applicants) * 0.5
        total_score += diversity_bonus

        return min(total_score, 40.0)

    def _calculate_knowledge_score(self, evidences: List[TopicEvidence]) -> float:
        """计算知识维度分数（基于技术书籍）"""
        if not evidences:
            return 0.0

        total_score = 0.0
        publishers = set()

        for evidence in evidences:
            signal = evidence.raw_signal
            metadata = json.loads(signal.metadata_json or '{}')

            # 书籍评分：出版社权重 + 出版时间
            publisher = metadata.get('publisher', 'unknown')
            publishers.add(publisher)

            # 知名出版社加成
            prestige_publishers = {'oreilly', 'manning', 'packt', 'apress', 'addison-wesley'}
            publisher_bonus = 1.5 if publisher.lower() in prestige_publishers else 1.0

            base_score = 1.0 * publisher_bonus
            total_score += base_score * evidence.weight

        return min(total_score, 20.0)  # 书籍数量通常不会太多

    def _calculate_cross_signal_score(self, evidence_by_type: Dict[str, List]) -> float:
        """计算交叉信号分数（维度覆盖度）"""
        covered_dimensions = len([evidences for evidences in evidence_by_type.values() if evidences])

        # 基础分数：每个维度的覆盖
        base_score = covered_dimensions * 5.0

        # 密度加成：同一维度内多个信号
        density_bonus = 0.0
        for evidences in evidence_by_type.values():
            if len(evidences) > 1:
                density_bonus += (len(evidences) - 1) * 2.0

        return min(base_score + density_bonus, 30.0)

    def _calculate_novelty_score(self, topic: Topic) -> float:
        """计算新颖性分数"""
        # 检查是否是新出现的主题
        days_since_first_seen = (datetime.utcnow() - topic.first_seen_at).days

        if days_since_first_seen <= 7:
            return 10.0  # 新主题高分
        elif days_since_first_seen <= 30:
            return 5.0   # 相对较新
        else:
            return 0.0   # 老主题

    def _calculate_momentum_score(self, topic: Topic, evidences: List[TopicEvidence]) -> float:
        """计算动量分数（近期活跃度）"""
        # 检查最近7天内的证据数量
        week_ago = datetime.utcnow() - timedelta(days=7)
        recent_evidences = [e for e in evidences if e.created_at >= week_ago]

        momentum = len(recent_evidences) * 3.0

        # 时间分布加成（持续活跃比一次性爆发更好）
        if len(recent_evidences) >= 3:
            momentum += 5.0

        return min(momentum, 20.0)

    def _calculate_final_score(self, scores: Dict[str, float]) -> float:
        """计算最终综合分数"""
        # 权重配置
        weights = {
            'community_score': 0.25,
            'research_score': 0.25,
            'industry_score': 0.20,
            'knowledge_score': 0.15,
            'cross_signal_score': 0.10,
            'novelty_score': 0.03,
            'momentum_score': 0.02
        }

        final_score = sum(scores[key] * weights[key] for key in weights)
        return round(final_score, 2)

    def update_topic_scores(self, topic_id: int = None) -> Dict[str, int]:
        """更新主题评分"""
        query = self.db.query(Topic)
        if topic_id:
            query = query.filter_by(id=topic_id)

        topics = query.all()
        updated_count = 0

        for topic in topics:
            scores = self.calculate_topic_scores(topic)

            # 更新数据库
            for key, value in scores.items():
                setattr(topic, key, value)

            updated_count += 1

        self.db.commit()
        return {"updated_topics": updated_count}