CREATE TABLE IF NOT EXISTS job_requests (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    job_id UUID NOT NULL REFERENCES jobs(id) ON DELETE CASCADE,
    repository_url TEXT NOT NULL,
    access_token TEXT NOT NULL,
    user_input TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(job_id)
);

CREATE INDEX IF NOT EXISTS idx_job_requests_job_id ON job_requests(job_id);
CREATE INDEX IF NOT EXISTS idx_job_requests_repository_url ON job_requests(repository_url);

