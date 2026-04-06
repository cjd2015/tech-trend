#!/usr/bin/env python3
"""
主题聚合和评分管道测试脚本
测试完整的主题发现、聚合、评分和记录流程
"""

import asyncio
import sys
from pathlib import Path

# 添加backend路径
backend_dir = Path(__file__).resolve().parent / "backend"
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from sqlalchemy.orm import sessionmaker
from app.core.database import engine
from app.topics.aggregator import TopicAggregator
from app.topics.scorer import TopicScorer
from app.topics.classifier import TopicClassifier
from app.topics.record_manager import RecordManager
from app.models.raw_signal import RawSignal, Topic, Record

def test_topic_pipeline():
    """测试完整的主题处理管道"""
    print("🚀 开始测试主题聚合和评分管道...")

    # 创建数据库会话
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()

    try:
        # 1. 检查现有信号
        signal_count = db.query(RawSignal).count()
        print(f"📊 当前数据库中有 {signal_count} 个原始信号")

        if signal_count == 0:
            print("⚠️  没有原始信号，跳过聚合测试")
            return

        # 2. 执行主题聚合
        print("\n🔄 执行主题聚合...")
        aggregator = TopicAggregator(db)
        agg_result = aggregator.aggregate_topics()
        print(f"✅ 聚合完成: 处理了 {agg_result['processed_signals']} 个信号")

        # 3. 计算评分
        print("\n📈 计算主题评分...")
        scorer = TopicScorer(db)
        score_result = scorer.update_topic_scores()
        print(f"✅ 评分完成: 更新了 {score_result['updated_topics']} 个主题的评分")

        # 4. 分类主题状态
        print("\n🏷️  分类主题状态...")
        classifier = TopicClassifier(db)
        class_result = classifier.classify_topics()
        print(
            "✅ 分类完成: "
            f"晋升候选 {class_result['promoted_to_candidate']} 个, "
            f"验证 {class_result['promoted_to_validated']} 个, "
            f"自动入库 {class_result['promoted_to_recorded']} 个, "
            f"参考 {class_result['reference']} 个, "
            f"废弃 {class_result['discarded']} 个"
        )

        # 5. 检查结果
        print("\n📋 检查结果...")

        # 主题统计
        topic_stats = {}
        topics = db.query(Topic).all()
        for topic in topics:
            topic_stats[topic.status] = topic_stats.get(topic.status, 0) + 1

        print("主题状态分布:")
        for status, count in topic_stats.items():
            print(f"  {status}: {count} 个")

        # 记录统计
        record_count = db.query(Record).count()
        print(f"\n总记录数: {record_count} 个")

        if record_count > 0:
            records = db.query(Record).limit(5).all()
            print("\n最新记录示例:")
            for record in records:
                print(f"  📝 {record.title} (置信度: {record.confidence:.2f})")
                print(f"     原因: {record.record_reason}")

        # 6. 验证数据完整性
        print("\n🔍 验证数据完整性...")
        issues = []

        # 检查是否有评分缺失的主题
        unscored_topics = db.query(Topic).filter(Topic.final_score.is_(None)).count()
        if unscored_topics > 0:
            issues.append(f"{unscored_topics} 个主题缺少评分")

        # 检查是否有未分类的主题
        unclassified_topics = db.query(Topic).filter(Topic.status.is_(None)).count()
        if unclassified_topics > 0:
            issues.append(f"{unclassified_topics} 个主题未分类")

        # 检查记录和主题的关联
        orphaned_records = db.query(Record).filter(~Record.topic_id.in_(
            db.query(Topic.id)
        )).count()
        if orphaned_records > 0:
            issues.append(f"{orphaned_records} 个记录缺少对应的主题")

        if issues:
            print("⚠️  发现问题:")
            for issue in issues:
                print(f"  - {issue}")
        else:
            print("✅ 数据完整性检查通过")

        print("\n🎉 主题聚合和评分管道测试完成！")

    except Exception as e:
        print(f"❌ 测试失败: {str(e)}")
        import traceback
        traceback.print_exc()

    finally:
        db.close()

if __name__ == "__main__":
    test_topic_pipeline()
