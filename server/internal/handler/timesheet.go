package handler

import (
	"encoding/json"
	"fmt"
	"net/http"
	"time"

	"github.com/jackc/pgx/v5/pgtype"
	db "github.com/multica-ai/multica/server/pkg/db/generated"
)

// --- Request/Response types ---

type CreateTimeEntryRequest struct {
	IssueID         string `json:"issue_id"`
	DurationSeconds int32  `json:"duration_seconds"`
	Description     string `json:"description"`
	TaskType        string `json:"task_type"`
	RiskLevel       string `json:"risk_level"`
	LoggedByType    string `json:"logged_by_type"`
}

type TimeEntryResponse struct {
	ID              string `json:"id"`
	WorkspaceID     string `json:"workspace_id"`
	IssueID         string `json:"issue_id"`
	LoggedByType    string `json:"logged_by_type"`
	LoggedByID      string `json:"logged_by_id"`
	DurationSeconds int32  `json:"duration_seconds"`
	Duration        string `json:"duration"` // hh:mm:ss
	Description     string `json:"description"`
	TaskType        string `json:"task_type"`
	RiskLevel       string `json:"risk_level"`
	Month           string `json:"month"`
	CreatedAt       string `json:"created_at"`
}

type TimesheetSummaryResponse struct {
	WorkspaceID     string                   `json:"workspace_id"`
	Month           string                   `json:"month"`
	TotalSeconds    int64                    `json:"total_seconds"`
	TotalDuration   string                   `json:"total_duration"` // hh:mm:ss
	TotalHours      float64                  `json:"total_hours"`
	ContractedHours float64                  `json:"contracted_hours"`
	UsagePercent    float64                  `json:"usage_percent"`
	ByType          []TimesheetTypeBreakdown `json:"by_type"`
}

type TimesheetTypeBreakdown struct {
	Month         string  `json:"month"`
	TaskType      string  `json:"task_type"`
	EntryCount    int64   `json:"entry_count"`
	TotalSeconds  int64   `json:"total_seconds"`
	TotalDuration string  `json:"total_duration"` // hh:mm:ss
	TotalHours    float64 `json:"total_hours"`
}

func formatDuration(seconds int64) string {
	h := seconds / 3600
	m := (seconds % 3600) / 60
	s := seconds % 60
	return fmt.Sprintf("%02d:%02d:%02d", h, m, s)
}

// --- Handlers ---

func (h *Handler) CreateTimeEntry(w http.ResponseWriter, r *http.Request) {
	workspaceID := h.resolveWorkspaceID(r)
	_, ok := h.workspaceMember(w, r, workspaceID)
	if !ok {
		return
	}

	var req CreateTimeEntryRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		writeError(w, http.StatusBadRequest, "invalid request body")
		return
	}

	if req.IssueID == "" || req.DurationSeconds <= 0 {
		writeError(w, http.StatusBadRequest, "issue_id and duration_seconds > 0 are required")
		return
	}

	loggedByType := req.LoggedByType
	if loggedByType == "" {
		loggedByType = "pipeline"
	}

	month := time.Now().UTC().Format("2006-01")
	userID := requestUserID(r)
	var loggedByID pgtype.UUID
	if userID != "" {
		loggedByID = parseUUID(userID)
	}

	entry, err := h.Queries.CreateTimeEntry(r.Context(), db.CreateTimeEntryParams{
		WorkspaceID:     parseUUID(workspaceID),
		IssueID:         parseUUID(req.IssueID),
		LoggedByType:    loggedByType,
		LoggedByID:      loggedByID,
		DurationSeconds: req.DurationSeconds,
		Description:     req.Description,
		TaskType:        req.TaskType,
		RiskLevel:       req.RiskLevel,
		Month:           month,
	})
	if err != nil {
		writeError(w, http.StatusInternalServerError, fmt.Sprintf("failed to create time entry: %v", err))
		return
	}

	writeJSON(w, http.StatusCreated, timeEntryToResponse(entry))
}

