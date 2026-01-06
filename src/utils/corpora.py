from __future__ import annotations

DEPARTMENTS = [
    "Engineering",
    "Product",
    "Design",
    "QA",
    "Data",
    "Marketing",
    "Sales",
    "Customer Success",
    "Operations",
    "IT",
    "Security",
    "People",
    "Finance",
    "Legal",
    "RevOps",
]

LOCATIONS = [
    "Bengaluru, IN",
    "Hyderabad, IN",
    "Pune, IN",
    "Gurugram, IN",
    "Chennai, IN",
    "San Francisco, US",
    "New York, US",
    "Austin, US",
    "London, UK",
    "Dublin, IE",
    "Berlin, DE",
    "Singapore",
    "Sydney, AU",
]

ENG_AREAS = [
    "Auth",
    "Billing",
    "Search",
    "Notifications",
    "Integrations",
    "Data Pipeline",
    "Web App",
    "Mobile",
    "API Gateway",
    "Observability",
    "Permissions",
    "Reporting",
    "Onboarding",
    "Performance",
]

PRODUCT_AREAS = [
    "Activation",
    "Retention",
    "Collaboration",
    "Analytics",
    "Admin",
    "Marketplace",
    "Enterprise",
    "Security",
    "Mobile Experience",
]

MARKETING_CAMPAIGNS = [
    "Q1 Demand Gen",
    "Spring Product Launch",
    "Partner Webinar Series",
    "ABM Tier-1 Outreach",
    "Customer Stories",
    "G2 Reviews Drive",
    "Developer Community Push",
    "SEO Refresh",
]

OPS_INITIATIVES = [
    "SOC2 Evidence Collection",
    "Quarterly Access Review",
    "Vendor Renewal Cycle",
    "Incident Response Runbook",
    "IT Asset Audit",
    "Headcount Planning",
    "Onboarding Automation",
]

PROJECT_TEMPLATES = {
    "sprint": ["Backlog", "Ready", "In Progress", "Code Review", "QA", "Done"],
    "bug_triage": ["New", "Investigating", "Fix In Progress", "Ready for QA", "Closed"],
    "product_roadmap": ["Discovery", "Design", "Build", "Beta", "Launched"],
    "marketing_campaign": ["Ideas", "Planned", "In Progress", "Review", "Scheduled", "Complete"],
    "content_calendar": ["Backlog", "Draft", "Review", "Approved", "Published"],
    "ops_initiative": ["Intake", "Triage", "In Progress", "Blocked", "Done"],
    "sales_enablement": ["Requests", "In Progress", "Review", "Published"],
}

TAG_COLORS = ["red", "orange", "yellow", "green", "teal", "blue", "purple", "pink", "gray"]

FILE_TYPES = ["pdf", "docx", "xlsx", "pptx", "png", "jpg", "csv", "txt"]

PRIORITY_ENUM = ["P0", "P1", "P2", "P3"]

STATUS_ENUM = ["Not Started", "In Progress", "Blocked", "In Review", "Done"]

CUSTOMER_IMPACT_ENUM = ["Low", "Medium", "High", "Critical"]

CHANNEL_ENUM = ["Email", "Paid Search", "Organic Search", "Social", "Webinar", "Partner", "In-App"]

REGION_ENUM = ["NA", "EMEA", "APAC", "LATAM"]
