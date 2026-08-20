from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import urlparse

from reelagent.topics.models import SourceKind


@dataclass(frozen=True)
class AuthoritativeDomain:
    """Trusted source family used to constrain verification evidence."""

    name: str
    hosts: tuple[str, ...]
    keywords: tuple[str, ...]
    source_kind: SourceKind = SourceKind.OFFICIAL


DEFAULT_AUTHORITATIVE_DOMAINS: tuple[AuthoritativeDomain, ...] = (
    AuthoritativeDomain(
        name="PostgreSQL",
        hosts=("postgresql.org", "www.postgresql.org"),
        keywords=("postgres", "postgresql", "sql", "jsonb", "skip locked"),
    ),
    AuthoritativeDomain(
        name="Apache Kafka",
        hosts=("kafka.apache.org",),
        keywords=("kafka", "consumer", "producer", "topic", "partition"),
    ),
    AuthoritativeDomain(
        name="Kubernetes",
        hosts=("kubernetes.io",),
        keywords=("kubernetes", "k8s", "pod", "deployment", "container"),
    ),
    AuthoritativeDomain(
        name="Python",
        hosts=("docs.python.org", "python.org", "www.python.org"),
        keywords=("python", "cpython", "asyncio", "gil"),
    ),
    AuthoritativeDomain(
        name="AWS",
        hosts=("docs.aws.amazon.com", "aws.amazon.com"),
        keywords=("aws", "amazon web services", "lambda", "dynamodb", "s3", "ec2"),
    ),
    AuthoritativeDomain(
        name="Google Cloud",
        hosts=("cloud.google.com",),
        keywords=("gcp", "google cloud", "gke", "bigquery", "cloud run"),
    ),
    AuthoritativeDomain(
        name="OpenJDK",
        hosts=("openjdk.org", "docs.oracle.com"),
        keywords=("java", "jdk", "jvm", "openjdk", "virtual threads"),
    ),
    AuthoritativeDomain(
        name="GitHub",
        hosts=("github.com", "docs.github.com"),
        keywords=("github", "git", "actions", "pull request"),
        source_kind=SourceKind.GITHUB,
    ),
)


def domains_for_query(
    query: str,
    domains: tuple[AuthoritativeDomain, ...] = DEFAULT_AUTHORITATIVE_DOMAINS,
) -> tuple[AuthoritativeDomain, ...]:
    lowered = query.lower()
    return tuple(
        domain
        for domain in domains
        if any(keyword in lowered for keyword in domain.keywords)
    )


def trusted_hosts_for_query(query: str) -> frozenset[str]:
    return frozenset(host for domain in domains_for_query(query) for host in domain.hosts)


def is_trusted_url(url: str, trusted_hosts: frozenset[str]) -> bool:
    parsed = urlparse(url)
    return parsed.scheme == "https" and (parsed.hostname or "").lower() in trusted_hosts
