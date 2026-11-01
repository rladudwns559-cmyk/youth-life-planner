"""메모리 내 정책 근거 조회. 검증 상태·최신성·정책 적용 범위를 재판정하지 않는다."""

from dataclasses import dataclass

from .models import SourceDocument, SourceEvidence, SourceStatus, SourceValidationError, _identifier, parse_evidence_ref


@dataclass(frozen=True, slots=True)
class SourceRegistry:
    sources: tuple[SourceDocument, ...]

    def __post_init__(self) -> None:
        if (type(self.sources) is not tuple or not self.sources
                or any(type(item) is not SourceDocument for item in self.sources)):
            raise SourceValidationError("INVALID_SOURCE_COLLECTION", "sources")
        ids = tuple(item.source_document_id for item in self.sources)
        if len(set(ids)) != len(ids):
            raise SourceValidationError("DUPLICATE_SOURCE_ID", "sources")
        # 현재 묶음에 정확한 확인본이 있는 대체 관계만 순환 검사한다.
        # 과거 release에 대한 관계는 보존하며 존재 검증은 manifest 계층의 책임이다.
        nodes = {(item.source_document_id, item.document_version) for item in self.sources}
        edges = {key: set() for key in nodes}
        incoming = {key: 0 for key in nodes}
        for item in self.sources:
            key = (item.source_document_id, item.document_version)
            for previous in item.supersedes:
                if previous in nodes:
                    edges[key].add(previous)
                    incoming[previous] += 1
        pending = [key for key in nodes if incoming[key] == 0]
        visited = 0
        while pending:
            key = pending.pop()
            visited += 1
            for previous in edges[key]:
                incoming[previous] -= 1
                if incoming[previous] == 0:
                    pending.append(previous)
        if visited != len(nodes):
            raise SourceValidationError("CYCLIC_SUPERSEDES", "supersedes")

    def has_source(self, source_document_id: str) -> bool:
        _identifier(source_document_id, "source_document_id")
        return any(item.source_document_id == source_document_id for item in self.sources)

    def get_source(self, source_document_id: str) -> SourceDocument:
        _identifier(source_document_id, "source_document_id")
        for item in self.sources:
            if item.source_document_id == source_document_id:
                return item
        raise SourceValidationError("SOURCE_NOT_FOUND", "source_document_id")

    def has_evidence(self, ref: str) -> bool:
        """존재만 조회한다. 참조 수명에 대한 허용 여부는 resolve가 검사한다."""
        source_id, locator_id = parse_evidence_ref(ref)
        return any(item.source_document_id == source_id and any(
            evidence.locator_id == locator_id for evidence in item.locators) for item in self.sources)

    def resolve(self, ref: str) -> SourceEvidence:
        source_id, locator_id = parse_evidence_ref(ref)
        source = self.get_source(source_id)
        if source.status is not SourceStatus.ACTIVE:
            raise SourceValidationError("SOURCE_NOT_REFERENCEABLE", "status")
        for evidence in source.locators:
            if evidence.locator_id == locator_id:
                if evidence.status is not SourceStatus.ACTIVE:
                    raise SourceValidationError("EVIDENCE_NOT_REFERENCEABLE", "locators.status")
                return evidence
        raise SourceValidationError("LOCATOR_NOT_FOUND", "locator_id")

    def to_dict(self) -> dict:
        """JSON 친화적인 값 표현이며 파일 loader나 배포 검증이 아니다."""
        return {"schema_version": "source-registry-1.0", "sources": [item.to_dict() for item in self.sources]}


def validate_evidence_refs(refs: tuple[str, ...], registry: SourceRegistry) -> tuple[SourceEvidence, ...]:
    """leaf 하나의 참조 묶음을 순서대로 검증한다. 부분 결과는 반환하지 않는다."""
    if type(registry) is not SourceRegistry:
        raise SourceValidationError("INVALID_SOURCE_REGISTRY", "registry")
    if type(refs) is not tuple or not refs:
        raise SourceValidationError("INVALID_EVIDENCE_REFS", "evidence_refs")
    for ref in refs:
        parse_evidence_ref(ref)
    if len(set(refs)) != len(refs):
        raise SourceValidationError("DUPLICATE_EVIDENCE_REF", "evidence_refs")
    return tuple(registry.resolve(ref) for ref in refs)
