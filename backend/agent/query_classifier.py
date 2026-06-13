"""Query classification for RAG routing decisions.

Classifies user queries to determine whether document retrieval is needed
and what scope of retrieval to use.

Architecture rule: retrieval is OFF by default. It is only triggered when the
query contains explicit document/file/source intent OR explicit scope
(attached_files / selected_files).

Industrial keywords (PLC, DCS, motor, ...) by themselves DO NOT trigger
retrieval; they only mark the question as INDUSTRIAL_KNOWLEDGE so the answer
node can use a knowledge-only prompt mode.

Definition / comparison / explanation questions ("what is", "difference
between", "ما هو", "الفرق بين", ...) are treated as knowledge questions and
never trigger retrieval unless they also contain explicit document intent.
"""

from __future__ import annotations

import re
from enum import Enum


class QueryCategory(str, Enum):
    GENERAL_CHAT = "GENERAL_CHAT"
    RAG_REQUIRED = "RAG_REQUIRED"
    FILE_QA = "FILE_QA"
    CURRENT_ATTACHMENT_QA = "CURRENT_ATTACHMENT_QA"
    INDUSTRIAL_KNOWLEDGE = "INDUSTRIAL_KNOWLEDGE"
    UNKNOWN = "UNKNOWN"


# Explicit English document-intent phrases. These are deliberately narrow:
# generic words on their own are not enough — we need a phrase that clearly
# refers to a stored document, file, or attachment.
_DOC_INTENT_EN = re.compile(
    r"\b("
    r"uploaded\s+(file|document|pdf|report|image|audio|recording|attachment)"
    r"|attached\s+(file|document|pdf|report|image|audio|recording|attachment)"
    r"|this\s+(file|document|pdf|report|image|attachment|manual)"
    r"|the\s+(pdf|report|manual|document|file|attachment|transcript|audio\s+recording|recording|scan|image)"
    r"|according\s+to\s+(the\s+)?(file|document|pdf|report|manual|attachment|transcript|audio|recording)"
    r"|in\s+the\s+(file|document|pdf|report|manual|attachment|audio|recording|transcript)"
    r"|from\s+the\s+(file|document|pdf|report|manual|attachment|attached|audio|recording|transcript)"
    r"|about\s+the\s+(file|document|pdf|report|manual|attachment|audio|recording|transcript)"
    r"|based\s+on\s+the\s+(attached|attachment|file|document|pdf|report|manual)"
    r"|summari[sz]e\s+(the\s+)?(file|pdf|document|report|manual|attachment|uploaded|attached)"
    r"|explain\s+(this|the)\s+(file|document|pdf|report|attachment|image)"
    r"|\bpdf\b|\bmanual\b|\breport\b|\bdocument\b|\bdocuments\b|\battachment\b|\battachments\b"
    r"|\btranscript\b|\baudio\s+recording\b|\brecording\b|\bocr\b|\bscan\b"
    r")",
    re.IGNORECASE,
)


# Explicit Arabic document-intent phrases.
_DOC_INTENT_AR = re.compile(
    r"الملف\s+المرفوع"
    r"|الملف\s+المرفق"
    r"|الملفات\s+المرفقة"
    r"|المرفق|المرفقات"
    r"|المستند|المستندات|الوثيقة|الوثائق"
    r"|التقرير|التقارير"
    r"|المانيوال|المانوال"
    r"|دليل\s+التشغيل|كتيب"
    r"|حسب\s+الملف|حسب\s+التقرير|حسب\s+المستند|حسب\s+المانيوال"
    r"|من\s+الملف|من\s+التقرير|من\s+المستند|من\s+المرفق"
    r"|في\s+الملف|في\s+التقرير|في\s+المستند"
    r"|بناء(ً)?\s+على\s+(الملف|التقرير|المستند|النص\s+المرفق|المرفق)"
    r"|الصورة\s+المرفقة|الصوت\s+المرفق|التسجيل|تسجيل\s+صوتي"
    r"|لخص\s+(الملف|الملفات|المستند|التقرير|المرفق|المرفقات)"
    r"|اشرح\s+(الملف|الملفات|المستند|التقرير|المرفق|المرفقات)"
)


# Industrial keywords. These mark the query as INDUSTRIAL_KNOWLEDGE so the
# answer node can answer from general industrial knowledge, but they DO NOT
# trigger retrieval on their own.
_INDUSTRIAL_KEYWORDS_EN = re.compile(
    r"\b("
    r"machine|machinery|equipment|maintenance|fault|vibration|bearing|motor"
    r"|pump|valve|compressor|turbine|sensor|alarm|plc|dcs|scada|hmi|opc(\s*ua)?"
    r"|downtime|failure|inspection|calibration|safety|hazard"
    r"|iso\s*\d+|standard|procedure|sop|specification"
    r"|industrial|automation|instrumentation|control\s+system"
    r")\b",
    re.IGNORECASE,
)