func (h *Handler) ListTimeEntries(w http.ResponseWriter, r *http.Request) {
	workspaceID := h.resolveWorkspaceID(r)
	_, ok := h.workspaceMember(w, r, workspaceID)
	if !ok {
		return
	}

	month := r.URL.Query().Get("month")
	if month == "" {
		month = time.Now().UTC().Format("2006-01")
	}

	entries, err := h.Queries.ListTimeEntriesByWorkspaceMonth(r.Context(), db.ListTimeEntriesByWorkspaceMonthParams{
		WorkspaceID: parseUUID(workspaceID),
		Month:       month,
	})
	if err != nil {
		writeError(w, http.StatusInternalServerError, "failed to list time entries")
		return
	}

	resp := make([]TimeEntryResponse, len(entries))
	for i, e := range entries {
		resp[i] = timeEntryToResponse(e)
	}
	writeJSON(w, http.StatusOK, resp)
}

func (h *Handler) GetTimesheetSummary(w http.ResponseWriter, r *http.Request) {
	workspaceID := h.resolveWorkspaceID(r)
	_, ok := h.workspaceMember(w, r, workspaceID)
	if !ok {
		return
	}

	month := r.URL.Query().Get("month")
	if month == "" {
		month = time.Now().UTC().Format("2006-01")
	}

	totalSeconds, err := h.Queries.SumTimeByWorkspaceMonth(r.Context(), db.SumTimeByWorkspaceMonthParams{
		WorkspaceID: parseUUID(workspaceID),
		Month:       month,
	})
	if err != nil {
		writeError(w, http.StatusInternalServerError, "failed to sum time entries")
		return
	}

	breakdown, err := h.Queries.SumTimeByWorkspaceMonthGrouped(r.Context(), db.SumTimeByWorkspaceMonthGroupedParams{
		WorkspaceID: parseUUID(workspaceID),
		Month:       month,
		Month_2:     month,
	})
	if err != nil {
		writeError(w, http.StatusInternalServerError, "failed to get breakdown")
		return
	}

	ws, err := h.Queries.GetWorkspace(r.Context(), parseUUID(workspaceID))
	if err != nil {
		writeError(w, http.StatusInternalServerError, "failed to get workspace")
		return
	}

	var settings map[string]interface{}
	json.Unmarshal(ws.Settings, &settings)
	contractedHours := 0.0
	if ch, ok := settings["contracted_hours_monthly"]; ok {
		if v, ok := ch.(float64); ok {
			contractedHours = v
		}
	}

	totalHours := float64(totalSeconds) / 3600.0
	usagePercent := 0.0
	if contractedHours > 0 {
		usagePercent = (totalHours / contractedHours) * 100
	}

	byType := make([]TimesheetTypeBreakdown, len(breakdown))
	for i, b := range breakdown {
		byType[i] = TimesheetTypeBreakdown{
			Month:         b.Month,
			TaskType:      b.TaskType,
			EntryCount:    b.EntryCount,
			TotalSeconds:  b.TotalSeconds,
			TotalDuration: formatDuration(b.TotalSeconds),
			TotalHours:    float64(b.TotalSeconds) / 3600.0,
		}
	}

	writeJSON(w, http.StatusOK, TimesheetSummaryResponse{
		WorkspaceID:     workspaceID,
		Month:           month,
		TotalSeconds:    totalSeconds,
		TotalDuration:   formatDuration(totalSeconds),
		TotalHours:      totalHours,
		ContractedHours: contractedHours,
		UsagePercent:    usagePercent,
		ByType:          byType,
	})
}

func timeEntryToResponse(e db.TimeEntry) TimeEntryResponse {
	return TimeEntryResponse{
		ID:              uuidToString(e.ID),
		WorkspaceID:     uuidToString(e.WorkspaceID),
		IssueID:         uuidToString(e.IssueID),
		LoggedByType:    e.LoggedByType,
		LoggedByID:      uuidToString(e.LoggedByID),
		DurationSeconds: e.DurationSeconds,
		Duration:        formatDuration(int64(e.DurationSeconds)),
		Description:     e.Description,
		TaskType:        e.TaskType,
		RiskLevel:       e.RiskLevel,
		Month:           e.Month,
		CreatedAt:       e.CreatedAt.Time.Format(time.RFC3339),
	}
}
