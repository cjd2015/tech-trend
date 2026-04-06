import re
import json
from typing import List, Dict, Set
from collections import defaultdict
from rapidfuzz import fuzz
from sqlalchemy.orm import Session
from app.models.raw_signal import RawSignal, Topic, TopicEvidence
from app.core.database import get_db

class TopicAggregator:
    """主题聚合器：负责将原始信号聚合成主题"""

    def __init__(self, db: Session):
        self.db = db
        self.stop_words = {
            'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by',
            'is', 'are', 'was', 'were', 'be', 'been', 'being', 'have', 'has', 'had', 'do', 'does',
            'did', 'will', 'would', 'could', 'should', 'may', 'might', 'must', 'can', 'this',
            'that', 'these', 'those', 'i', 'you', 'he', 'she', 'it', 'we', 'they', 'me', 'him',
            'her', 'us', 'them', 'my', 'your', 'his', 'its', 'our', 'their', 'what', 'which',
            'who', 'when', 'where', 'why', 'how', 'all', 'any', 'both', 'each', 'few', 'more',
            'most', 'other', 'some', 'such', 'no', 'nor', 'not', 'only', 'own', 'same', 'so',
            'than', 'too', 'very', 'just', 'now', 'here', 'there', 'then', 'once', 'as', 'if'
        }

    def extract_keywords(self, text: str) -> List[str]:
        """从文本中提取关键词"""
        if not text:
            return []

        # 转换为小写
        text = text.lower()

        # 移除标点符号和特殊字符
        text = re.sub(r'[^\w\s]', ' ', text)

        # 分词
        words = text.split()

        # 移除停用词和短词
        keywords = []
        for word in words:
            if len(word) > 2 and word not in self.stop_words:
                # 移除常见技术前缀
                word = re.sub(r'^(using|build|create|develop|implement|design)', '', word).strip()
                if word and len(word) > 2:
                    keywords.append(word)

        # 提取名词短语（连续的非停用词）
        phrases = []
        current_phrase = []

        for word in words:
            if word not in self.stop_words and len(word) > 2:
                current_phrase.append(word)
            else:
                if len(current_phrase) >= 2:
                    phrases.append(' '.join(current_phrase))
                current_phrase = []

        if len(current_phrase) >= 2:
            phrases.append(' '.join(current_phrase))

        # 合并关键词和短语
        all_keywords = list(set(keywords + phrases))

        # 按重要性排序（这里简化处理，实际可以根据TF-IDF等算法）
        return sorted(all_keywords, key=len, reverse=True)[:10]  # 取前10个最长的关键词

    def normalize_topic_name(self, title: str) -> str:
        """规范化主题名称"""
        if not title:
            return "未知主题"

        # 移除常见前缀
        title = re.sub(r'^(Show HN|Ask HN|New|Using|Build|Create|Develop|Implement|Design):\s*', '', title, flags=re.IGNORECASE)

        # 移除特殊字符
        title = re.sub(r'[^\w\s]', ' ', title)

        # 规范化空格
        title = ' '.join(title.split())

        # 限制长度
        if len(title) > 100:
            title = title[:97] + "..."

        return title.strip() or "未知主题"

    def find_similar_topics(self, keywords: List[str], threshold: float = 0.5) -> List[Topic]:
        """查找相似的现有主题（跨维度）"""
        # 获取所有活跃主题，不限制维度
        existing_topics = self.db.query(Topic).filter(Topic.status.in_(['observed', 'candidate', 'validated'])).all()

        similar_topics = []
        for topic in existing_topics:
            topic_keywords = json.loads(topic.keywords or '[]')
            similarity_score = self.calculate_similarity(keywords, topic_keywords)
            if similarity_score >= threshold:
                similar_topics.append((topic, similarity_score))

        # 按相似度排序
        similar_topics.sort(key=lambda x: x[1], reverse=True)
        return [topic for topic, score in similar_topics]

    def calculate_similarity(self, keywords1: List[str], keywords2: List[str]) -> float:
        """计算两个关键词列表的相似度"""
        if not keywords1 or not keywords2:
            return 0.0

        total_score = 0.0
        matches = 0

        for kw1 in keywords1:
            best_score = 0.0
            for kw2 in keywords2:
                # 使用模糊匹配
                score = fuzz.ratio(kw1.lower(), kw2.lower()) / 100.0
                best_score = max(best_score, score)

            if best_score >= 0.6:  # 相似度阈值
                total_score += best_score
                matches += 1

        if matches == 0:
            return 0.0

        return total_score / len(keywords1)  # 平均相似度

    def create_or_update_topic(self, signal: RawSignal) -> Topic:
        """为信号创建或更新主题"""
        # 提取关键词
        text_to_analyze = f"{signal.title or ''} {signal.content or ''}"
        keywords = self.extract_keywords(text_to_analyze)

        # 规范化主题名称
        canonical_name = self.normalize_topic_name(signal.title or signal.content or "未知主题")

        # 查找相似主题
        similar_topics = self.find_similar_topics(keywords)

        if similar_topics:
            # 使用最相似的主题
            topic = similar_topics[0]

            # 更新主题的关键词
            existing_keywords = set(json.loads(topic.keywords or '[]'))
            existing_keywords.update(keywords)
            topic.keywords = json.dumps(list(existing_keywords))

            # 更新最后出现时间
            topic.last_seen_at = signal.fetched_at or topic.last_seen_at

        else:
            # 创建新主题
            topic = Topic(
                canonical_name=canonical_name,
                keywords=json.dumps(keywords),
                aliases=json.dumps([canonical_name]),
                status='observed',
                first_seen_at=signal.fetched_at,
                last_seen_at=signal.fetched_at
            )
            self.db.add(topic)
            self.db.flush()  # 获取ID

        # 创建证据关联
        evidence = TopicEvidence(
            topic_id=topic.id,
            raw_signal_id=signal.id,
            source_type=signal.source_type,
            weight=1.0,
            matched_by='keyword'
        )
        self.db.add(evidence)

        return topic

    def aggregate_topics(self, signals: List[RawSignal] = None) -> Dict[str, int]:
        """聚合主题的主函数 - 分两阶段：先创建，再合并"""
        if signals is None:
            # 获取最近未处理的信号
            from sqlalchemy import select
            processed_signal_ids = select(TopicEvidence.raw_signal_id)
            signals = self.db.query(RawSignal).filter(
                ~RawSignal.id.in_(processed_signal_ids)
            ).all()

        # 第一阶段：为每个信号创建独立的主题
        print(f"第一阶段：处理 {len(signals)} 个信号...")
        created_topics = []
        for signal in signals:
            try:
                topic = self.create_topic_for_signal(signal)
                created_topics.append(topic)
                print(f"  创建主题: {topic.canonical_name} (信号 {signal.id})")
            except Exception as e:
                print(f"处理信号 {signal.id} 时出错: {e}")
                continue

        # 提交第一阶段的更改，确保主题和证据都持久化
        self.db.commit()

        # 第二阶段：合并相似的主题
        print(f"第二阶段：合并 {len(created_topics)} 个主题...")
        merged_count = self.merge_similar_topics(created_topics)

        self.db.commit()
        return {
            "processed_signals": len(signals),
            "created_topics": len(created_topics),
            "merged_topics": merged_count
        }

    def create_topic_for_signal(self, signal: RawSignal) -> Topic:
        """为单个信号创建主题（不合并）"""
        # 提取关键词
        text_to_analyze = f"{signal.title or ''} {signal.content or ''}"
        keywords = self.extract_keywords(text_to_analyze)

        # 规范化主题名称
        canonical_name = self.normalize_topic_name(signal.title or signal.content or "未知主题")

        # 创建新主题
        topic = Topic(
            canonical_name=canonical_name,
            keywords=json.dumps(keywords),
            aliases=json.dumps([canonical_name]),
            status='observed',
            first_seen_at=signal.fetched_at,
            last_seen_at=signal.fetched_at
        )
        self.db.add(topic)
        self.db.flush()  # 获取ID

        # 创建证据关联
        evidence = TopicEvidence(
            topic_id=topic.id,
            raw_signal_id=signal.id,
            source_type=signal.source_type,
            weight=1.0,
            matched_by='keyword'
        )
        self.db.add(evidence)

        return topic

    def merge_similar_topics(self, topics: List[Topic]) -> int:
        """合并相似的主题"""
        merged_count = 0
        merged_ids = set()  # 已合并的主题ID

        # 对每个主题，查找是否有更相似的主题可以合并到
        for i, topic1 in enumerate(topics):
            if topic1.id in merged_ids:
                continue

            best_match = None
            best_similarity = 0.0

            # 查找最佳匹配
            for j, topic2 in enumerate(topics):
                if i == j or topic2.id in merged_ids:
                    continue

                keywords1 = set(json.loads(topic1.keywords or '[]'))
                keywords2 = set(json.loads(topic2.keywords or '[]'))
                similarity = self.calculate_similarity(list(keywords1), list(keywords2))

                if similarity >= 0.5 and similarity > best_similarity:
                    best_match = topic2
                    best_similarity = similarity

            # 如果找到匹配，合并topic2到topic1
            if best_match:
                print(f"  合并主题: {best_match.canonical_name} (ID:{best_match.id}) -> {topic1.canonical_name} (ID:{topic1.id}) (相似度: {best_similarity:.2f})")

                # 转移证据
                evidences_to_transfer = self.db.query(TopicEvidence).filter_by(topic_id=best_match.id).all()
                updated_count = 0
                for evidence in evidences_to_transfer:
                    evidence.topic_id = topic1.id
                    updated_count += 1
                
                self.db.flush()  # 立即刷新以确保更新生效
                print(f"    转移了 {updated_count} 条证据")
                
                # 合并关键词
                keywords1 = set(json.loads(topic1.keywords or '[]'))
                keywords2 = set(json.loads(best_match.keywords or '[]'))
                combined_keywords = keywords1.union(keywords2)
                topic1.keywords = json.dumps(list(combined_keywords))

                # 更新时间范围
                if best_match.first_seen_at and (not topic1.first_seen_at or best_match.first_seen_at < topic1.first_seen_at):
                    topic1.first_seen_at = best_match.first_seen_at
                if best_match.last_seen_at and (not topic1.last_seen_at or best_match.last_seen_at > topic1.last_seen_at):
                    topic1.last_seen_at = best_match.last_seen_at

                # 标记为已合并
                merged_ids.add(best_match.id)
                merged_count += 1

                # 合并关键词
                keywords1 = set(json.loads(topic1.keywords or '[]'))
                keywords2 = set(json.loads(best_match.keywords or '[]'))
                combined_keywords = keywords1.union(keywords2)
                topic1.keywords = json.dumps(list(combined_keywords))

                # 更新时间范围
                if best_match.first_seen_at and (not topic1.first_seen_at or best_match.first_seen_at < topic1.first_seen_at):
                    topic1.first_seen_at = best_match.first_seen_at
                if best_match.last_seen_at and (not topic1.last_seen_at or best_match.last_seen_at > topic1.last_seen_at):
                    topic1.last_seen_at = best_match.last_seen_at

                # 标记为已合并，不实际删除主题（避免外键约束问题）
                # best_match.status = 'merged'  # 可以添加一个合并状态
                merged_ids.add(best_match.id)
                merged_count += 1

                # 暂时不删除主题，避免外键问题
                # self.db.delete(best_match)

        return merged_count