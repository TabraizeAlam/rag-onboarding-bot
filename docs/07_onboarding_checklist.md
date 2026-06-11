# New Hire Onboarding Checklist

## Week 1: Get Set Up

### Day 1
- [ ] Receive laptop from IT and complete initial setup (FileVault/BitLocker encryption required)
- [ ] Set up Google Workspace account (email, Calendar, Meet)
- [ ] Join Slack and set up profile with full name, role, and photo
- [ ] Join all required Slack channels (see `04_tools_and_access.md`)
- [ ] Attend New Hire Orientation with HR (9 AM, Conference Room A / Zoom)
- [ ] Meet with your Engineering Manager (David Park or squad lead) for a 1:1 welcome call
- [ ] Get GitHub org access — request via IT portal, expected by EOD

### Day 2–3
- [ ] Complete developer environment setup (see `02_dev_environment_setup.md`)
- [ ] Clone and successfully run your squad's primary repository locally
- [ ] Configure AWS SSO with profile `acme-dev`
- [ ] Request access to required tools via IT portal (Jira, Datadog, Terraform Cloud)
- [ ] Set up 1Password and store any personal credentials there
- [ ] Install and configure Tailscale VPN
- [ ] Shadow your squad lead or a buddy engineer for half a day

### Day 4–5
- [ ] Read the Architecture Overview (`06_architecture_overview.md`)
- [ ] Read the Engineering Processes doc (`05_engineering_processes.md`)
- [ ] Attend your first team standup
- [ ] Open and merge your first "Hello World" PR (update the team roster in Confluence or fix a doc typo)
- [ ] Set up your Jira account and view the current sprint board
- [ ] Meet with your assigned onboarding buddy for lunch/coffee

## Week 2: Start Contributing

- [ ] Be assigned your first real ticket (XS or S size) in Jira
- [ ] Attend sprint planning if it falls in Week 2
- [ ] Complete the Security Awareness Training (link in your email from IT)
- [ ] Complete the Data Privacy training (mandatory, required within 14 days of start)
- [ ] Set up recurring 1:1 with your Engineering Manager (weekly for first 90 days)
- [ ] Read on-call runbooks for your squad (Confluence > Platform Engineering > On-Call Runbooks)
- [ ] Shadow an on-call rotation week (observe, do not respond solo yet)

## Week 3–4: Build Confidence

- [ ] Submit your second PR independently (no hand-holding)
- [ ] Conduct your first code review for a teammate
- [ ] Attend an Architecture Review meeting and ask at least one question
- [ ] Review and understand the deployment process (`03_deployment_process.md`)
- [ ] Run a staging deployment for any service (with your buddy observing)
- [ ] Complete HR-required compliance training modules (in Workday)

## 30-Day Check-In (with your Manager)

Your manager will schedule a 30-day check-in. Come prepared to discuss:
- What's going well?
- What's unclear or confusing?
- What do you want to learn in the next 30 days?
- Are there any blockers to your productivity?

## 60-Day Milestones

By day 60 you should be able to:
- [ ] Independently own and close tickets without asking for help at every step
- [ ] Participate in PR reviews with substantive feedback
- [ ] Know who to go to for questions on each part of the stack
- [ ] Run a production deployment (with approval) from start to finish
- [ ] Be added to the on-call rotation schedule

## Key Contacts for New Hires

| Who | Role | Slack | When to contact |
|-----|------|-------|----------------|
| Your onboarding buddy | Peer engineer | Assigned on Day 1 | First point of contact for "dumb questions" |
| David Park | Engineering Manager | @david.park | Career, process, team concerns |
| Sarah Chen | Team Lead | @sarah.chen | Technical architecture, escalations |
| #help-desk | IT Support | Slack channel | Tool access, laptop issues |
| #devex-team | Developer Experience | Slack channel | Dev environment issues |
| #infra-team | Infrastructure | Slack channel | AWS, Kubernetes, cloud access |

## FAQ for New Hires

**Q: How do I request time off?**
Use Workday (workday.acme.com). Submit at least 2 weeks ahead for 3+ days. Inform your manager and mark your Google Calendar as Out of Office.

**Q: Where do I find the on-call schedule?**
PagerDuty at `acme.pagerduty.com`. You can also see it in #infra-team channel — the current on-call posts a message every Monday.

**Q: What if I break something in production?**
Stay calm. Post immediately in #incidents. Call your squad lead if it's P0/P1. Never try to fix production quietly on your own. Blameless culture — the system that allowed the mistake is the problem, not you.

**Q: How do I propose a technical change (new tool, architecture change)?**
Write an RFC (Request for Comments) doc using the template in Confluence (Platform Engineering > RFC Template). Post in #team-general. Architecture Review discusses RFCs on Wednesdays.

**Q: Who approves expenses?**
Submit in Concur (concur.acme.com). Your manager approves up to $500. Above that, VP Engineering approval needed. Home office setup budget: $1,000 (use within first 90 days).
