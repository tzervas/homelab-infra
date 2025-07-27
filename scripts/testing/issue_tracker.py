#!/usr/bin/env python3
"""Issue Tracking and Prioritization for Homelab Testing Framework.

This module provides comprehensive issue tracking with severity classification,
aggregation, and prioritized reporting to ensure critical issues are not masked.
"""

from collections import Counter, defaultdict
from dataclasses import dataclass, field
from enum import Enum
import logging
from typing import Any, Dict, List, Optional, Tuple


class IssueSeverity(Enum):
    """Issue severity levels for prioritization."""

    CRITICAL = "critical"  # System-breaking issues
    HIGH = "high"  # Security vulnerabilities, major functionality loss
    MEDIUM = "medium"  # Performance issues, minor functionality loss
    LOW = "low"  # Cosmetic issues, recommendations
    INFO = "info"  # Informational findings


class IssueCategory(Enum):
    """Issue categories for classification."""

    SECURITY = "security"
    CONFIGURATION = "configuration"
    CONNECTIVITY = "connectivity"
    PERFORMANCE = "performance"
    DEPLOYMENT = "deployment"
    COMPATIBILITY = "compatibility"
    VALIDATION = "validation"
    UNKNOWN = "unknown"


@dataclass
class Issue:
    """Represents a single issue with severity and categorization."""

    component: str
    message: str
    severity: IssueSeverity
    category: IssueCategory
    details: Dict[str, Any] = field(default_factory=dict)
    recommendations: List[str] = field(default_factory=list)
    affects_deployment: bool = False  # Whether this blocks deployment

    def __str__(self) -> str:
        return f"[{self.severity.value.upper()}] {self.component}: {self.message}"


@dataclass
class IssueGroup:
    """Groups related issues together."""

    category: IssueCategory
    component: str
    issues: List[Issue] = field(default_factory=list)
    total_count: int = 0
    shown_count: int = 0

    @property
    def hidden_count(self) -> int:
        return self.total_count - self.shown_count

    @property
    def highest_severity(self) -> IssueSeverity:
        if not self.issues:
            return IssueSeverity.INFO
        return min(self.issues, key=lambda x: list(IssueSeverity).index(x.severity)).severity


@dataclass
class IssueSummary:
    """Summary of all issues with counts and priorities."""

    total_issues: int = 0
    by_severity: Dict[IssueSeverity, int] = field(default_factory=lambda: defaultdict(int))
    by_category: Dict[IssueCategory, int] = field(default_factory=lambda: defaultdict(int))
    by_component: Dict[str, int] = field(default_factory=lambda: defaultdict(int))
    deployment_blocking: int = 0
    top_issues: List[Issue] = field(default_factory=list)
    issue_groups: List[IssueGroup] = field(default_factory=list)