# Arabic industrial keywords. Deliberately narrow: generic words like
# "تشغيل" alone are excluded to avoid false positives in conversational
# Arabic (it just means "running" / "operation").
_INDUSTRIAL_KEYWORDS_AR = re.compile(
    r"معدات|الصيانة|صيانة|عطل|أعطال|محرك|مضخة|صمام|استشعار|فحص|إنذار|سلامة"
    r"|ماكينة|مكينة|آلة|آلية|تحكم\s+صناعي|أتمتة|توربين|ضاغط|محامل|اهتزاز"
    r"|تشغيل\s+(الماكينة|المضخة|المحرك|الآلة)"
)


_GREETING_PATTERNS = re.compile(
    r"^("
    r"hi|hello|hey|howdy|good\s+morning|good\s+evening|good\s+afternoon"
    r"|thanks|thank\s+you|bye|goodbye|see\s+you"
    r"|مرحبا|أهلا|شكرا|مع\s+السلامة|السلام\s+عليكم"
    r"|what\s+can\s+you\s+do|who\s+are\s+you|help"
    r")[\s?!.]*$",
    re.IGNORECASE,
)


# Definition / comparison / explanation intent (English).
# A query matching these patterns is treated as a knowledge question, NOT a
# document question, unless it also contains explicit document intent.
_DEFINITION_INTENT_EN = re.compile(
    r"\b("
    r"what\s+is|what\s+are|what\s+does"
    r"|define|definition\s+of"
    r"|explain|explanation\s+of"
    r"|difference\s+between|differences\s+between"
    r"|compare|comparison\s+between"
    r"|overview\s+of"
    r"|who\s+is|who\s+are|who\s+was|who\s+were"
    r"|tell\s+me\s+about"
    r"|how\s+does\s+\w+\s+work"
    r")\b",
    re.IGNORECASE,
)


# Definition / comparison / explanation intent (Arabic).
_DEFINITION_INTENT_AR = re.compile(
    r"ما\s+هو|ما\s+هي|ما\s+معنى|يعني\s+ايه|يعني\s+إيه"
    r"|اشرح(?!\s+(الملف|الملفات|المستند|التقرير|المرفق|المرفقات))"
    r"|الفرق\s+بين|ما\s+الفرق\s+بين|قارن\s+بين"
    r"|مين\s+هو|مين\s+هي|من\s+هو|من\s+هي"
    r"|تعريف|عرف"
    r"|نبذة\s+عن"
)


_SEARCH_TRIGGER_EN = re.compile(
    r"\b("
    r"search|look\s+up|find|verify|double\s+check|cross[-\s]?check"
    r"|updated|update|latest|current|currently|today|news|release\s+notes"
    r"|references?|citations?|sources?"
    r"|price|pricing|cost|law|regulation|standard\s+version|api\s+changes?"
    r")\b",
    re.IGNORECASE,
)


_SEARCH_TRIGGER_AR = re.compile(
    r"ابحث|دور|تحقق|اتاكد|اتأكد|راجع|دبل\s*تشيك|تحقق\s+من"
    r"|محدث|محد[ثة]ة|أحدث|احدث|حالي|حالياً|حاليا|دلوقتي|اليوم|الآن|الان"
    r"|مصادر|مرجع|مراجع|سعر|أسعار|اسعار|قانون|لائحة|معيار|إصدار|اصدار",
    re.IGNORECASE,
)


_SEARCH_TOPIC_EN = re.compile(
    r"\b("
    r"price|pricing|cost|standard|spec|regulation|law|api|sdk|release|version"
    r"|company|role|schedule|news|opc\s*ua|iec|iso\s*\d+"
    r")\b",
    re.IGNORECASE,
)


_SEARCH_TOPIC_AR = re.compile(
    r"سعر|اسعار|أسعار|معيار|قياسي|لائحة|قانون|تشريع|إصدار|اصدار|نسخة|إصدار"
    r"|واجهة\s*برمجة|خبر|أخبار|اخبار|شركة|منصب|جدول|موعد|حالي|أحدث|احدث|OPC\s*UA|IEC|ISO",
    re.IGNORECASE,
)


