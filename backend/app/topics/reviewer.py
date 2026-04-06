import json
import re
from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from app.models.raw_signal import Record, Topic


class TopicAutoReviewer:
    """自动审核器：根据规则评估主题是否值得入库。"""

    SCORE_WEIGHTS = {
        "timeliness": 0.20,
        "credibility": 0.25,
        "accuracy": 0.30,
        "practicality": 0.25,
    }

    SOURCE_PROFILES = {
        "hacker_news": {
            "credibility": 3.1,
            "source_type": "社区论坛",
            "author_background": "普通用户",
            "commercial_bias": False,
        },
        "github_trending": {
            "credibility": 4.1,
            "source_type": "代码托管平台",
            "author_background": "资深开发者",
            "commercial_bias": False,
        },
        "stackoverflow": {
            "credibility": 4.3,
            "source_type": "问答平台",
            "author_background": "资深开发者",
            "commercial_bias": False,
        },
        "devto": {
            "credibility": 3.4,
            "source_type": "技术博客",
            "author_background": "资深开发者",
            "commercial_bias": False,
        },
        "producthunt": {
            "credibility": 2.8,
            "source_type": "社区论坛",
            "author_background": "未知",
            "commercial_bias": True,
        },
        "techcrunch": {
            "credibility": 3.5,
            "source_type": "科技媒体",
            "author_background": "资深开发者",
            "commercial_bias": False,
        },
        "reddit_tech": {
            "credibility": 2.4,
            "source_type": "社区论坛",
            "author_background": "普通用户",
            "commercial_bias": False,
        },
        "arxiv": {
            "credibility": 4.8,
            "source_type": "官方文档",
            "author_background": "官方团队",
            "commercial_bias": False,
        },
        "patent": {
            "credibility": 4.6,
            "source_type": "官方文档",
            "author_background": "官方团队",
            "commercial_bias": False,
        },
        "technical_book": {
            "credibility": 4.2,
            "source_type": "技术博客",
            "author_background": "资深开发者",
            "commercial_bias": False,
        },
    }

    HIGH_FREQUENCY_SOURCES = {
        "hacker_news",
        "github_trending",
        "stackoverflow",
        "devto",
        "producthunt",
        "techcrunch",
        "reddit_tech",
    }
    MEDIUM_FREQUENCY_SOURCES = {"arxiv", "patent"}
    LOW_FREQUENCY_SOURCES = {"technical_book"}

    VERSION_PATTERNS = [
        re.compile(r"\b(?:python|node(?:\.js)?|react|vue|angular|go|rust|java|kubernetes|docker|postgresql|redis)\s+\d+(?:\.\d+){0,2}\+?\b", re.IGNORECASE),
        re.compile(r"\bv?\d+(?:\.\d+){1,3}\b", re.IGNORECASE),
    ]

    CODE_HINTS = [
        "```",
        "pip install",
        "npm install",
        "pnpm add",
        "yarn add",
        "docker run",
        "docker compose",
        "kubectl",
        "python -m",
        "uvicorn",
        "git clone",
        "curl ",
    ]

    ACTIONABLE_KEYWORDS = [
        "how to",
        "guide",
        "tutorial",
        "build",
        "deploy",
        "setup",
        "benchmark",
        "performance",
        "issue",
        "problem",
        "release",
        "api",
        "tool",
        "library",
        "framework",
        "database",
        "server",
        "agent",
        "copilot",
    ]

    WARNING_KEYWORDS = [
        "warning",
        "caution",
        "risk",
        "danger",
        "注意",
        "风险",
        "警告",
        "limitation",
    ]

    ERROR_HANDLING_KEYWORDS = [
        "error",
        "exception",
        "troubleshoot",
        "fallback",
        "retry",
        "debug",
        "排查",
        "报错",
        "失败",
    ]

    PROMOTION_KEYWORDS = [
        "sponsor",
        "sponsored",
        "promo",
        "advertisement",
        "launch",
        "growth hack",
    ]

    SECURITY_RISK_RULES = {
        "修改系统配置": [
            "sysctl",
            "registry",
            "group policy",
            "systemctl",
            "launchctl",
            "hosts file",
            "kernel parameter",
        ],
        "执行未知脚本": [
            "curl | sh",
            "wget | sh",
            "bash -c",
            "sh -c",
            "powershell -executionpolicy bypass",
            "iwr ",
        ],
        "暴露密钥": [
            "api key",
            "access token",
            "secret key",
            "private key",
            "aws_secret",
            "token=",
            "password=",
        ],
    }

    REVERSE_ENGINEERING_KEYWORDS = [
        "crack",
        "keygen",
        "jailbreak",
        "reverse engineer",
        "逆向",
        "破解",
        "bypass drm",
    ]

    LICENSE_KEYWORDS = [
        "mit license",
        "apache license",
        "bsd license",
        "gpl",
        "mpl",
        "license",
        "许可证",
    ]

    def __init__(self, db: Session):
        self.db = db

    def review_topics(self, topic_ids: Optional[List[int]] = None) -> Dict[str, int]:
        """批量执行自动审核，并按规则同步记录库。"""
        query = self.db.query(Topic)
        if topic_ids:
            query = query.filter(Topic.id.in_(topic_ids))

        topics = query.all()
        result = {
            "reviewed": 0,
            "useful": 0,
            "reference": 0,
            "discarded": 0,
            "stored": 0,
            "removed": 0,
        }

        for topic in topics:
            if topic.status == "observed":
                continue

            report = self.review_topic(topic)
            sync_result = self.apply_review(topic, report)

            result["reviewed"] += 1
            result[report["conclusion"]] += 1
            result["stored"] += sync_result["stored"]
            result["removed"] += sync_result["removed"]

        self.db.commit()
        return result

    def review_topic(self, topic: Topic) -> Dict[str, Any]:
        """生成单个主题的审核报告。"""
        evidences = list(topic.topic_evidences)
        signals = [evidence.raw_signal for evidence in evidences if evidence.raw_signal]
        combined_text = self._build_combined_text(topic, signals)

        timeliness = self._evaluate_timeliness(signals)
        credibility = self._evaluate_credibility(signals, combined_text)
        accuracy = self._evaluate_accuracy(signals, topic, combined_text)
        practicality = self._evaluate_practicality(signals, topic, combined_text)
        security = self._evaluate_security(combined_text)
        compliance = self._evaluate_compliance(combined_text, signals)

        weighted_total = round(
            timeliness["score"] * self.SCORE_WEIGHTS["timeliness"]
            + credibility["score"] * self.SCORE_WEIGHTS["credibility"]
            + accuracy["score"] * self.SCORE_WEIGHTS["accuracy"]
            + practicality["score"] * self.SCORE_WEIGHTS["practicality"],
            2,
        )

        conclusion = self._determine_conclusion(
            weighted_total=weighted_total,
            timeliness_score=timeliness["score"],
            credibility_score=credibility["score"],
            accuracy_score=accuracy["score"],
            practicality_score=practicality["score"],
            security=security,
            compliance=compliance,
        )

        summary = self._build_summary(
            weighted_total=weighted_total,
            conclusion=conclusion,
            timeliness=timeliness,
            credibility=credibility,
            accuracy=accuracy,
            practicality=practicality,
            security=security,
            compliance=compliance,
        )

        return {
            "timeliness": timeliness,
            "credibility": credibility,
            "accuracy": accuracy,
            "practicality": practicality,
            "security": security,
            "compliance": compliance,
            "weighted_total": weighted_total,
            "conclusion": conclusion,
            "store": conclusion == "useful",
            "summary": summary,
        }

    def apply_review(self, topic: Topic, report: Dict[str, Any]) -> Dict[str, int]:
        """根据审核结果同步 topic 状态和 records。"""
        existing_record = self.db.query(Record).filter(Record.topic_id == topic.id).first()
        result = {"stored": 0, "removed": 0}

        if report["store"]:
            if existing_record:
                existing_record.title = topic.canonical_name
                existing_record.summary = self._build_record_summary(topic, report)
                existing_record.record_reason = report["summary"]
                existing_record.evidence_count = len(topic.topic_evidences)
                existing_record.confidence = min(report["weighted_total"] / 5.0, 1.0)
                existing_record.review_status = "useful"
            else:
                record = Record(
                    topic_id=topic.id,
                    title=topic.canonical_name,
                    summary=self._build_record_summary(topic, report),
                    record_reason=report["summary"],
                    evidence_count=len(topic.topic_evidences),
                    confidence=min(report["weighted_total"] / 5.0, 1.0),
                    review_status="useful",
                )
                self.db.add(record)
                result["stored"] += 1

            topic.status = "recorded"
            return result

        if existing_record:
            self.db.delete(existing_record)
            result["removed"] += 1

        topic.status = "discarded"
        return result

    def _evaluate_timeliness(self, signals: List[Any]) -> Dict[str, Any]:
        latest = self._get_latest_signal_time(signals)
        source_names = {signal.source_name for signal in signals if getattr(signal, "source_name", None)}
        frequency_key, frequency_label = self._determine_frequency(source_names)
        days_old = (datetime.utcnow() - latest).days if latest else 9999

        if frequency_key == "high":
            thresholds = [(7, 5.0), (30, 4.0), (90, 3.0), (180, 2.0)]
        elif frequency_key == "medium":
            thresholds = [(30, 5.0), (90, 4.0), (180, 3.0), (365, 2.0)]
        else:
            thresholds = [(180, 5.0), (365, 4.0), (730, 3.0), (1825, 2.0)]

        score = 1.0
        for threshold, threshold_score in thresholds:
            if days_old <= threshold:
                score = threshold_score
                break

        applicable = score >= 3.0
        return {
            "score": score,
            "published_at": latest.isoformat() if latest else None,
            "update_frequency": frequency_label,
            "applicable": applicable,
            "judgement": "仍适用于当前技术环境" if applicable else "时效性偏弱，建议谨慎采用",
        }

    def _evaluate_credibility(self, signals: List[Any], combined_text: str) -> Dict[str, Any]:
        profiles = [self._get_source_profile(signal.source_name) for signal in signals]
        if not profiles:
            base_score = 2.0
            source_types = ["未知"]
            author_background = "未知"
            interest_related = False
        else:
            base_score = sum(profile["credibility"] for profile in profiles) / len(profiles)
            source_types = sorted({profile["source_type"] for profile in profiles})
            author_background = self._most_common([profile["author_background"] for profile in profiles]) or "未知"
            interest_related = any(profile["commercial_bias"] for profile in profiles)

        if len({signal.source_type for signal in signals}) >= 2:
            base_score += 0.2
        if self._contains_keywords(combined_text, self.PROMOTION_KEYWORDS):
            base_score -= 0.6
            interest_related = True

        score = round(self._clamp(base_score, 1.0, 5.0), 1)
        return {
            "score": score,
            "source_type": " / ".join(source_types),
            "author_background": author_background,
            "interest_related": interest_related,
        }

    def _evaluate_accuracy(self, signals: List[Any], topic: Topic, combined_text: str) -> Dict[str, Any]:
        version_explicit = any(pattern.search(combined_text) for pattern in self.VERSION_PATTERNS)
        code_level = self._detect_code_completeness(combined_text)
        authoritative_sources = {
            signal.source_name
            for signal in signals
            if signal.source_name in {"arxiv", "patent", "technical_book", "stackoverflow", "github_trending"}
        }
        dimensions = {signal.source_type for signal in signals}

        if len(dimensions) >= 3 or (len(dimensions) >= 2 and authoritative_sources):
            alignment = "一致"
            alignment_bonus = 1.6
        elif len(dimensions) >= 2 or authoritative_sources:
            alignment = "未提及"
            alignment_bonus = 0.9
        else:
            alignment = "有偏差"
            alignment_bonus = 0.3

        score = 1.2
        score += 1.0 if version_explicit else 0.3
        score += {"完整可运行": 1.2, "片段需补全": 0.7, "明显错误或未提供": 0.2}[code_level]
        score += alignment_bonus
        score += 0.4 if topic.cross_signal_score and topic.cross_signal_score >= 10 else 0.0

        return {
            "score": round(self._clamp(score, 1.0, 5.0), 1),
            "version_explicit": version_explicit,
            "code_completeness": code_level,
            "official_alignment": alignment,
        }

    def _evaluate_practicality(self, signals: List[Any], topic: Topic, combined_text: str) -> Dict[str, Any]:
        content_lengths = [len((signal.content or "").strip()) for signal in signals]
        avg_length = sum(content_lengths) / len(content_lengths) if content_lengths else 0
        specific_problem = self._contains_keywords(combined_text, self.ACTIONABLE_KEYWORDS) or topic.final_score >= 10

        if avg_length >= 180 or self._detect_code_completeness(combined_text) == "完整可运行":
            clarity = "详细可复现"
            clarity_bonus = 1.5
        elif avg_length >= 80:
            clarity = "大致可行"
            clarity_bonus = 1.0
        else:
            clarity = "过于简略"
            clarity_bonus = 0.4

        has_error_handling = self._contains_keywords(combined_text, self.ERROR_HANDLING_KEYWORDS + self.WARNING_KEYWORDS)
        score = 1.1
        score += 1.3 if specific_problem else 0.4
        score += clarity_bonus
        score += 0.7 if has_error_handling else 0.2
        score += 0.5 if len({signal.source_type for signal in signals}) >= 2 else 0.0

        return {
            "score": round(self._clamp(score, 1.0, 5.0), 1),
            "solves_specific_problem": specific_problem,
            "clarity": clarity,
            "has_error_handling": has_error_handling,
        }

    def _evaluate_security(self, combined_text: str) -> Dict[str, Any]:
        hits = []
        for label, keywords in self.SECURITY_RISK_RULES.items():
            if self._contains_keywords(combined_text, keywords):
                hits.append(label)

        has_warning = self._contains_keywords(combined_text, self.WARNING_KEYWORDS)
        if "执行未知脚本" in hits or "暴露密钥" in hits:
            risk_level = "high"
        elif hits:
            risk_level = "medium"
        else:
            risk_level = "low"

        if risk_level == "high":
            recommendation = "检测到高风险操作，除非有官方说明和隔离环境，否则不应采用。"
        elif risk_level == "medium":
            recommendation = "涉及潜在敏感操作，采用前需补充安全说明和回滚方案。"
        else:
            recommendation = "未发现明显安全风险，可继续按标准流程评估。"

        return {
            "risk_level": risk_level,
            "sensitive_operations": hits or ["无风险"],
            "has_warning": has_warning,
            "recommendation": recommendation,
        }

    def _evaluate_compliance(self, combined_text: str, signals: List[Any]) -> Dict[str, Any]:
        license_clear = self._contains_keywords(combined_text, self.LICENSE_KEYWORDS)
        reverse_engineering = self._contains_keywords(combined_text, self.REVERSE_ENGINEERING_KEYWORDS)
        mentions_repository = any("github.com" in (signal.url or "").lower() for signal in signals)

        if reverse_engineering:
            recommendation = "涉及破解或逆向语义，不建议纳入知识库。"
        elif mentions_repository and not license_clear:
            recommendation = "若后续引用代码实现，需补充许可证信息。"
        else:
            recommendation = "未发现明显合规阻碍。"

        return {
            "license_clear": license_clear,
            "reverse_engineering": reverse_engineering,
            "recommendation": recommendation,
        }

    def _determine_conclusion(
        self,
        weighted_total: float,
        timeliness_score: float,
        credibility_score: float,
        accuracy_score: float,
        practicality_score: float,
        security: Dict[str, Any],
        compliance: Dict[str, Any],
    ) -> str:
        if security["risk_level"] == "high" or compliance["reverse_engineering"]:
            return "discarded"

        if weighted_total >= 3.8 and min(timeliness_score, credibility_score, accuracy_score, practicality_score) >= 3.0:
            return "useful"

        if weighted_total >= 3.0 and accuracy_score >= 2.5 and credibility_score >= 2.5:
            return "reference"

        return "discarded"

    def _build_summary(
        self,
        weighted_total: float,
        conclusion: str,
        timeliness: Dict[str, Any],
        credibility: Dict[str, Any],
        accuracy: Dict[str, Any],
        practicality: Dict[str, Any],
        security: Dict[str, Any],
        compliance: Dict[str, Any],
    ) -> str:
        conclusion_map = {
            "useful": "有用，可直接入库",
            "reference": "仅供参考，不入库",
            "discarded": "应丢弃",
        }
        return (
            f"自动审核结论：{conclusion_map[conclusion]}。"
            f"总分 {weighted_total:.2f}/5.0；时效性 {timeliness['score']:.1f}，"
            f"可信度 {credibility['score']:.1f}，准确性 {accuracy['score']:.1f}，实用性 {practicality['score']:.1f}。"
            f"安全风险 {security['risk_level']}，合规建议：{compliance['recommendation']}"
        )

    def _build_record_summary(self, topic: Topic, report: Dict[str, Any]) -> str:
        dimensions = {}
        for evidence in topic.topic_evidences:
            dimensions[evidence.source_type] = dimensions.get(evidence.source_type, 0) + 1

        dimension_summary = "，".join(f"{key} {count} 条" for key, count in sorted(dimensions.items()))
        return (
            f"{topic.canonical_name} 通过自动审核并入库。"
            f"交叉证据：{dimension_summary or '无'}。"
            f"审核加权总分 {report['weighted_total']:.2f}/5.0，结论：有用。"
        )

    def _get_source_profile(self, source_name: str) -> Dict[str, Any]:
        return self.SOURCE_PROFILES.get(
            source_name,
            {
                "credibility": 3.0,
                "source_type": "未知",
                "author_background": "未知",
                "commercial_bias": False,
            },
        )

    def _determine_frequency(self, source_names: set[str]) -> tuple[str, str]:
        if source_names & self.HIGH_FREQUENCY_SOURCES:
            return "high", "高频"
        if source_names & self.MEDIUM_FREQUENCY_SOURCES:
            return "medium", "中频"
        return "low", "低频"

    def _build_combined_text(self, topic: Topic, signals: List[Any]) -> str:
        parts = [topic.canonical_name or ""]
        for signal in signals:
            parts.extend([signal.title or "", signal.content or "", signal.url or ""])
            try:
                metadata = json.loads(signal.metadata_json or "{}")
                parts.append(json.dumps(metadata, ensure_ascii=False))
            except json.JSONDecodeError:
                pass
        return " ".join(parts).lower()

    def _get_latest_signal_time(self, signals: List[Any]) -> Optional[datetime]:
        timestamps = [
            signal.published_at or signal.fetched_at
            for signal in signals
            if signal.published_at or signal.fetched_at
        ]
        return max(timestamps) if timestamps else None

    def _detect_code_completeness(self, combined_text: str) -> str:
        hits = sum(1 for hint in self.CODE_HINTS if hint in combined_text)
        if hits >= 2:
            return "完整可运行"
        if hits == 1:
            return "片段需补全"
        return "明显错误或未提供"

    def _contains_keywords(self, text: str, keywords: List[str]) -> bool:
        return any(keyword.lower() in text for keyword in keywords)

    def _most_common(self, items: List[str]) -> Optional[str]:
        if not items:
            return None
        counts: Dict[str, int] = {}
        for item in items:
            counts[item] = counts.get(item, 0) + 1
        return sorted(counts.items(), key=lambda pair: pair[1], reverse=True)[0][0]

    def _clamp(self, value: float, minimum: float, maximum: float) -> float:
        return max(minimum, min(maximum, value))
