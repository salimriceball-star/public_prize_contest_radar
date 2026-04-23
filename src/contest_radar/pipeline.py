from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Iterable
from uuid import uuid4

from .collectors import safe_collect_source
from .config_loader import DEFAULT_CATEGORIES_PATH, DEFAULT_DB_PATH, DEFAULT_SOURCES_PATH, load_categories, load_sources
from .models import ContestRecord, RawListing, SourceSpec
from .normalize import canonicalize_url, fingerprint_for, repeat_key_from_title
from .scoring import score_listing
from .storage import connect, fetch_known_urls, init_db, lookup_existing_fingerprints, lookup_repeat_counts, record_run, upsert_records


def _dedupe_listings(listings: Iterable[RawListing]) -> list[RawListing]:
    seen_urls: set[str] = set()
    deduped: list[RawListing] = []
    for listing in listings:
        key = canonicalize_url(listing.url)
        if key in seen_urls:
            continue
        seen_urls.add(key)
        deduped.append(listing)
    return deduped


def run_once(
    db_path: str = str(DEFAULT_DB_PATH),
    sources_path: str = str(DEFAULT_SOURCES_PATH),
    categories_path: str = str(DEFAULT_CATEGORIES_PATH),
    enabled_source_ids: set[str] | None = None,
) -> dict[str, Any]:
    init_db(db_path)
    defaults, sources = load_sources(sources_path)
    categories = load_categories(categories_path)
    source_map = {source.id: source for source in sources}
    started_at = datetime.now(timezone.utc).isoformat()
    run_id_prefix = uuid4().hex[:10]
    collected: list[RawListing] = []
    errors: list[dict[str, Any]] = []
    with connect(db_path) as conn:
        known_urls = fetch_known_urls(conn)
        for index, source in enumerate(sources, start=1):
            if enabled_source_ids and source.id not in enabled_source_ids:
                continue
            if not source.enabled:
                continue
            run_id = f"{run_id_prefix}-{index}"
            raw_items, error_text = safe_collect_source(source, defaults, known_urls=known_urls)
            items = []
            for item in raw_items:
                cache_key = canonicalize_url(item.url)
                if cache_key in known_urls:
                    item.extras["cache_hit"] = True
                    continue
                known_urls.add(cache_key)
                items.append(item)
            status = "ok" if not error_text else "error"
            record_run(conn, run_id, started_at, source.id, status, len(items), error_text)
            collected.extend(items)
            if error_text:
                errors.append({"source_id": source.id, "source_name": source.name, "error": error_text})

        deduped = _dedupe_listings(collected)
        repeat_lookup = lookup_repeat_counts(conn, [listing.title for listing in deduped])
        records: list[ContestRecord] = []
        for listing in deduped:
            source = source_map[listing.source_id]
            repeat_count = repeat_lookup.get(repeat_key_from_title(listing.title), 0)
            records.append(score_listing(listing, source, categories, repeat_count=repeat_count))
        records.sort(key=lambda item: item.score, reverse=True)
        existing_fingerprints = lookup_existing_fingerprints(conn, [record.fingerprint for record in records])
        new_records = [record for record in records if record.fingerprint not in existing_fingerprints]
        inserted = upsert_records(conn, records)
    return {
        "run_started_at": started_at,
        "sources_attempted": len([source for source in sources if source.enabled and (not enabled_source_ids or source.id in enabled_source_ids)]),
        "collected_count": len(collected),
        "deduped_count": len(deduped),
        "inserted_count": inserted,
        "new_count": len(new_records),
        "errors": errors,
        "records": records,
        "new_records": new_records,
    }
