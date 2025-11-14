ALTER TABLE jobs
ADD COLUMN IF NOT EXISTS access_token TEXT;

CREATE INDEX IF NOT EXISTS idx_jobs_access_token ON jobs(access_token) WHERE access_token IS NOT NULL;

