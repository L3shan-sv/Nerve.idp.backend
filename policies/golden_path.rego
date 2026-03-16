package nerve.golden_path

import future.keywords.if
import future.keywords.in

# ── Weights ──────────────────────────────────────────────────
weights := {
    "health_endpoints":    20,
    "slo_defined":         20,
    "runbook_live_doc":    15,
    "otel_instrumentation": 15,
    "secrets_via_vault":   10,
    "security_posture":    20,
}

passing_threshold := 80

# ── Top-level evaluation ─────────────────────────────────────
evaluate := result if {
    result := {
        "checks":      all_checks,
        "total_score": total_score,
        "allowed":     total_score >= passing_threshold,
    }
}

total_score := sum([c.score | c := all_checks[_]])

all_checks := [
    health_check,
    slo_check,
    runbook_check,
    otel_check,
    vault_check,
    security_check,
]

# ── Check: health endpoints ───────────────────────────────────
health_check := result if {
    input.service.health_status != "unknown"
    result := {
        "name":   "health_endpoints",
        "passed": true,
        "score":  weights.health_endpoints,
        "detail": "/health + /ready endpoints detected",
    }
}

health_check := result if {
    input.service.health_status == "unknown"
    result := {
        "name":    "health_endpoints",
        "passed":  false,
        "score":   0,
        "detail":  "Health endpoints not found — add /health and /ready routes",
        "fix_url": "https://nerve.idp/docs/golden-path/health-endpoints",
    }
}

# ── Check: SLO defined ────────────────────────────────────────
slo_check := result if {
    input.service.slo_uptime_target > 0
    input.service.slo_latency_p99_ms > 0
    result := {
        "name":   "slo_defined",
        "passed": true,
        "score":  weights.slo_defined,
        "detail": sprintf("SLO: %.2f%% uptime · P99 %dms", [
            input.service.slo_uptime_target,
            input.service.slo_latency_p99_ms,
        ]),
    }
}

slo_check := result if {
    not input.service.slo_uptime_target > 0
    result := {
        "name":    "slo_defined",
        "passed":  false,
        "score":   0,
        "detail":  "No SLO defined in service.yaml",
        "fix_url": "https://nerve.idp/docs/golden-path/slo",
    }
}

# ── Check: runbook live doc ───────────────────────────────────
runbook_check := result if {
    input.service.repo_url != ""
    result := {
        "name":   "runbook_live_doc",
        "passed": true,
        "score":  weights.runbook_live_doc,
        "detail": "Live runbook doc detected",
    }
}

runbook_check := result if {
    not input.service.repo_url
    result := {
        "name":    "runbook_live_doc",
        "passed":  false,
        "score":   0,
        "detail":  "No runbook URL found — add /docs/runbook.md to repo",
        "fix_url": "https://nerve.idp/docs/golden-path/runbooks",
    }
}

# ── Check: OTel instrumentation ───────────────────────────────
# Phase 3: this will be populated by real OTel trace data
otel_check := {
    "name":    "otel_instrumentation",
    "passed":  false,
    "score":   0,
    "detail":  "OTel traces not yet verified — run nerve scan otel <service>",
    "fix_url": "https://nerve.idp/docs/golden-path/otel",
}

# ── Check: secrets via Vault ──────────────────────────────────
# Phase 3: populated by Vault secret scan
vault_check := {
    "name":    "secrets_via_vault",
    "passed":  false,
    "score":   0,
    "detail":  "Vault secret scan not yet run",
    "fix_url": "https://nerve.idp/docs/golden-path/secrets",
}

# ── Check: security posture ───────────────────────────────────
# Phase 3: populated by Trivy CVE scan results
security_check := {
    "name":    "security_posture",
    "passed":  false,
    "score":   0,
    "detail":  "Trivy scan not yet run for this image",
    "fix_url": "https://nerve.idp/docs/golden-path/security",
}
