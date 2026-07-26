#!/usr/bin/env python3
"""Wolne Lektury -- public JSON API (no key).

Docs: https://wolnelektury.pl/api/

The flat /api/books/ catalog returns a multi-megabyte JSON array -- this
script deliberately never calls it directly. Use list-taxonomy to discover
slugs, then filter-books / get-book / get-collection.

Subcommands mirror the original MCP tools:
  list-taxonomy   -> GET /api/{authors|epochs|genres|kinds|themes|collections}/
  filter-books    -> GET /api/authors/.../epochs/.../genres/.../kinds/.../(books|parent_books)/
  get-book        -> GET /api/books/{slug}/
  get-collection  -> GET /api/collections/{slug}/
"""

from __future__ import annotations

import argparse
import sys
import urllib.parse

from _http import fail, print_result, request_json

API_BASE = "https://wolnelektury.pl/api"
JSON_HEADERS = {"Accept": "application/json"}

TAXONOMY_KINDS = ["authors", "epochs", "genres", "kinds", "themes", "collections"]


def _enc(slug: str) -> str:
    return urllib.parse.quote(slug.strip(), safe="")


def _build_filtered_books_url(author_slug, epoch_slug, genre_slug, kind_slug, parent_only: bool) -> str:
    segments = []
    if author_slug:
        segments.append(f"authors/{_enc(author_slug)}/")
    if epoch_slug:
        segments.append(f"epochs/{_enc(epoch_slug)}/")
    if genre_slug:
        segments.append(f"genres/{_enc(genre_slug)}/")
    if kind_slug:
        segments.append(f"kinds/{_enc(kind_slug)}/")
    if not segments:
        fail(
            "Error calling wolnelektury_filter_books: provide at least one of "
            "--author, --epoch, --genre, --kind (the flat /api/books/ endpoint is too large to fetch)."
        )
    leaf = "parent_books/" if parent_only else "books/"
    return f"{API_BASE}/{''.join(segments)}{leaf}"


def cmd_get_book(args: argparse.Namespace) -> None:
    url = f"{API_BASE}/books/{_enc(args.slug)}/"
    try:
        result = request_json(url, headers=JSON_HEADERS)
    except RuntimeError as e:
        fail(f"Error calling wolnelektury_get_book: {e}")
        return
    print_result(result)


def cmd_get_collection(args: argparse.Namespace) -> None:
    url = f"{API_BASE}/collections/{_enc(args.slug)}/"
    try:
        result = request_json(url, headers=JSON_HEADERS)
    except RuntimeError as e:
        fail(f"Error calling wolnelektury_get_collection: {e}")
        return
    print_result(result)


def cmd_filter_books(args: argparse.Namespace) -> None:
    url = _build_filtered_books_url(args.author, args.epoch, args.genre, args.kind, args.parent_only)
    try:
        result = request_json(url, headers=JSON_HEADERS)
    except RuntimeError as e:
        fail(f"Error calling wolnelektury_filter_books: {e}")
        return
    print_result(result)


def cmd_list_taxonomy(args: argparse.Namespace) -> None:
    url = f"{API_BASE}/{args.kind}/"
    try:
        result = request_json(url, headers=JSON_HEADERS)
    except RuntimeError as e:
        fail(f"Error calling wolnelektury_list_taxonomy: {e}")
        return
    print_result(result)


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="wolne_lektury.py",
        description="Wolne Lektury (wolnelektury.pl) -- free Polish-literature ebook library, public JSON API.",
    )
    sub = p.add_subparsers(dest="command", required=True)

    pt = sub.add_parser("list-taxonomy", help="List reference data for discovery (names, slugs, hrefs).")
    pt.add_argument("--kind", required=True, choices=TAXONOMY_KINDS, help="Which taxonomy endpoint to list.")
    pt.set_defaults(func=cmd_list_taxonomy)

    pf = sub.add_parser("filter-books", help="List books matching combined filters (AND). Requires at least one filter.")
    pf.add_argument("--author", default=None, help="Author slug, e.g. boleslaw-prus.")
    pf.add_argument("--epoch", default=None, help="Literary epoch slug, e.g. pozytywizm.")
    pf.add_argument("--genre", default=None, help="Genre slug, e.g. powiesc.")
    pf.add_argument("--kind", default=None, help="Literary kind slug, e.g. epika, liryka.")
    pf.add_argument("--parent-only", action="store_true", help="Use parent_books/ instead of books/ (top-level works only, no sub-volumes).")
    pf.set_defaults(func=cmd_filter_books)

    pb = sub.add_parser("get-book", help="Fetch one book by URL slug (e.g. lalka, pan-tadeusz).")
    pb.add_argument("--slug", required=True, help="Book slug from /katalog/lektura/{slug}/ or an API href.")
    pb.set_defaults(func=cmd_get_book)

    pc = sub.add_parser("get-collection", help="Fetch one thematic collection by slug (metadata + embedded books list).")
    pc.add_argument("--slug", required=True, help="Collection slug (see list-taxonomy --kind collections).")
    pc.set_defaults(func=cmd_get_collection)

    return p


def main(argv=None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main(sys.argv[1:])
