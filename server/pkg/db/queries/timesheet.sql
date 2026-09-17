-- name: CreateTimeEntry :one
INSERT INTO time_entry (workspace_id, issue_id, logged_by_type, logged_by_id, duration_seconds, minutes, description, task_type, risk_level, month)
VALUES ($1, $2, $3, $4, $5, $5 / 60, $6, $7, $8, $9)
RETURNING *;

-- name: ListTimeEntriesByIssue :many
SELECT * FROM time_entry
WHERE issue_id = $1
ORDER BY created_at DESC;

-- name: ListTimeEntriesByWorkspaceMonth :many
SELECT * FROM time_entry
WHERE workspace_id = $1 AND month = $2
ORDER BY created_at DESC;

-- name: SumTimeByWorkspaceMonth :one
SELECT COALESCE(SUM(duration_seconds), 0)::bigint AS total_seconds
FROM time_entry
WHERE workspace_id = $1 AND month = $2;

-- name: SumTimeByWorkspaceMonthGrouped :many
SELECT
    month,
    task_type,
    COUNT(*)::bigint AS entry_count,
    COALESCE(SUM(duration_seconds), 0)::bigint AS total_seconds
FROM time_entry
WHERE workspace_id = $1 AND month >= $2 AND month <= $3
GROUP BY month, task_type
ORDER BY month DESC, total_seconds DESC;

-- name: DeleteTimeEntry :exec
DELETE FROM time_entry WHERE id = $1 AND workspace_id = $2;