_COMPARE_WITH_WEB_EN = re.compile(r"\b(compare\s+with\s+the\s+web|check\s+online|web\s+search)\b", re.IGNORECASE)
_COMPARE_WITH_WEB_AR = re.compile(r"قارن\s+مع\s+الويب|من\s+الويب|ابحث\s+على\s+الويب|تحقق\s+اونلاين|تحقق\s+عبر\s+الويب", re.IGNORECASE)
_LOCAL_ONLY_EN = re.compile(r"\b(from|using)\s+the\s+(file|document|attachment)\s+only\b", re.IGNORECASE)
_LOCAL_ONLY_AR = re.compile(r"من\s+الملف\s+فقط|من\s+المرفق\s+فقط|اعتمد\s+على\s+الملف\s+فقط|جاوب\s+من\s+الملف\s+فقط", re.IGNORECASE)


def _has_doc_intent(query: str) -> bool:
    return bool(_DOC_INTENT_EN.search(query) or _DOC_INTENT_AR.search(query))


def _has_definition_intent(query: str) -> bool:
    return bool(_DEFINITION_INTENT_EN.search(query) or _DEFINITION_INTENT_AR.search(query))


def _has_industrial_keyword(query: str) -> bool:
    return bool(_INDUSTRIAL_KEYWORDS_EN.search(query) or _INDUSTRIAL_KEYWORDS_AR.search(query))


def classify_search_requirement(
    query: str,
    *,
    answer_mode: str | None = None,
    has_attached_files: bool = False,
    has_selected_files: bool = False,
) -> tuple[bool, str | None]:
    stripped = (query or "").strip()
    if not stripped:
        return False, None

    explicit_compare = bool(_COMPARE_WITH_WEB_EN.search(stripped) or _COMPARE_WITH_WEB_AR.search(stripped))
    local_only = bool(_LOCAL_ONLY_EN.search(stripped) or _LOCAL_ONLY_AR.search(stripped))

    if local_only and not explicit_compare:
        return False, "local_only_request"

    if answer_mode in {"groundx", "audio"} and not explicit_compare:
        return False, "local_mode_without_web_override"

    if has_attached_files and not explicit_compare:
        return False, "attached_file_request"

    if has_selected_files and not explicit_compare:
        return False, "selected_scope_request"

    has_search_trigger = bool(_SEARCH_TRIGGER_EN.search(stripped) or _SEARCH_TRIGGER_AR.search(stripped))
    has_search_topic = bool(_SEARCH_TOPIC_EN.search(stripped) or _SEARCH_TOPIC_AR.search(stripped))

    if explicit_compare:
        return True, "explicit_web_comparison"
    if has_search_trigger and has_search_topic:
        return True, "explicit_current_information_request"
    if has_search_trigger and any(word in stripped.lower() for word in ("latest", "current", "updated", "sources", "citations", "today")):
        return True, "explicit_search_request"
    if re.search(r"(أحدث|احدث|حالي|حاليا|حالياً|دلوقتي|اليوم)", stripped, re.IGNORECASE) and has_search_topic:
        return True, "recent_fact_request"

    return False, None


def classify_query(
    query: str,
    *,
    has_attached_files: bool = False,
    has_selected_files: bool = False,
) -> QueryCategory:
    """Classify a user query to determine retrieval routing.

    Args:
        query: The user's question text.
        has_attached_files: Whether the request includes file attachments.
        has_selected_files: Whether specific files are selected for scope.

    Returns:
        QueryCategory indicating the routing decision.
    """
    stripped = (query or "").strip()

    if not stripped:
        return QueryCategory.GENERAL_CHAT

    if has_attached_files:
        return QueryCategory.CURRENT_ATTACHMENT_QA

    if _GREETING_PATTERNS.match(stripped):
        return QueryCategory.GENERAL_CHAT

    has_doc_intent = _has_doc_intent(stripped)
    has_def_intent = _has_definition_intent(stripped)
    has_industrial = _has_industrial_keyword(stripped)

    # Explicit document intent always wins: the user is asking about a
    # specific document/file/manual/transcript.
    if has_doc_intent:
        if has_selected_files:
            return QueryCategory.FILE_QA
        return QueryCategory.RAG_REQUIRED

    # Definition / comparison / explanation question with no doc intent:
    # this is a knowledge question, not a document question.
    if has_def_intent:
        if has_industrial:
            return QueryCategory.INDUSTRIAL_KNOWLEDGE
        return QueryCategory.GENERAL_CHAT

    # Industrial keyword present but no doc intent and no definition pattern:
    # still classify as INDUSTRIAL_KNOWLEDGE (router will NOT trigger retrieval).
    if has_industrial:
        return QueryCategory.INDUSTRIAL_KNOWLEDGE

    # Short / generic queries default to GENERAL_CHAT.
    if len(stripped.split()) <= 5:
        return QueryCategory.GENERAL_CHAT

    return QueryCategory.UNKNOWN
