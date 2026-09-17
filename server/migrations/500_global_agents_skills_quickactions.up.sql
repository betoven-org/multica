-- Global agents, skills, and quick actions.
--
-- Adds is_global flag to agent, skill, and quick_action tables.
-- Global items are visible in ALL workspaces, not just the workspace_id they
-- belong to. The owning workspace acts as the "home" workspace (for management).
--
-- This lets a self-hosted deployment define agents, skills, and quick actions
-- once in a master workspace and have them appear in every client workspace.

ALTER TABLE agent ADD COLUMN IF NOT EXISTS is_global BOOLEAN NOT NULL DEFAULT false;
ALTER TABLE skill ADD COLUMN IF NOT EXISTS is_global BOOLEAN NOT NULL DEFAULT false;
ALTER TABLE quick_action ADD COLUMN IF NOT EXISTS is_global BOOLEAN NOT NULL DEFAULT false;
ALTER TABLE squad ADD COLUMN IF NOT EXISTS is_global BOOLEAN NOT NULL DEFAULT false;
