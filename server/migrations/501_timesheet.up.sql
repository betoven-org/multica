-- Timesheet system: contracted hours per workspace + time entries per issue.
--
-- workspace.settings gets "contracted_hours_monthly" via application code.
-- time_entry tracks estimated human-equivalent time per issue.
-- Monthly report: SUM(time_entry.minutes) vs workspace contracted hours.

CREATE TABLE time_entry (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id UUID NOT NULL,
    issue_id UUID NOT NULL,
    -- Who logged: pipeline (automatic) or member (manual)
    logged_by_type TEXT NOT NULL DEFAULT 'pipeline' CHECK (logged_by_type IN ('pipeline', 'member')),
    logged_by_id UUID,
    -- Time in minutes (human-equivalent estimate)
    minutes INT NOT NULL CHECK (minutes > 0),
    -- Description of what was done
    description TEXT NOT NULL DEFAULT '',
    -- Task metadata at time of logging
    task_type TEXT NOT NULL DEFAULT '',
    risk_level TEXT NOT NULL DEFAULT '',
    -- Month for aggregation (YYYY-MM)
    month TEXT NOT NULL DEFAULT to_char(now(), 'YYYY-MM'),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
