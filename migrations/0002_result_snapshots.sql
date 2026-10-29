ALTER TABLE human_runs ADD COLUMN result_json TEXT CHECK (result_json IS NULL OR json_valid(result_json));
