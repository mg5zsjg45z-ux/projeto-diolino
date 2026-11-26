use rusqlite::{params, Connection};
use serde_json::Value;
use tauri::Manager;

fn section(app: &tauri::AppHandle, key: &str) -> Result<Connection, String> {
    if !matches!(
        key,
        "diolino-health-entries"
            | "diolino-health-goals"
            | "diolino-habits-v1"
            | "diolino-habit-marks-v1"
            | "diolino-preview-reviews"
            | "diolino-bible-days"
    ) {
        return Err("Seção local inválida.".into());
    }
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
        let raw = value.to_string();
        if raw.len() > 8 * 1024 * 1024 { return Err("Registro excede o limite local.".into()); }
        section(&app, &key)?.execute(
            "INSERT INTO sections (key,value) VALUES (?1,?2) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
            params![key, raw],
        ).map_err(|_| "Não foi possível salvar no banco 3.0.")?;
        Ok(())
    }).await.map_err(|_| "Falha de comunicação local.".to_string())?
}
