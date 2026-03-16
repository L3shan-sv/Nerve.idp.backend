package nerve.security

import future.keywords.if
import future.keywords.in

# ── CVE severity gates ────────────────────────────────────────

# Critical CVE = hard block regardless of total score
deploy_blocked if {
    some cve in input.cve_report
    cve.severity == "CRITICAL"
}

# Summarise security posture score (max 20)
security_score := score if {
    critical_count := count([c | c := input.cve_report[_]; c.severity == "CRITICAL"])
    high_count     := count([c | c := input.cve_report[_]; c.severity == "HIGH"])
    medium_count   := count([c | c := input.cve_report[_]; c.severity == "MEDIUM"])

    critical_count == 0
    high_count     == 0
    score := max([0, 20 - (medium_count * 1)])
}

security_score := 0 if {
    some cve in input.cve_report
    cve.severity == "CRITICAL"
}

security_score := score if {
    critical_count := count([c | c := input.cve_report[_]; c.severity == "CRITICAL"])
    high_count     := count([c | c := input.cve_report[_]; c.severity == "HIGH"])
    critical_count == 0
    high_count     > 0
    score := max([0, 15 - (high_count * 5)])
}
