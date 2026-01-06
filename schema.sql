PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS organizations (
  organization_id TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  domain TEXT NOT NULL,
  created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS teams (
  team_id TEXT PRIMARY KEY,
  organization_id TEXT NOT NULL,
  name TEXT NOT NULL,
  team_type TEXT NOT NULL,
  created_at TEXT NOT NULL,
  FOREIGN KEY (organization_id) REFERENCES organizations(organization_id)
);

CREATE TABLE IF NOT EXISTS users (
  user_id TEXT PRIMARY KEY,
  organization_id TEXT NOT NULL,
  email TEXT NOT NULL,
  full_name TEXT NOT NULL,
  title TEXT NOT NULL,
  department TEXT NOT NULL,
  location TEXT NOT NULL,
  role TEXT NOT NULL,
  manager_user_id TEXT,
  hire_date TEXT NOT NULL,
  created_at TEXT NOT NULL,
  deactivated_at TEXT,
  FOREIGN KEY (organization_id) REFERENCES organizations(organization_id),
  FOREIGN KEY (manager_user_id) REFERENCES users(user_id)
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_users_email ON users(email);

CREATE TABLE IF NOT EXISTS team_memberships (
  team_id TEXT NOT NULL,
  user_id TEXT NOT NULL,
  is_team_admin INTEGER NOT NULL DEFAULT 0,
  joined_at TEXT NOT NULL,
  left_at TEXT,
  PRIMARY KEY (team_id, user_id),
  FOREIGN KEY (team_id) REFERENCES teams(team_id),
  FOREIGN KEY (user_id) REFERENCES users(user_id)
);

CREATE TABLE IF NOT EXISTS projects (
  project_id TEXT PRIMARY KEY,
  organization_id TEXT NOT NULL,
  owner_team_id TEXT NOT NULL,
  name TEXT NOT NULL,
  project_type TEXT NOT NULL,
  privacy TEXT NOT NULL,
  status TEXT NOT NULL,
  start_date TEXT,
  due_date TEXT,
  created_at TEXT NOT NULL,
  archived_at TEXT,
  description TEXT,
  FOREIGN KEY (organization_id) REFERENCES organizations(organization_id),
  FOREIGN KEY (owner_team_id) REFERENCES teams(team_id)
);

CREATE INDEX IF NOT EXISTS idx_projects_team ON projects(owner_team_id);

CREATE TABLE IF NOT EXISTS sections (
  section_id TEXT PRIMARY KEY,
  project_id TEXT NOT NULL,
  name TEXT NOT NULL,
  position INTEGER NOT NULL,
  created_at TEXT NOT NULL,
  FOREIGN KEY (project_id) REFERENCES projects(project_id)
);

CREATE INDEX IF NOT EXISTS idx_sections_project ON sections(project_id);

CREATE TABLE IF NOT EXISTS tasks (
  task_id TEXT PRIMARY KEY,
  project_id TEXT NOT NULL,
  section_id TEXT NOT NULL,
  name TEXT NOT NULL,
  description TEXT,
  creator_user_id TEXT NOT NULL,
  assignee_user_id TEXT,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  start_date TEXT,
  due_date TEXT,
  completed INTEGER NOT NULL,
  completed_at TEXT,
  FOREIGN KEY (project_id) REFERENCES projects(project_id),
  FOREIGN KEY (section_id) REFERENCES sections(section_id),
  FOREIGN KEY (creator_user_id) REFERENCES users(user_id),
  FOREIGN KEY (assignee_user_id) REFERENCES users(user_id)
);

CREATE INDEX IF NOT EXISTS idx_tasks_project ON tasks(project_id);
CREATE INDEX IF NOT EXISTS idx_tasks_assignee ON tasks(assignee_user_id);
CREATE INDEX IF NOT EXISTS idx_tasks_created_at ON tasks(created_at);

CREATE TABLE IF NOT EXISTS subtasks (
  subtask_id TEXT PRIMARY KEY,
  parent_task_id TEXT NOT NULL,
  name TEXT NOT NULL,
  description TEXT,
  creator_user_id TEXT NOT NULL,
  assignee_user_id TEXT,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  due_date TEXT,
  completed INTEGER NOT NULL,
  completed_at TEXT,
  FOREIGN KEY (parent_task_id) REFERENCES tasks(task_id),
  FOREIGN KEY (creator_user_id) REFERENCES users(user_id),
  FOREIGN KEY (assignee_user_id) REFERENCES users(user_id)
);

CREATE INDEX IF NOT EXISTS idx_subtasks_parent ON subtasks(parent_task_id);

CREATE TABLE IF NOT EXISTS comments (
  comment_id TEXT PRIMARY KEY,
  author_user_id TEXT NOT NULL,
  task_id TEXT,
  subtask_id TEXT,
  body TEXT NOT NULL,
  created_at TEXT NOT NULL,
  FOREIGN KEY (author_user_id) REFERENCES users(user_id),
  FOREIGN KEY (task_id) REFERENCES tasks(task_id),
  FOREIGN KEY (subtask_id) REFERENCES subtasks(subtask_id),
  CHECK (
    (task_id IS NOT NULL AND subtask_id IS NULL) OR
    (task_id IS NULL AND subtask_id IS NOT NULL)
  )
);

CREATE INDEX IF NOT EXISTS idx_comments_task ON comments(task_id);
CREATE INDEX IF NOT EXISTS idx_comments_subtask ON comments(subtask_id);

CREATE TABLE IF NOT EXISTS tags (
  tag_id TEXT PRIMARY KEY,
  organization_id TEXT NOT NULL,
  name TEXT NOT NULL,
  color TEXT NOT NULL,
  created_at TEXT NOT NULL,
  FOREIGN KEY (organization_id) REFERENCES organizations(organization_id)
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_tags_org_name ON tags(organization_id, name);

CREATE TABLE IF NOT EXISTS task_tags (
  task_id TEXT,
  subtask_id TEXT,
  tag_id TEXT NOT NULL,
  added_at TEXT NOT NULL,
  PRIMARY KEY (tag_id, task_id, subtask_id),
  FOREIGN KEY (task_id) REFERENCES tasks(task_id),
  FOREIGN KEY (subtask_id) REFERENCES subtasks(subtask_id),
  FOREIGN KEY (tag_id) REFERENCES tags(tag_id),
  CHECK (
    (task_id IS NOT NULL AND subtask_id IS NULL) OR
    (task_id IS NULL AND subtask_id IS NOT NULL)
  )
);

CREATE INDEX IF NOT EXISTS idx_task_tags_task ON task_tags(task_id);

CREATE TABLE IF NOT EXISTS custom_field_definitions (
  custom_field_id TEXT PRIMARY KEY,
  organization_id TEXT NOT NULL,
  name TEXT NOT NULL,
  field_type TEXT NOT NULL,
  enum_options_json TEXT,
  created_at TEXT NOT NULL,
  FOREIGN KEY (organization_id) REFERENCES organizations(organization_id)
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_cfd_org_name ON custom_field_definitions(organization_id, name);

CREATE TABLE IF NOT EXISTS project_custom_fields (
  project_id TEXT NOT NULL,
  custom_field_id TEXT NOT NULL,
  is_required INTEGER NOT NULL DEFAULT 0,
  created_at TEXT NOT NULL,
  PRIMARY KEY (project_id, custom_field_id),
  FOREIGN KEY (project_id) REFERENCES projects(project_id),
  FOREIGN KEY (custom_field_id) REFERENCES custom_field_definitions(custom_field_id)
);

CREATE TABLE IF NOT EXISTS custom_field_values (
  custom_field_value_id TEXT PRIMARY KEY,
  custom_field_id TEXT NOT NULL,
  task_id TEXT,
  subtask_id TEXT,
  value_text TEXT,
  value_number REAL,
  value_enum TEXT,
  created_at TEXT NOT NULL,
  FOREIGN KEY (custom_field_id) REFERENCES custom_field_definitions(custom_field_id),
  FOREIGN KEY (task_id) REFERENCES tasks(task_id),
  FOREIGN KEY (subtask_id) REFERENCES subtasks(subtask_id),
  CHECK (
    (task_id IS NOT NULL AND subtask_id IS NULL) OR
    (task_id IS NULL AND subtask_id IS NOT NULL)
  )
);

CREATE INDEX IF NOT EXISTS idx_cfv_task ON custom_field_values(task_id);

CREATE TABLE IF NOT EXISTS attachments (
  attachment_id TEXT PRIMARY KEY,
  task_id TEXT,
  subtask_id TEXT,
  uploader_user_id TEXT NOT NULL,
  file_name TEXT NOT NULL,
  file_type TEXT NOT NULL,
  file_size_bytes INTEGER NOT NULL,
  created_at TEXT NOT NULL,
  url TEXT,
  FOREIGN KEY (task_id) REFERENCES tasks(task_id),
  FOREIGN KEY (subtask_id) REFERENCES subtasks(subtask_id),
  FOREIGN KEY (uploader_user_id) REFERENCES users(user_id),
  CHECK (
    (task_id IS NOT NULL AND subtask_id IS NULL) OR
    (task_id IS NULL AND subtask_id IS NOT NULL)
  )
);

CREATE INDEX IF NOT EXISTS idx_attachments_task ON attachments(task_id);
