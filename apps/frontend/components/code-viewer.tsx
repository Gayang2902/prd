"use client";

import dynamic from "next/dynamic";
import type { Finding } from "@/lib/api/findings";

const Editor = dynamic(
  () => import("@monaco-editor/react").then((m) => m.default),
  {
    ssr: false,
    loading: () => <div className="h-full bg-muted animate-pulse" />,
  },
);

interface Props {
  finding: Finding | null;
}

const SAMPLE_CODE: Record<string, string> = {
  "src/api/users.py": `import sqlite3

def get_user(username):
    conn = sqlite3.connect('app.db')
    cursor = conn.cursor()
    # Vulnerable: SQL injection
    query = f"SELECT * FROM users WHERE name = '{username}'"
    cursor.execute(query)
    return cursor.fetchone()

def create_user(username, email):
    conn = sqlite3.connect('app.db')
    cursor = conn.cursor()
    cursor.execute("INSERT INTO users (name, email) VALUES (?, ?)", (username, email))
    conn.commit()`,
  "src/views/profile.html": `<!DOCTYPE html>
<html>
<head><title>Profile</title></head>
<body>
  <div class="profile">
    <h1>User Profile</h1>
    <span>{{ user.display_name | safe }}</span>
    <p>Email: {{ user.email }}</p>
  </div>
</body>
</html>`,
  "src/config.py": `import os

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///app.db")
SECRET_KEY = os.getenv("SECRET_KEY", "dev-only")
DEBUG = os.getenv("DEBUG", "false").lower() == "true"

AWS_KEY = "AKIA..."
AWS_SECRET = "wJalr..."`,
  "src/api/files.py": `import os
from pathlib import Path

UPLOAD_DIR = "/var/uploads"

def get_file(request):
    filename = request.params["filename"]
    path = os.path.join(UPLOAD_DIR, filename)
    if not os.path.exists(path):
        return {"error": "not found"}, 404
    with open(path, "rb") as f:
        return f.read()`,
  "src/auth/password.py": `import hashlib

def hash_password(password):
    return hashlib.md5(password.encode()).hexdigest()

def verify_password(password, hashed):
    return hash_password(password) == hashed`,
};

function getLanguage(filePath: string): string {
  if (filePath.endsWith(".py")) return "python";
  if (filePath.endsWith(".html")) return "html";
  if (filePath.endsWith(".ts") || filePath.endsWith(".tsx"))
    return "typescript";
  if (filePath.endsWith(".js") || filePath.endsWith(".jsx"))
    return "javascript";
  return "plaintext";
}

export function CodeViewer({ finding }: Props) {
  if (!finding) {
    return (
      <div className="flex h-full items-center justify-center text-muted-foreground">
        취약점을 선택하면 코드가 표시됩니다.
      </div>
    );
  }

  const code =
    SAMPLE_CODE[finding.file_path] ??
    `// ${finding.file_path}\n// 코드를 불러올 수 없습니다.`;
  const language = getLanguage(finding.file_path);

  return (
    <div className="h-full flex flex-col">
      <div className="shrink-0 border-b bg-muted/50 px-3 py-2 text-xs font-mono">
        {finding.file_path}:{finding.line_start}-{finding.line_end}
      </div>
      <div className="flex-1 min-h-0">
        <Editor
          height="100%"
          language={language}
          value={code}
          theme="vs-dark"
          options={{
            readOnly: true,
            minimap: { enabled: true },
            lineNumbers: "on",
            scrollBeyondLastLine: false,
            fontSize: 13,
          }}
          onMount={(editor) => {
            editor.revealLineInCenter(finding.line_start);
            editor.deltaDecorations(
              [],
              [
                {
                  range: {
                    startLineNumber: finding.line_start,
                    startColumn: 1,
                    endLineNumber: finding.line_end,
                    endColumn: 1,
                  },
                  options: {
                    isWholeLine: true,
                    className: "bg-red-500/20",
                    glyphMarginClassName: "bg-red-500",
                  },
                },
              ],
            );
          }}
        />
      </div>
    </div>
  );
}
