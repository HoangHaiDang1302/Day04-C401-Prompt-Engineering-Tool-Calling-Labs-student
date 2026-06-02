from __future__ import annotations

from typing import Any

from tools._shared import domain, err, fold_text


HIGH_TRUST_DOMAINS = {
    "openai.com",
    "anthropic.com",
    "deepmind.google",
    "googleblog.com",
    "microsoft.com",
    "arxiv.org",
    "nature.com",
    "science.org",
    "acm.org",
    "ieee.org",
    "nih.gov",
    "who.int",
    "europa.eu",
}

NEWS_DOMAINS = {
    "reuters.com",
    "apnews.com",
    "bbc.com",
    "theverge.com",
    "techcrunch.com",
    "wired.com",
    "mit.edu",
}

LOW_TRUST_MARKERS = {
    "rumor",
    "leak",
    "unconfirmed",
    "viral",
    "anonymous",
    "screenshot",
    "thread",
    "tweet",
    "tiktok",
}


def audit_source(url: str = "", source_name: str = "", claim: str = "") -> dict[str, Any]:
    try:
        source_domain = domain(url)
        folded = fold_text(" ".join([url, source_name, claim]))
        reasons: list[str] = []

        if source_domain in HIGH_TRUST_DOMAINS or source_domain.endswith(".gov") or source_domain.endswith(".edu"):
            rating = "strong"
            reasons.append("Primary, academic, government, or official institutional source.")
        elif source_domain in NEWS_DOMAINS:
            rating = "usable"
            reasons.append("Recognized news or technology publication; cite with date and link.")
        elif any(marker in folded for marker in LOW_TRUST_MARKERS):
            rating = "weak"
            reasons.append("Contains rumor/social/anonymous markers; verify with a primary or reputable source first.")
        elif source_domain:
            rating = "needs_review"
            reasons.append("Domain is provided but not in the known high-trust list; manually verify author, date, and evidence.")
        else:
            rating = "insufficient"
            reasons.append("No URL/domain was provided, so source quality cannot be assessed.")

        if claim and any(marker in fold_text(claim) for marker in LOW_TRUST_MARKERS):
            if rating in {"strong", "usable"}:
                rating = "needs_review"
            reasons.append("The claim wording itself suggests uncertainty.")

        guidance = {
            "strong": "Good candidate for citation. Prefer this source over secondary summaries.",
            "usable": "Can be cited, but check whether a primary source is available.",
            "needs_review": "Review manually before citing externally.",
            "weak": "Do not cite as evidence without corroboration.",
            "insufficient": "Ask for a URL or named source before deciding.",
        }[rating]

        return {
            "tool": "source_audit",
            "url": url,
            "source_name": source_name,
            "domain": source_domain,
            "claim": claim,
            "rating": rating,
            "reasons": reasons,
            "citation_guidance": guidance,
        }
    except Exception as exc:
        return err("source_audit", exc)
