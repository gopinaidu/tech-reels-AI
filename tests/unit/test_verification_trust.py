from reelagent.verification.trust import (
    domains_for_query,
    is_trusted_url,
    trusted_hosts_for_query,
)


def test_domains_for_query_selects_matching_authoritative_family() -> None:
    domains = domains_for_query("PostgreSQL supports SKIP LOCKED")

    assert [domain.name for domain in domains] == ["PostgreSQL"]


def test_trusted_hosts_for_query_collects_all_hosts_for_selected_domains() -> None:
    hosts = trusted_hosts_for_query("Python asyncio GIL")

    assert "docs.python.org" in hosts
    assert "python.org" in hosts


def test_is_trusted_url_requires_https_and_exact_host() -> None:
    hosts = frozenset({"www.postgresql.org", "postgresql.org"})

    assert is_trusted_url(
        "https://www.postgresql.org/docs/current/sql-select.html",
        hosts,
    )
    assert not is_trusted_url("http://www.postgresql.org/docs/current/sql-select.html", hosts)
    assert not is_trusted_url("https://postgresql.org.example.com/docs/current/", hosts)