class IssueTracker:
    """Comprehensive issue tracking and reporting system."""

    def __init__(self, max_issues_per_component: int = 5, max_total_display: int = 20) -> None:
        """Initialize the issue tracker.

        Args:
            max_issues_per_component: Maximum issues to show per component
            max_total_display: Maximum total issues to display in detail

        """
        self.max_issues_per_component = max_issues_per_component
        self.max_total_display = max_total_display
        self.issues: List[Issue] = []
        self.logger = logging.getLogger(__name__)

    def add_issue(
        self,
        component: str,
        message: str,
        severity: IssueSeverity,
        category: IssueCategory,
        details: Optional[Dict[str, Any]] = None,
        recommendations: Optional[List[str]] = None,
        affects_deployment: bool = False,
    ) -> None:
        """Add a new issue to the tracker."""
        issue = Issue(
            component=component,
            message=message,
            severity=severity,
            category=category,
            details=details or {},
            recommendations=recommendations or [],
            affects_deployment=affects_deployment,
        )
        self.issues.append(issue)

    def add_issues_from_list(
        self,
        component: str,
        issues_list: List[str],
        severity: IssueSeverity,
        category: IssueCategory,
        max_display: Optional[int] = None,
    ) -> None:
        """Add multiple issues from a list with automatic counting."""
        total_count = len(issues_list)
        display_count = min(total_count, max_display or self.max_issues_per_component)

        # Add individual issues up to display limit
        for issue_msg in issues_list[:display_count]:
            self.add_issue(
                component=component, message=issue_msg, severity=severity, category=category
            )

        # Add summary issue if there are hidden items
        if total_count > display_count:
            hidden_count = total_count - display_count
            self.add_issue(
                component=component,
                message=f"... and {hidden_count} additional similar issues (total: {total_count})",
                severity=severity,
                category=category,
                details={"total_count": total_count, "hidden_count": hidden_count},
            )

    def categorize_security_issue(
        self, issue_description: str
    ) -> Tuple[IssueSeverity, IssueCategory]:
        """Automatically categorize security-related issues."""
        description_lower = issue_description.lower()

        # Critical security issues
        if any(
            term in description_lower
            for term in [
                "cluster-admin",
                "privileged",
                "root user",
                "privilege escalation",
                "cluster role binding",
                "security context missing",
            ]
        ):
            return IssueSeverity.CRITICAL, IssueCategory.SECURITY

        # High security issues
        if any(
            term in description_lower
            for term in [
                "runasnonroot",
                "capabilities",
                "seccomp",
                "pod security",
                "rbac",
                "service account token",
            ]
        ):
            return IssueSeverity.HIGH, IssueCategory.SECURITY

        # Medium security issues
        if any(
            term in description_lower
            for term in ["network policy", "tls", "certificate", "encryption"]
        ):
            return IssueSeverity.MEDIUM, IssueCategory.SECURITY

        return IssueSeverity.LOW, IssueCategory.SECURITY

    def categorize_deployment_issue(
        self, issue_description: str
    ) -> Tuple[IssueSeverity, IssueCategory]:
        """Automatically categorize deployment-related issues."""
        description_lower = issue_description.lower()

        # Critical deployment issues
        if any(
            term in description_lower
            for term in [
                "failed",
                "error",
                "crash",
                "cannot connect",
                "unreachable",
                "deployment user does not exist",
                "kubeconfig not found",
            ]
        ):
            return IssueSeverity.CRITICAL, IssueCategory.DEPLOYMENT

        # High deployment issues
        if any(
            term in description_lower
            for term in ["not ready", "pending", "timeout", "missing", "configuration"]
        ):
            return IssueSeverity.HIGH, IssueCategory.DEPLOYMENT

        return IssueSeverity.MEDIUM, IssueCategory.DEPLOYMENT

    def auto_categorize_issue(
        self, component: str, message: str
    ) -> Tuple[IssueSeverity, IssueCategory]:
        """Automatically categorize an issue based on component and message."""
        message_lower = message.lower()
        component_lower = component.lower()

        # Security-related components and messages
        if any(term in component_lower for term in ["security", "rbac", "tls", "cert"]) or any(
            term in message_lower for term in ["security", "privilege", "root", "capabilities"]
        ):
            return self.categorize_security_issue(message)

        # Deployment-related issues
        if any(term in component_lower for term in ["deployment", "user", "ansible"]) or any(
            term in message_lower for term in ["deploy", "install", "configure"]
        ):
            return self.categorize_deployment_issue(message)

        # Network/connectivity issues
        if any(term in component_lower for term in ["network", "dns", "metallb", "ingress"]) or any(
            term in message_lower for term in ["connect", "network", "dns", "timeout"]
        ):
            if "failed" in message_lower or "error" in message_lower:
                return IssueSeverity.HIGH, IssueCategory.CONNECTIVITY
            return IssueSeverity.MEDIUM, IssueCategory.CONNECTIVITY

        # Performance issues
        if any(
            term in message_lower for term in ["slow", "performance", "resource", "memory", "cpu"]
        ):
            return IssueSeverity.MEDIUM, IssueCategory.PERFORMANCE

        # Default categorization
        if any(term in message_lower for term in ["failed", "error", "critical"]):
            return IssueSeverity.HIGH, IssueCategory.UNKNOWN

        return IssueSeverity.MEDIUM, IssueCategory.UNKNOWN

    def add_auto_categorized_issue(
        self,
        component: str,
        message: str,
        details: Optional[Dict[str, Any]] = None,
        recommendations: Optional[List[str]] = None,
    ) -> None:
        """Add an issue with automatic severity and category detection."""
        severity, category = self.auto_categorize_issue(component, message)

        # Deployment blocking logic
        affects_deployment = severity in [
            IssueSeverity.CRITICAL,
            IssueSeverity.HIGH,
        ] and category in [
            IssueCategory.SECURITY,
            IssueCategory.DEPLOYMENT,
            IssueCategory.CONNECTIVITY,
        ]

        self.add_issue(
            component=component,
            message=message,
            severity=severity,
            category=category,
            details=details,
            recommendations=recommendations,
            affects_deployment=affects_deployment,
        )

    def generate_summary(self) -> IssueSummary:
        """Generate a comprehensive summary of all issues."""
        summary = IssueSummary()
        summary.total_issues = len(self.issues)

        # Count by severity
        for issue in self.issues:
            summary.by_severity[issue.severity] += 1
            summary.by_category[issue.category] += 1
            summary.by_component[issue.component] += 1
            if issue.affects_deployment:
                summary.deployment_blocking += 1

        # Sort issues by severity and get top issues
        severity_order = {s: i for i, s in enumerate(IssueSeverity)}
        sorted_issues = sorted(
            self.issues,
            key=lambda x: (
                severity_order[x.severity],
                x.affects_deployment and -1 or 0,  # Deployment blocking issues first
                x.component,
                x.message,
            ),
        )

        summary.top_issues = sorted_issues[: self.max_total_display]

        # Group issues by component and category
        groups = defaultdict(lambda: defaultdict(list))
        for issue in self.issues:
            groups[issue.component][issue.category].append(issue)

        for component, categories in groups.items():
            for category, issues in categories.items():
                group = IssueGroup(
                    category=category,
                    component=component,
                    issues=issues[: self.max_issues_per_component],
                    total_count=len(issues),
                    shown_count=min(len(issues), self.max_issues_per_component),
                )
                summary.issue_groups.append(group)

        # Sort groups by highest severity
        summary.issue_groups.sort(key=lambda g: severity_order[g.highest_severity])

        return summary

    def get_critical_issues(self) -> List[Issue]:
        """Get all critical issues that must be addressed."""
        return [issue for issue in self.issues if issue.severity == IssueSeverity.CRITICAL]

    def get_deployment_blocking_issues(self) -> List[Issue]:
        """Get all issues that would block deployment."""
        return [issue for issue in self.issues if issue.affects_deployment]

    def format_summary_report(self, summary: Optional[IssueSummary] = None) -> str:
        """Format a comprehensive summary report."""
        if summary is None:
            summary = self.generate_summary()

        if summary.total_issues == 0:
            return "✅ No issues found - system is healthy!"

        report = []
        report.append("# Issue Summary Report")
        report.append("")

        # Overall statistics
        report.append(f"**Total Issues Found**: {summary.total_issues}")
        report.append(f"**Deployment Blocking**: {summary.deployment_blocking}")
        report.append("")

        # Severity breakdown
        report.append("## Issues by Severity")
        for severity in IssueSeverity:
            count = summary.by_severity[severity]
            if count > 0:
                icon = {"critical": "🚨", "high": "⚠️", "medium": "⚡", "low": "ℹ️", "info": "📝"}[
                    severity.value
                ]
                report.append(f"- {icon} **{severity.value.title()}**: {count}")
        report.append("")

        # Category breakdown
        report.append("## Issues by Category")
        for category in IssueCategory:
            count = summary.by_category[category]
            if count > 0:
                report.append(f"- **{category.value.title()}**: {count}")
        report.append("")

        # Critical issues (always show all)
        critical_issues = self.get_critical_issues()
        if critical_issues:
            report.append("## 🚨 Critical Issues (Must Fix)")
            for issue in critical_issues:
                report.append(f"- **{issue.component}**: {issue.message}")
                if issue.recommendations:
                    for rec in issue.recommendations[:2]:  # Show top 2 recommendations
                        report.append(f"  - 💡 {rec}")
            report.append("")

        # Deployment blocking issues
        blocking_issues = self.get_deployment_blocking_issues()
        if blocking_issues and len(blocking_issues) > len(critical_issues):
            report.append("## ⚠️ Deployment Blocking Issues")
            non_critical_blocking = [
                i for i in blocking_issues if i.severity != IssueSeverity.CRITICAL
            ]
            for issue in non_critical_blocking[:10]:  # Limit to top 10
                report.append(f"- **{issue.component}**: {issue.message}")

            if len(non_critical_blocking) > 10:
                report.append(
                    f"- ... and {len(non_critical_blocking) - 10} more deployment blocking issues"
                )
            report.append("")

        # Top issues by component
        report.append("## Top Issues by Component")
        component_counts = Counter(issue.component for issue in self.issues)
        for component, count in component_counts.most_common(10):
            component_issues = [i for i in summary.top_issues if i.component == component]
            if component_issues:
                highest_severity = min(
                    component_issues, key=lambda x: list(IssueSeverity).index(x.severity)
                )
                severity_icon = {
                    "critical": "🚨",
                    "high": "⚠️",
                    "medium": "⚡",
                    "low": "ℹ️",
                    "info": "📝",
                }[highest_severity.severity.value]
                report.append(f"### {severity_icon} {component} ({count} issues)")

                # Show top issues for this component
                for issue in component_issues[:3]:
                    report.append(f"- {issue.message}")

                if count > 3:
                    report.append(f"- ... and {count - 3} more issues")
                report.append("")

        # Summary recommendations
        if summary.deployment_blocking > 0:
            report.append("## 🔧 Next Steps")
            report.append(
                "1. **Immediate Action Required**: Fix critical and deployment-blocking issues first"
            )
            report.append("2. **Security Review**: Address high-severity security issues")
            report.append("3. **Configuration**: Review and update configuration-related issues")
            report.append("4. **Validation**: Re-run tests after addressing issues")
            report.append("")

        return "\n".join(report)

    def clear(self) -> None:
        """Clear all tracked issues."""
        self.issues.clear()


