use rusqlite::{params, Connection};
use serde_json::Value;
use tauri::Manager;

fn section(app: &tauri::AppHandle, key: &str) -> Result<Connection, String> {
    if !SECTION_KEYS.contains(&key) {
        return Err("Seção local inválida.".into());
    }
    open_database(app)
}

pub(crate) const SECTION_KEYS: &[&str] = &[
    WORKSPACE_KEY,
    "diolino-health-entries",
    "diolino-health-goals",
    "diolino-habits-v1",
    "diolino-habit-marks-v1",
    "diolino-preview-reviews",
    "diolino-bible-days",
    "diolino-bible-notes",
    "diolino-food-entries",
    "diolino-food-goals",
    "diolino-food-date-goals",
    "diolino-strength-plan",
    "diolino-daily-tasks",
];

pub(crate) fn open_database(app: &tauri::AppHandle) -> Result<Connection, String> {
    let directory = app
        .path()
        .app_data_dir()
        .map_err(|_| "Pasta de dados 3.0 indisponível.")?;
    std::fs::create_dir_all(&directory)
        .map_err(|_| "Não foi possível criar a pasta de dados 3.0.")?;
    let conn = Connection::open(directory.join("desktop-v3.sqlite3"))
        .map_err(|_| "Banco 3.0 indisponível.")?;
    conn.busy_timeout(std::time::Duration::from_secs(3))
        .map_err(|_| "Banco 3.0 ocupado.")?;
    conn.execute_batch(
        "CREATE TABLE IF NOT EXISTS sections (key TEXT PRIMARY KEY, value TEXT NOT NULL);",
    )
    .map_err(|_| "Não foi possível abrir a estrutura do banco 3.0.")?;
    Ok(conn)
}

#[tauri::command]
pub async fn read_local_section(
    app: tauri::AppHandle,
    key: String,
) -> Result<Option<Value>, String> {
    tauri::async_runtime::spawn_blocking(move || {
        use rusqlite::OptionalExtension;
        let raw: Option<String> = section(&app, &key)?
            .query_row("SELECT value FROM sections WHERE key=?1", [&key], |row| {
                row.get(0)
            })
            .optional()
            .map_err(|_| "Não foi possível ler os dados 3.0.")?;
        raw.map(|data| serde_json::from_str(&data).map_err(|_| "Dados 3.0 inválidos.".into()))
            .transpose()
    })
    .await
    .map_err(|_| "Falha de comunicação local.".to_string())?
}

#[tauri::command]
pub async fn write_local_section(
    app: tauri::AppHandle,
    key: String,
    value: Value,
) -> Result<(), String> {
    tauri::async_runtime::spawn_blocking(move || {
        if key == WORKSPACE_KEY { return Err("Use a gravação transacional dos registros.".into()); }
        let raw = value.to_string();
        if raw.len() > 8 * 1024 * 1024 { return Err("Registro excede o limite local.".into()); }
        section(&app, &key)?.execute(
            "INSERT INTO sections (key,value) VALUES (?1,?2) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
            params![key, raw],
        ).map_err(|_| "Não foi possível salvar no banco 3.0.")?;
        Ok(())
    }).await.map_err(|_| "Falha de comunicação local.".to_string())?
}

pub(crate) const WORKSPACE_KEY: &str = "diolino-workspace-v1";

#[tauri::command]
pub async fn save_workspace(
    app: tauri::AppHandle,
    expected: Option<Value>,
    value: Value,
) -> Result<(), String> {
    tauri::async_runtime::spawn_blocking(move || {
        use rusqlite::{OptionalExtension, TransactionBehavior};
        let raw = value.to_string();
        if raw.len() > 8 * 1024 * 1024 {
            return Err("A base de agenda, planos e estudos atingiu o limite desta prévia.".into());
        }
        let mut conn = section(&app, WORKSPACE_KEY)?;
        let tx = conn
            .transaction_with_behavior(TransactionBehavior::Immediate)
            .map_err(|_| "Banco 3.0 ocupado. Tente novamente.")?;
        let stored: Option<String> = tx
            .query_row("SELECT value FROM sections WHERE key=?1", [WORKSPACE_KEY], |row| row.get(0))
            .optional()
            .map_err(|_| "Não foi possível ler a versão dos registros.")?;
        let current = stored
            .map(|raw| serde_json::from_str::<Value>(&raw))
            .transpose()
            .map_err(|_| "Registros da 3.0 inválidos.")?;
        if current != expected {
            return Err("Os registros mudaram em outra janela. Use Atualizar antes de salvar.".into());
        }
        tx.execute(
            "INSERT INTO sections (key,value) VALUES (?1,?2) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
            params![WORKSPACE_KEY, raw],
        )
        .map_err(|_| "Não foi possível guardar os registros.")?;
        tx.commit().map_err(|_| "Não foi possível confirmar a gravação.".into())
    })
    .await
    .map_err(|_| "Falha de comunicação local.".to_string())?
}
