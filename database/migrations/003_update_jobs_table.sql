ALTER TABLE jobs
ADD COLUMN IF NOT EXISTS failed_step_id UUID REFERENCES steps(id) ON DELETE SET NULL,
ADD COLUMN IF NOT EXISTS failed_agent_id VARCHAR(50);

CREATE INDEX IF NOT EXISTS idx_jobs_failed_step_id ON jobs(failed_step_id);
CREATE INDEX IF NOT EXISTS idx_jobs_failed_agent_id ON jobs(failed_agent_id);