# Utility functions for common issue patterns
def create_missing_items_issues(
    tracker: IssueTracker,
    component: str,
    missing_items: List[str],
    item_type: str,
    severity: IssueSeverity = IssueSeverity.HIGH,
    category: IssueCategory = IssueCategory.CONFIGURATION,
) -> None:
    """Create issues for missing items with proper counting."""
    if not missing_items:
        return

    total_count = len(missing_items)

    if total_count == 1:
        tracker.add_issue(
            component=component,
            message=f"Missing {item_type}: {missing_items[0]}",
            severity=severity,
            category=category,
            affects_deployment=severity in [IssueSeverity.CRITICAL, IssueSeverity.HIGH],
        )
    else:
        # Show first few items and total count
        display_count = min(3, total_count)
        shown_items = ", ".join(missing_items[:display_count])

        if total_count > display_count:
            message = f"Missing {total_count} {item_type}(s): {shown_items} ... and {total_count - display_count} more"
        else:
            message = f"Missing {total_count} {item_type}(s): {shown_items}"

        tracker.add_issue(
            component=component,
            message=message,
            severity=severity,
            category=category,
            details={"total_count": total_count, "missing_items": missing_items},
            affects_deployment=severity in [IssueSeverity.CRITICAL, IssueSeverity.HIGH],
        )


def create_validation_failure_issues(
    tracker: IssueTracker,
    component: str,
    failed_validations: List[str],
    validation_type: str = "validation",
) -> None:
    """Create issues for validation failures."""
    if not failed_validations:
        return

    total_count = len(failed_validations)
    severity = IssueSeverity.CRITICAL if total_count > 5 else IssueSeverity.HIGH

    tracker.add_issues_from_list(
        component=component,
        issues_list=failed_validations,
        severity=severity,
        category=IssueCategory.VALIDATION,
    )


def create_security_context_issues(
    tracker: IssueTracker,
    component: str,
    privileged_containers: List[str],
    missing_contexts: List[str],
) -> None:
    """Create security context related issues with proper categorization."""
    if privileged_containers:
        create_missing_items_issues(
            tracker=tracker,
            component=component,
            missing_items=privileged_containers,
            item_type="privileged container",
            severity=IssueSeverity.CRITICAL,
            category=IssueCategory.SECURITY,
        )

    if missing_contexts:
        create_missing_items_issues(
            tracker=tracker,
            component=component,
            missing_items=missing_contexts,
            item_type="security context",
            severity=IssueSeverity.HIGH,
            category=IssueCategory.SECURITY,
        )
